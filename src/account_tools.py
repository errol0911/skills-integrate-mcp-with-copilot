"""Interactive helper for generating account entries for ACCOUNTS_JSON."""

import argparse
import getpass
import json

from app import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("student", "admin"), required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if not password:
        parser.error("Password must not be empty")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords do not match")

    print(json.dumps({args.email: {
        "role": args.role,
        "password_hash": hash_password(password),
    }}, indent=2))


if __name__ == "__main__":
    main()