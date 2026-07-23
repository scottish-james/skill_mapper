"""Pre-flight check: does the input CSV's columns match what the prompt's
user_template needs? Catches column-name mismatches, UTF-8 BOMs, and wrong
delimiters early — with a clear report instead of a KeyError buried mid-run.
Called automatically by orchestrator.py before a real run, and can also be
run standalone: uv run python src/skill_judger/validate_csv.py
"""
import csv
import re
from pathlib import Path

import yaml


def _template_fields(user_template: str) -> set:
    return set(re.findall(r"\{(\w+)\}", user_template))


def _read_header(csv_path: Path, encoding: str) -> list:
    with open(csv_path, newline="", encoding=encoding) as f:
        return next(csv.reader(f), [])


def validate_csv(input_csv: Path, prompt_path: Path, verbose: bool = True) -> bool:
    """Return True if input_csv has every column prompt_path's user_template
    needs. Prints a diagnostic report either way when verbose (the default)."""
    if not input_csv.exists():
        print(f"FAIL: {input_csv} does not exist.")
        return False

    if not prompt_path.exists():
        print(f"FAIL: {prompt_path} does not exist.")
        return False

    with open(prompt_path) as f:
        prompt_config = yaml.safe_load(f)

    required_fields = _template_fields(prompt_config.get("user_template", ""))

    header_plain = _read_header(input_csv, encoding="utf-8")
    header_sig = _read_header(input_csv, encoding="utf-8-sig")
    has_bom = header_plain != header_sig
    header = header_sig

    if verbose:
        print(f"Checking:       {input_csv}")
        print(f"Against prompt: {prompt_path}\n")
        print("Raw header, exact column names (repr'd so hidden characters show):")
        for col in header_plain:
            print(f"  {col!r}")
        print()

    if len(header_plain) == 1 and any(c in header_plain[0] for c in ("\t", ";")):
        print(
            "WARNING: only one column was parsed, but it contains a tab or "
            "semicolon — this file is likely not comma-delimited. csv.DictReader "
            "will misread every row.\n"
        )

    if has_bom and verbose:
        print(
            "UTF-8 BOM detected at the start of the file. This silently "
            f"turns your first column's real name into {header_plain[0]!r} "
            "instead of what you'd expect. The code needs to read this file "
            "with encoding='utf-8-sig' to strip it.\n"
        )
    elif verbose:
        print("No UTF-8 BOM detected on this file.\n")

    if verbose:
        print("Header as the code will see it once BOM-safe reading is used:")
        for col in header:
            print(f"  {col!r}")
        print()
        print(f"Prompt's user_template requires these fields: {sorted(required_fields)}")

    missing = required_fields - set(header)

    if missing:
        print(f"\nFAIL: CSV is missing required column(s): {sorted(missing)}")
        print(f"CSV actually has: {header}")
        print(
            "\nFix: either rename the CSV's columns to match, or update "
            f"user_template in {prompt_path} to use your CSV's real column names."
        )
        return False

    if verbose:
        print("\nPASS: every field the prompt needs is present in the CSV header.")
    return True


def main():
    from skill_judger.orchestrator import CLASSIFIERS, INPUT_CSV

    for name, classifier in CLASSIFIERS.items():
        print(f"=== {name} ===")
        validate_csv(INPUT_CSV, classifier["prompt_path"])
        print()


if __name__ == "__main__":
    main()
