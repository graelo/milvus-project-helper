"""Unit tests for the utils module."""

import pytest

from milvus_project_helper.utils import PasswordStrengthError, check_password_strength


@pytest.mark.parametrize(
    "password",
    [
        "Password123!",
        "StrongP@ss1",
        "C0mpl3x!Pass",
        "Sup3r$tr0ng",
        "MyP@ssw0rd",
    ],
)
def test_valid_passwords(password: str) -> None:
    """Test passwords that should pass validation."""
    check_password_strength(password)  # Should not raise


@pytest.mark.parametrize(
    "password,expected_error",
    [
        ("short1!", PasswordStrengthError.MIN_LENGTH),
        ("password123!", PasswordStrengthError.UPPERCASE),
        ("PASSWORD123!", PasswordStrengthError.LOWERCASE),
        ("Password!", PasswordStrengthError.DIGIT),
        ("Password123", PasswordStrengthError.SPECIAL),
        ("abc", PasswordStrengthError.MIN_LENGTH),
        ("nospecialchar1A", PasswordStrengthError.SPECIAL),
        ("!@#$%^&*()", PasswordStrengthError.UPPERCASE),
    ],
)
def test_invalid_passwords(password: str, expected_error: str) -> None:
    """Test passwords that should fail validation with specific errors."""
    with pytest.raises(PasswordStrengthError) as exc_info:
        check_password_strength(password)
    assert str(exc_info.value) == expected_error
