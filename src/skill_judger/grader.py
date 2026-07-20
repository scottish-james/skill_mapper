"""Generic row-by-row LLM grading loop. Knows nothing about skills, job
families, prompts, or which model/gateway is behind classify_row — reusable
for any project that needs "read a CSV, send each row through a prompt,
write the enriched CSV back out"."""
import csv
from pathlib import Path

import yaml


def load_prompt_config(prompt_path: Path) -> dict:
    """Load a YAML prompt config with 'system_prompt' and 'user_template' keys."""
    with open(prompt_path) as f:
        return yaml.safe_load(f)


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

        try:
            result = classify_row(prompt_config, row)
        except Exception as e:
            print(f"  Failed: {e}")
            continue

        combined = {**row, **result}
        output_rows.append(combined)
        if fieldnames is None:
            fieldnames = list(combined.keys())

    with open(output_csv, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Done. Results written to {output_csv}")
