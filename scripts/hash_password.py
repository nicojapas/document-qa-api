#!/usr/bin/env python3
"""
Utility script to generate bcrypt password hashes for the demo user.

Usage:
    python scripts/hash_password.py <password>

Then add the output to your .env file as DEMO_USER_PASSWORD_HASH.
"""
import sys

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/hash_password.py <password>")
        sys.exit(1)

    password = sys.argv[1]
    hashed = pwd_context.hash(password)

    print(f"\nPassword hash generated successfully!\n")
    print(f"Add this to your .env file:\n")
    print(f'DEMO_USER_PASSWORD_HASH="{hashed}"')
    print()


if __name__ == "__main__":
    main()
