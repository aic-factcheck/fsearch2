#!/usr/bin/env python3
import json
import getpass
from pathlib import Path
from passlib.context import CryptContext

USERS_FILE = Path("users.json")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def add_user(username: str):
    password = getpass.getpass(f"Password for {username}: ")
    pw_hash = pwd_context.hash(password)

    users = {}
    if USERS_FILE.exists():
        users = json.loads(USERS_FILE.read_text())

    users[username] = {"password_hash": pw_hash}
    USERS_FILE.write_text(json.dumps(users, indent=2))
    print(f"✅ User '{username}' added/updated in {USERS_FILE}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Add or update a user for the FactSearch2 app")
    p.add_argument("username")
    args = p.parse_args()
    add_user(args.username)
