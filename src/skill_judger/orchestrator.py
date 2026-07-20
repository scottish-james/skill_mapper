from skill_judger.auth import AuthError, authenticate


def main():
    try:
        token = authenticate()
    except AuthError as e:
        print(f"Authentication failed: {e}")
        return

    print("JWT received, moving to next step")


if __name__ == "__main__":
    main()
