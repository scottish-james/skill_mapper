from pathlib import Path

from skill_judger.auth import AuthError
from skill_judger.grader import grade_rows
from skill_judger.validate_csv import validate_csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "grade_rating_prompt.yaml"
INPUT_CSV = PROJECT_ROOT / "data" / "skills.csv"
OUTPUT_CSV_TESTING = PROJECT_ROOT / "data" / "skills_graded.csv"
OUTPUT_CSV_PROD = PROJECT_ROOT / "data" / "skills_graded_prod.csv"


def run_prod():
    from skill_judger.prod_provider import classify_row, get_token

    try:
        get_token()
    except AuthError as e:
        print(f"Authentication failed: {e}")
        return

    grade_rows(classify_row, PROMPT_PATH, INPUT_CSV, OUTPUT_CSV_PROD)


def main():
    environment = input("Environment (testing/prod): ").strip().lower()

    if not validate_csv(INPUT_CSV, PROMPT_PATH):
        print("\nAborting: fix the CSV/prompt mismatch above before running.")
        return

    if environment == "testing":
        # dev-only path, see testing_provider.py — remove this branch before prod
        from skill_judger.testing_provider import classify_row
        grade_rows(classify_row, PROMPT_PATH, INPUT_CSV, OUTPUT_CSV_TESTING)
    elif environment == "prod":
        run_prod()
    else:
        print(f"Unknown environment '{environment}', expected 'testing' or 'prod'")


if __name__ == "__main__":
    main()
