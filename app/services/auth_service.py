"""
Business Layer — AuthService

Responsibility: Authentication logic and rules.

Loose coupling: This service calls user_repository to fetch data
but has no knowledge of Flask, HTTP, or sessions. It raises plain
Python exceptions (ValueError, PermissionError) that the REST layer
(api_routes.py) maps to HTTP status codes. This means the same
business logic could be reused with a different web framework
or a CLI without any changes here.
"""

import bcrypt
from app.repositories import user_repository


def login(db, email, password):
    if not email or not password:
        raise ValueError("Email and password are required.")

    user = user_repository.get_user_by_email(db, email)

    if not user:
        raise PermissionError("Invalid credentials.")

    if user["status"] != "active":
        raise PermissionError("This account is not active.")

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise PermissionError("Invalid credentials.")

    return {
        "user_id": user["user_id"],
        "society_id": user["society_id"],
        "role": user["role"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
    }
