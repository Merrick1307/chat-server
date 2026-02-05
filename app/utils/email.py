import logging
from pathlib import Path
from typing import Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import SecretStr

from app.utils.config import (
    MAIL_FROM, MAIL_USERNAME, MAIL_PORT, MAIL_SERVER,
    MAIL_PASSWORD, MAIL_STARTTLS, MAIL_SSL_TLS, CLIENT_BASE_URL
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

mail_config: Optional[ConnectionConfig] = None


# def _get_tls_settings(port: int, starttls: bool, ssl_tls: bool) -> tuple[bool, bool]:
#     """
#     Determine correct TLS settings based on port and configuration.
#
#     Port 465: Use SSL/TLS from start (MAIL_SSL_TLS=True, MAIL_STARTTLS=False)
#     Port 587: Use STARTTLS upgrade (MAIL_SSL_TLS=False, MAIL_STARTTLS=True)
#
#     Note: MAIL_SSL_TLS and MAIL_STARTTLS cannot both be True in fastapi-mail.
#     """
#     if ssl_tls and starttls:
#         logger.warning("Both MAIL_SSL_TLS and MAIL_STARTTLS are True. Using port-based defaults.")
#         if port == 465:
#             return True, False
#         else:
#             return False, True
#
#     if port == 465 and not ssl_tls:
#         logger.info("Port 465 detected, enabling SSL/TLS")
#         return True, False
#
#     if port == 587 and not starttls:
#         logger.info("Port 587 detected, enabling STARTTLS")
#         return False, True
#
#     return ssl_tls, starttls


if MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM:
    # use_ssl, use_starttls = _get_tls_settings(MAIL_PORT, MAIL_STARTTLS, MAIL_SSL_TLS)
    #
    # logger.info(
    #     f"Email config: server={MAIL_SERVER}, port={MAIL_PORT}, "
    #     f"ssl_tls={use_ssl}, starttls={use_starttls}"
    # )
    
    mail_config = ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=SecretStr(MAIL_PASSWORD),
        MAIL_FROM=MAIL_FROM,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_SSL_TLS=MAIL_SSL_TLS,
        MAIL_STARTTLS=MAIL_STARTTLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )


def _load_template(template_name: str) -> Optional[str]:
    """Load HTML template from templates directory."""
    template_path = TEMPLATES_DIR / template_name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    logger.warning(f"Template {template_name} not found, using fallback")
    return None


def _build_password_reset_email_html(first_name: str, reset_url: str) -> str:
    """Build HTML content for password reset email from template."""
    template = _load_template("password_reset.html")
    
    if template:
        return template.replace("{{first_name}}", first_name).replace("{{reset_url}}", reset_url)
    
    # Fallback if template not found
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body>
        <h2>Password Reset Request</h2>
        <p>Hello {first_name},</p>
        <p>Click the link below to reset your password:</p>
        <a href="{reset_url}">Reset Password</a>
        <p>This link expires in 1 hour.</p>
    </body>
    </html>
    """


def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    import secrets
    return secrets.token_urlsafe(32)


async def send_password_reset_email(
    first_name: str,
    last_name: str,
    user_email: str,
    user_id: str,
    token: str
) -> bool:
    """
    Send password reset email to user.
    
    Args:
        first_name: User's first name
        last_name: User's last name  
        user_email: Email address to send to
        user_id: User's ID
        token: Pre-generated reset token (stored in Redis by caller)
    
    Returns True if email was sent successfully, False otherwise.
    """
    if not mail_config:
        logger.warning("Email not configured. Cannot send password reset email.")
        return False
    
    reset_url = f"{CLIENT_BASE_URL}/reset-password.html?token={token}"
    
    msg = MessageSchema(
        body=_build_password_reset_email_html(first_name, reset_url),
        subject="Reset your password - Punch Chat",
        recipients=[user_email],
        subtype=MessageType.html
    )
    
    try:
        fastmail = FastMail(config=mail_config)
        await fastmail.send_message(msg)
        logger.info(f"Password reset email sent to {user_email}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "SMTP AUTH extension" in error_msg or "STARTTLS" in error_msg:
            logger.error(
                f"Failed to send password reset email: {e}, "
                f"check your credentials or email service configuration"
            )
            logger.info(
                f"Current mail config: server={mail_config.MAIL_SERVER}, "
                f"port={mail_config.MAIL_PORT}, ssl_tls={mail_config.MAIL_SSL_TLS}, "
                f"starttls={mail_config.MAIL_STARTTLS}"
            )
        else:
            logger.error(f"Failed to send password reset email: {e}")
        return False


def is_email_configured() -> bool:
    """Check if email is properly configured."""
    return mail_config is not None
