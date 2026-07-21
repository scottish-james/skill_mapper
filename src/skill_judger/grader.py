"""Generic row-by-row LLM grading loop. Knows nothing about skills, job
families, or which model/gateway is behind classify_row — reusable for any
project that needs "read a CSV, send each row through a prompt, write the
enriched CSV back out". Schema validation is driven by an optional
'expected_keys' list in the prompt YAML, not hardcoded here."""
import csv
from pathlib import Path

import yaml

MAX_ROW_ATTEMPTS = 3


class StopGrading(Exception):
    """Raise from classify_row to stop the whole run immediately (e.g. a
    daily token budget was exhausted) rather than retrying or erroring just
    the current row. Propagates straight through retry handling."""


def load_prompt_config(prompt_path: Path) -> dict:
    """Load a YAML prompt config with 'system_prompt', 'user_template', and
    an optional 'expected_keys' list used to validate each response and
    enable checkpointing."""
    with open(prompt_path) as f:
        return yaml.safe_load(f)


def _validate_result(result: dict, expected_keys: list) -> None:
    """Raise ValueError if result isn't exactly {key: "yes"|"no"} for every
    expected key — no missing keys, no extra keys, no other values."""
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object, got {type(result).__name__}")
    if set(result.keys()) != set(expected_keys):
        raise ValueError(f"Expected keys {expected_keys}, got {list(result.keys())}")
    for key, value in result.items():
        if value not in ("yes", "no"):
            raise ValueError(f"Expected 'yes' or 'no' for '{key}', got {value!r}")


def _classify_with_retry(classify_row, prompt_config: dict, row: dict) -> dict:
    """Try classify_row up to MAX_ROW_ATTEMPTS times, validating each
    response against expected_keys if the prompt config defines one. Returns
    the valid result, or an all-fields-errored dict if every attempt fails."""
    expected_keys = prompt_config.get("expected_keys")
    last_error = None

    for attempt in range(1, MAX_ROW_ATTEMPTS + 1):
        try:
            result = classify_row(prompt_config, row)
            if expected_keys is not None:
                _validate_result(result, expected_keys)
            return result
        except StopGrading:
            raise
        except Exception as e:
            last_error = e
            print(f"  Attempt {attempt} failed: {e}")

    print(f"  Giving up after {MAX_ROW_ATTEMPTS} attempts: {last_error}")
    error_value = f"ERROR: {last_error}"
    if expected_keys is not None:
        return {key: error_value for key in expected_keys}
    return {"error": error_value}


def _completed_keys(output_csv: Path, key_field: str, fieldnames: list) -> set:
    """Rows already written from a previous, interrupted run — matched on
    key_field (the input CSV's first column). Raises if output_csv exists
    with different columns than this run would produce, rather than
    silently appending mismatched data."""
    if not output_csv.exists():
        return set()

    with open(output_csv, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != fieldnames:
            raise ValueError(
                f"{output_csv} exists with different columns than expected "
                f"({reader.fieldnames} vs {fieldnames}). Move or delete it "
                "before starting a new run."
            )
        return {row[key_field] for row in reader}


def _grade_rows_no_checkpoint(classify_row, prompt_config: dict, rows: list, output_csv: Path):
    """Fallback when the prompt config has no expected_keys, so the output
    schema isn't known upfront — writes everything at once at the end, same
    as before. No resume support in this mode."""
    output_rows = []
    fieldnames = None

    for row in rows:
        label = next(iter(row.values()), "<row>")
        print(f"Grading: {label}")

        try:
            result = _classify_with_retry(classify_row, prompt_config, row)
        except StopGrading as e:
            print(f"Stopping: {e}")
            break

        combined = {**row, **result}
        output_rows.append(combined)
        if fieldnames is None:
            fieldnames = list(combined.keys())

    with open(output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Done. Results written to {output_csv}")


def grade_rows(classify_row, prompt_path: Path, input_csv: Path, output_csv: Path):
    """classify_row(prompt_config: dict, row: dict) -> dict of fields to add
    to that row.

    Checkpointed: each row is written and flushed to output_csv immediately
    after grading. If interrupted and re-run, rows already present in
    output_csv (matched on the input CSV's first column) are skipped, so a
    crash only loses the one row that was in flight. Requires expected_keys
    in the prompt config to know the output schema upfront; without it,
    falls back to the old collect-then-write-once behaviour with no resume.
    """
    prompt_config = load_prompt_config(prompt_path)
    expected_keys = prompt_config.get("expected_keys")

    with open(input_csv, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        input_fieldnames = reader.fieldnames or []

    if not rows:
        print("No rows to grade.")
        return

    if expected_keys is None:
        _grade_rows_no_checkpoint(classify_row, prompt_config, rows, output_csv)
        return

    key_field = input_fieldnames[0]
    fieldnames = input_fieldnames + [k for k in expected_keys if k not in input_fieldnames]

    done = _completed_keys(output_csv, key_field, fieldnames)
    remaining_rows = [row for row in rows if row[key_field] not in done]

    if done:
        print(f"Resuming: {len(done)} already done, {len(remaining_rows)} remaining.")

    if not remaining_rows:
        print("All rows already graded.")
        return

    file_is_new = not output_csv.exists()
    with open(output_csv, "a", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        if file_is_new:
            writer.writeheader()

        for row in remaining_rows:
            print(f"Grading: {row[key_field]}")

            try:
                result = _classify_with_retry(classify_row, prompt_config, row)
            except StopGrading as e:
                print(f"Stopping: {e}")
                break

            writer.writerow({**row, **result})
            out.flush()

    print(f"Done. Results written to {output_csv}")
