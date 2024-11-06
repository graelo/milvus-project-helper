"""Utility functions for Milvus project management.

This module provides helper functions and classes:
- Password strength validation
- Exception classes for password validation errors

Password requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
"""

PASSWORD_MIN_LENGTH = 8


class PasswordStrengthError(Exception):
    """Base exception class for password strength validation errors."""

    MIN_LENGTH = f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
    UPPERCASE = "Password must contain at least one uppercase letter"
    LOWERCASE = "Password must contain at least one lowercase letter"
    DIGIT = "Password must contain at least one digit"
    SPECIAL = "Password must contain at least one special character"


def check_password_strength(password: str) -> None:
    """Check if the password is strong enough according to Milvus requirements."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordStrengthError(PasswordStrengthError.MIN_LENGTH)
    if not any(c.isupper() for c in password):
        raise PasswordStrengthError(PasswordStrengthError.UPPERCASE)
    if not any(c.islower() for c in password):
        raise PasswordStrengthError(PasswordStrengthError.LOWERCASE)
    if not any(c.isdigit() for c in password):
        raise PasswordStrengthError(PasswordStrengthError.DIGIT)
    if not any(c in "!@#$%^&*()-+" for c in password):
        raise PasswordStrengthError(PasswordStrengthError.SPECIAL)
