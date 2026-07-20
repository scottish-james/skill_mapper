"""Generic row-by-row LLM grading loop. Knows nothing about skills, job
families, or which model/gateway is behind classify_row — reusable for any
project that needs "read a CSV, send each row through a prompt, write the
enriched CSV back out". Schema validation is driven by an optional
'expected_keys' list in the prompt YAML, not hardcoded here."""
import csv
from pathlib import Path

import yaml

MAX_ROW_ATTEMPTS = 3


def load_prompt_config(prompt_path: Path) -> dict:
    """Load a YAML prompt config with 'system_prompt', 'user_template', and
    an optional 'expected_keys' list used to validate each response."""
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
        except Exception as e:
            last_error = e
            print(f"  Attempt {attempt} failed: {e}")

    print(f"  Giving up after {MAX_ROW_ATTEMPTS} attempts: {last_error}")
    error_value = f"ERROR: {last_error}"
    if expected_keys is not None:
        return {key: error_value for key in expected_keys}
    return {"error": error_value}


def grade_rows(classify_row, prompt_path: Path, input_csv: Path, output_csv: Path):
    """classify_row(prompt_config: dict, row: dict) -> dict of fields to add to that row"""
    prompt_config = load_prompt_config(prompt_path)

    with open(input_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    output_rows = []
    fieldnames = None

    for row in rows:
        label = next(iter(row.values()), "<row>")
        print(f"Grading: {label}")

        result = _classify_with_retry(classify_row, prompt_config, row)

        combined = {**row, **result}
        output_rows.append(combined)
        if fieldnames is None:
            fieldnames = list(combined.keys())

    with open(output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Done. Results written to {output_csv}")
