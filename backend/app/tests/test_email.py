import logging

import pytest

from app.services import email as email_service


@pytest.mark.parametrize(
    ("send_email", "args", "expected_text"),
    [
        (
            email_service.send_verification_email,
            ("researcher@example.org", "http://localhost:3000/verify?token=test-token"),
            "http://localhost:3000/verify?token=test-token",
        ),
        (
            email_service.send_password_reset_email,
            ("researcher@example.org", "http://localhost:3000/reset-password?token=test-token"),
            "http://localhost:3000/reset-password?token=test-token",
        ),
        (
            email_service.send_security_alert_email,
            ("researcher@example.org", "Security alert → review your account"),
            "Security alert → review your account",
        ),
    ],
)
def test_mock_emails_log_without_console_print(
    send_email, args, expected_text, monkeypatch, caplog
):
    monkeypatch.setattr(email_service, "_is_smtp_configured", lambda: False)

    def fail_print(*args, **kwargs):
        raise UnicodeEncodeError(
            "charmap", "→", 0, 1, "character maps to <undefined>"
        )

    monkeypatch.setattr("builtins.print", fail_print)

    with caplog.at_level(logging.INFO, logger=email_service.__name__):
        send_email(*args)

    assert expected_text in caplog.text
