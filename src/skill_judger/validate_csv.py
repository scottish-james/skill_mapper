"""Run this before a real grading pass to catch column-name mismatches,
UTF-8 BOMs, and wrong delimiters early — with a clear report instead of a
KeyError buried mid-run.

Usage: uv run python src/skill_judger/validate_csv.py
"""
import csv
import re
from pathlib import Path

import yaml

from skill_judger.orchestrator import INPUT_CSV, PROMPT_PATH


def _template_fields(user_template: str) -> set:
    return set(re.findall(r"\{(\w+)\}", user_template))


def _read_header(csv_path: Path, encoding: str) -> list:
    with open(csv_path, newline="", encoding=encoding) as f:
        return next(csv.reader(f), [])


def main():
    print(f"Checking:      {INPUT_CSV}")
    print(f"Against prompt: {PROMPT_PATH}\n")

    if not INPUT_CSV.exists():
        print(f"FAIL: {INPUT_CSV} does not exist.")
        return

    if not PROMPT_PATH.exists():
        print(f"FAIL: {PROMPT_PATH} does not exist.")
        return

    with open(PROMPT_PATH) as f:
        prompt_config = yaml.safe_load(f)

    required_fields = _template_fields(prompt_config.get("user_template", ""))

    header_plain = _read_header(INPUT_CSV, encoding="utf-8")
    header_sig = _read_header(INPUT_CSV, encoding="utf-8-sig")
    has_bom = header_plain != header_sig

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

    if has_bom:
        print(
            "UTF-8 BOM detected at the start of the file. This silently "
            f"turns your first column's real name into {header_plain[0]!r} "
            "instead of what you'd expect. The code needs to read this file "
            "with encoding='utf-8-sig' to strip it.\n"
        )
    else:
        print("No UTF-8 BOM detected on this file.\n")

    header = header_sig
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
            f"user_template in {PROMPT_PATH} to use your CSV's real column names."
        )
    else:
        print("\nPASS: every field the prompt needs is present in the CSV header.")


if __name__ == "__main__":
    main()
