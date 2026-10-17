"""Outbound email over SMTP.

A thin, dependency-free wrapper around the standard library's :mod:`smtplib`.
It owns two concerns: *how* to reach the SMTP relay (TLS mode, auth, timeout),
and *what* the transactional messages look like (password reset, email
verification). The auth service decides *when* to send; it never speaks SMTP
directly.

Design notes
------------
* **Graceful when unconfigured.** With no ``SMTP_HOST`` set (the default), every
  send is a logged no-op that returns ``False`` rather than raising. The auth
  flows stay functional in local/demo setups that have no mail relay - the
  forgot-password endpoint still returns its generic 200, it simply dispatches
  nothing.
* **Best-effort, never fatal to the request.** ``send_email`` catches and logs
  transport failures and returns a bool. Callers run it from a FastAPI
  ``BackgroundTask`` so a slow or down relay never blocks (or fails) the HTTP
  response.
* **No secrets in logs.** Only the recipient and subject are logged, never the
  body or credentials.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "send_email",
    "send_password_reset_email",
]


def send_email(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    settings: Settings | None = None,
) -> bool:
    """Send one email. Returns ``True`` on success, ``False`` otherwise.

    Never raises: an unconfigured relay, a connection failure or an auth
    rejection are all logged and reported as ``False``, because the callers
    treat delivery as best-effort.
    """
    settings = settings or get_settings()

    if not settings.emails_enabled:
        logger.info(
            "Email not sent to %s (%r): email delivery is disabled or "
            "SMTP is not configured.",
            to_email,
            subject,
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from_email))
    message["To"] = to_email
    # A plain-text part first, then HTML: compliant clients show the HTML, and
    # text-only clients still get a readable message.
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
                context=context,
            ) as client:
                _authenticate_and_send(client, message, settings)
        else:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ) as client:
                if settings.SMTP_USE_TLS:
                    client.starttls(context=ssl.create_default_context())
                _authenticate_and_send(client, message, settings)
    except (smtplib.SMTPException, OSError) as exc:
        # OSError covers DNS failures, refused connections and timeouts.
        logger.error(
            "Failed to send email to %s (%r): %s",
            to_email,
            subject,
            exc.__class__.__name__,
        )
        return False

    logger.info("Sent email to %s (%r)", to_email, subject)
    return True


def _authenticate_and_send(
    client: smtplib.SMTP, message: EmailMessage, settings: Settings
) -> None:
    """Log in (when credentials are present) and hand the message to the relay."""
    if settings.SMTP_USERNAME:
        client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
    client.send_message(message)


# ---------------------------------------------------------------------------
# Transactional messages
# ---------------------------------------------------------------------------
def send_password_reset_email(
    *,
    to_email: str,
    full_name: str,
    reset_url: str,
    settings: Settings | None = None,
) -> bool:
    """Send the "reset your password" message with a one-time link."""
    settings = settings or get_settings()
    app_name = settings.APP_NAME
    minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    greeting = full_name.strip() or "there"

    text_body = (
        f"Hi {greeting},\n\n"
        f"We received a request to reset the password for your {app_name} "
        "account.\n\n"
        f"Reset your password using the link below (valid for {minutes} "
        "minutes):\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email - your "
        "password will not change.\n"
    )
    html_body = _wrap_html(
        app_name=app_name,
        heading="Reset your password",
        intro=(
            f"Hi {_escape(greeting)}, we received a request to reset the "
            f"password for your {_escape(app_name)} account."
        ),
        button_label="Reset password",
        button_url=reset_url,
        note=(
            f"This link is valid for {minutes} minutes. If you did not request "
            "a reset, you can safely ignore this email."
        ),
    )
    return send_email(
        to_email=to_email,
        subject=f"Reset your {app_name} password",
        html_body=html_body,
        text_body=text_body,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------
def _escape(value: str) -> str:
    """Minimal HTML escaping for the small set of interpolated strings."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _wrap_html(
    *,
    app_name: str,
    heading: str,
    intro: str,
    button_label: str,
    button_url: str,
    note: str,
) -> str:
    """Render a simple, email-client-safe HTML message with a call-to-action.

    Inline styles only: email clients strip ``<style>`` blocks and ignore
    external CSS. The raw link is shown under the button for clients that do
    not render it.
    """
    return f"""\
<!DOCTYPE html>
<html lang="en">
<body style="margin:0;padding:0;background-color:#f1f5f9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f1f5f9;padding:32px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;background-color:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #e2e8f0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
          <tr>
            <td style="background-color:#0f172a;padding:20px 32px;color:#5eead4;font-size:13px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;">
              {_escape(app_name)}
            </td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <h1 style="margin:0 0 12px;font-size:20px;color:#0f172a;">{heading}</h1>
              <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#475569;">{intro}</p>
              <table role="presentation" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="border-radius:10px;background-color:#0d9488;">
                    <a href="{button_url}" style="display:inline-block;padding:12px 28px;font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:10px;">{button_label}</a>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 8px;font-size:12px;line-height:1.6;color:#94a3b8;">{note}</p>
              <p style="margin:0;font-size:12px;line-height:1.6;color:#94a3b8;word-break:break-all;">
                Or paste this link into your browser:<br>
                <a href="{button_url}" style="color:#0d9488;">{_escape(button_url)}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 32px;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;">
              This is an automated message from {_escape(app_name)}. Please do not reply.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
