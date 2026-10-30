#!/usr/bin/env python3
"""
Interactive CLI script to create the initial CEO / Administrator user.
Usage:
    python scripts/create_admin.py
    python scripts/create_admin.py --username admin --name "Abebe Bekele" --password "Secret123!"
"""
import sys
import getpass
import argparse
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.audit import AuditLog


def create_admin_user(name: str, username: str, password: str) -> User:
    """Create a new CEO user with hashed password and audit logging."""
    existing = User.query.filter_by(username=username).first()
    if existing:
        print(f"[!] Error: A user with username '{username}' already exists.")
        sys.exit(1)

    admin = User(
        name=name.strip(),
        username=username.strip().lower(),
        role=User.ROLE_CEO,
        is_active=True
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.flush()

    AuditLog.log(
        action="USER_CREATED",
        user_id=admin.id,
        details=f"Initial CEO administrator '{admin.username}' created via CLI script."
    )
    db.session.commit()
    return admin


def main():
    parser = argparse.ArgumentParser(description="Create the initial CEO / Admin user.")
    parser.add_argument("--name", help="Full name of the CEO", default=None)
    parser.add_argument("--username", help="Username for login", default=None)
    parser.add_argument("--password", help="Password for login", default=None)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        name = args.name
        username = args.username
        password = args.password

        print("=" * 60)
        print("          PTS Demo - Initial CEO Account Creation")
        print("=" * 60)

        if not name:
            name = input("Enter CEO Full Name: ").strip()
            while not name:
                print("Name cannot be empty.")
                name = input("Enter CEO Full Name: ").strip()

        if not username:
            username = input("Enter Username: ").strip().lower()
            while not username or len(username) < 3:
                print("Username must be at least 3 characters.")
                username = input("Enter Username: ").strip().lower()

        if not password:
            while True:
                p1 = getpass.getpass("Enter Secure Password: ")
                if len(p1) < 8:
                    print("Password must be at least 8 characters long.")
                    continue
                p2 = getpass.getpass("Confirm Password: ")
                if p1 != p2:
                    print("Passwords do not match. Please try again.")
                    continue
                password = p1
                break

        admin = create_admin_user(name=name, username=username, password=password)
        print("\n[+] Success! CEO user created successfully:")
        print(f"    - ID:       {admin.id}")
        print(f"    - Name:     {admin.name}")
        print(f"    - Username: {admin.username}")
        print(f"    - Role:     {admin.role}")
        print("\nYou can now log in to the web dashboard with these credentials.")


if __name__ == "__main__":
    main()
