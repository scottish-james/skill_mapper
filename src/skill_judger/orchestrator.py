from pathlib import Path

from skill_judger.auth import AuthError, authenticate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "config" / "prompts" / "grade_rating_prompt.yaml"
INPUT_CSV = PROJECT_ROOT / "data" / "skills.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "skills_graded.csv"


def run_prod():
    try:
        token = authenticate()
    except AuthError as e:
        print(f"Authentication failed: {e}")
        return

    print("JWT received, moving to next step")


def main():
    environment = input("Environment (testing/prod): ").strip().lower()

    if environment == "testing":
        # dev-only path, see testing_provider.py — remove this branch before prod
        from skill_judger.grader import grade_rows
        from skill_judger.testing_provider import classify_row
        grade_rows(classify_row, PROMPT_PATH, INPUT_CSV, OUTPUT_CSV)
    elif environment == "prod":
        run_prod()
    else:
        print(f"Unknown environment '{environment}', expected 'testing' or 'prod'")


if __name__ == "__main__":
    main()
