"""
Email service for Lexora.

Behaviour:
  - If SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD are configured in the
    environment, real emails are sent via Python's built-in smtplib.
  - Otherwise, the verification / reset links are printed to the console
    (mock mode) so developers can copy-paste them during local development.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


def _html_wrapper(heading: str, body_html: str, cta_url: Optional[str] = None, cta_label: Optional[str] = None) -> str:
    """Returns a branded HTML email template."""
    cta_block = ""
    if cta_url and cta_label:
        cta_block = f"""
        <div style="text-align:center;margin:32px 0;">
          <a href="{cta_url}"
             style="background:#7c3aed;color:#fff;text-decoration:none;
                    padding:14px 28px;border-radius:10px;font-weight:700;
                    font-size:14px;display:inline-block;">
            {cta_label}
          </a>
        </div>
        <p style="font-size:12px;color:#888;text-align:center;word-break:break-all;">
          If the button doesn't work, copy and paste this link into your browser:<br/>
          <a href="{cta_url}" style="color:#7c3aed;">{cta_url}</a>
        </p>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f0f14;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0f14;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#1a1a24;border-radius:16px;border:1px solid #2a2a3a;overflow:hidden;max-width:600px;">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#7c3aed,#a855f7);padding:28px 40px;">
            <h1 style="margin:0;font-size:22px;font-weight:800;color:#fff;letter-spacing:-0.5px;">
              &#x1F6E1;&#xFE0F; LEXORA
            </h1>
            <p style="margin:4px 0 0;font-size:11px;color:rgba(255,255,255,0.7);
                      text-transform:uppercase;letter-spacing:2px;">
              AI Risk Analyzer, Rephraser &amp; Humanizer
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <h2 style="margin:0 0 16px;font-size:18px;font-weight:700;color:#e5e5f0;">{heading}</h2>
            <div style="color:#aaa;font-size:14px;line-height:1.7;">
              {body_html}
            </div>
            {cta_block}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;border-top:1px solid #2a2a3a;">
            <p style="margin:0;font-size:11px;color:#555;text-align:center;">
              This email was sent by Lexora. If you did not request this action, you can safely ignore this email.<br/>
              &copy; 2024 Lexora Research Tools
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _send_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends an email using smtplib (STARTTLS on port 587 by default, or SSL on 465).
    Returns True on success, False on failure (so callers can fall back to mock).
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Lexora <{settings.SMTP_FROM}>"
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if settings.SMTP_PORT == 465:
            # SSL from the start
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        else:
            # Plain + STARTTLS (works for port 587 / 25)
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                smtp.ehlo()
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                    smtp.ehlo()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.sendmail(settings.SMTP_FROM, to_email, msg.as_string())

        logger.info(f"[EMAIL] Sent '{subject}' to {to_email}")
        return True

    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send '{subject}' to {to_email}: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def send_verification_email(to_email: str, verify_link: str) -> None:
    """
    Send an account verification email.
    Falls back to console print if SMTP is not configured.
    """
    subject = "Verify your Lexora account"
    body_html = """
    <p>Welcome to <strong>Lexora</strong>!</p>
    <p>Please click the button below to verify your email address and activate your researcher account.
       This link is valid for <strong>24 hours</strong>.</p>
    """

    html = _html_wrapper(
        heading="Confirm your email address",
        body_html=body_html,
        cta_url=verify_link,
        cta_label="Verify Email Address",
    )

    if _is_smtp_configured():
        success = _send_smtp(to_email, subject, html)
        if not success:
            _mock_verification(to_email, verify_link)
    else:
        _mock_verification(to_email, verify_link)


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Send a password-reset email.
    Falls back to console print if SMTP is not configured.
    """
    subject = "Reset your Lexora password"
    body_html = """
    <p>We received a request to reset the password for your Lexora account.</p>
    <p>Click the button below to choose a new password.
       This link is valid for <strong>1 hour</strong>.
       If you did not make this request, you can safely ignore this email.</p>
    """

    html = _html_wrapper(
        heading="Password reset request",
        body_html=body_html,
        cta_url=reset_link,
        cta_label="Reset Password",
    )

    if _is_smtp_configured():
        success = _send_smtp(to_email, subject, html)
        if not success:
            _mock_reset(to_email, reset_link)
    else:
        _mock_reset(to_email, reset_link)


def send_security_alert_email(to_email: str, message: str) -> None:
    """
    Send a generic security alert (e.g., duplicate registration attempt).
    Falls back to console print if SMTP is not configured.
    """
    subject = "Lexora Security Alert"
    body_html = f"<p>{message}</p>"

    html = _html_wrapper(
        heading="Security notification",
        body_html=body_html,
    )

    if _is_smtp_configured():
        _send_smtp(to_email, subject, html)
    else:
        logger.warning(f"[SMTP MOCK] Security alert to {to_email}: {message}")


# ─────────────────────────────────────────────────────────────────────────────
# Mock helpers (print links to console for easy copy-paste)
# ─────────────────────────────────────────────────────────────────────────────

def _mock_verification(to_email: str, verify_link: str) -> None:
    msg = (
        f"\n{'='*70}\n"
        f"[SMTP MOCK] Verification email for: {to_email}\n"
        f"  → Copy this link into your browser to verify the account:\n"
        f"  {verify_link}\n"
        f"{'='*70}\n"
    )
    logger.info(msg)


def _mock_reset(to_email: str, reset_link: str) -> None:
    msg = (
        f"\n{'='*70}\n"
        f"[SMTP MOCK] Password reset link for: {to_email}\n"
        f"  → Copy this link into your browser to reset the password:\n"
        f"  {reset_link}\n"
        f"{'='*70}\n"
    )
    logger.info(msg)
