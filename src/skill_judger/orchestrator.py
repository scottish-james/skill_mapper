from skill_judger.auth import AuthError, authenticate


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
        from skill_judger.testing_provider import run_testing
        run_testing()
    elif environment == "prod":
        run_prod()
    else:
        print(f"Unknown environment '{environment}', expected 'testing' or 'prod'")


if __name__ == "__main__":
    main()
