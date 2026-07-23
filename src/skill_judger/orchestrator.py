from pathlib import Path

from skill_judger.auth import AuthError
from skill_judger.grader import grade_rows
from skill_judger.validate_csv import validate_csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = PROJECT_ROOT / "data" / "skills.csv"

CLASSIFIERS = {
    "job_families": {
        "prompt_path": PROJECT_ROOT / "config" / "prompts" / "grade_rating_prompt.yaml",
        "output_testing": PROJECT_ROOT / "data" / "skills_graded.csv",
        "output_prod": PROJECT_ROOT / "data" / "skills_graded_prod.csv",
    },
    "grade_relevance": {
        "prompt_path": PROJECT_ROOT / "config" / "prompts" / "grade_relevance_prompt.yaml",
        "output_testing": PROJECT_ROOT / "data" / "skills_graded_relevance.csv",
        "output_prod": PROJECT_ROOT / "data" / "skills_graded_relevance_prod.csv",
    },
}


def run_prod(prompt_path, output_csv):
    from skill_judger.prod_provider import classify_row, get_token

    try:
        get_token()
    except AuthError as e:
        print(f"Authentication failed: {e}")
        return

    grade_rows(classify_row, prompt_path, INPUT_CSV, output_csv)


def main():
    classifier_name = input(f"Classifier ({'/'.join(CLASSIFIERS)}): ").strip().lower()
    classifier = CLASSIFIERS.get(classifier_name)
    if classifier is None:
        print(f"Unknown classifier '{classifier_name}', expected one of: {', '.join(CLASSIFIERS)}")
        return

    prompt_path = classifier["prompt_path"]

    environment = input("Environment (testing/prod): ").strip().lower()

    if not validate_csv(INPUT_CSV, prompt_path):
        print("\nAborting: fix the CSV/prompt mismatch above before running.")
        return

    if environment == "testing":
        # dev-only path, see testing_provider.py — remove this branch before prod
        from skill_judger.testing_provider import classify_row
        grade_rows(classify_row, prompt_path, INPUT_CSV, classifier["output_testing"])
    elif environment == "prod":
        run_prod(prompt_path, classifier["output_prod"])
    else:
        print(f"Unknown environment '{environment}', expected 'testing' or 'prod'")


if __name__ == "__main__":
    main()
