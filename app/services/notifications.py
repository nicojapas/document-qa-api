import logging
from datetime import datetime, timezone
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email notifications for API alerts."""

    @classmethod
    async def send_limit_exceeded_alert(cls, current_count: int, max_limit: int):
        """
        Send an email alert when the global daily request limit is exceeded.
        """
        if not settings.SMTP_HOST or not settings.ALERT_EMAIL:
            logger.warning(
                "Email notification skipped: SMTP not configured. "
                f"Limit exceeded: {current_count}/{max_limit}"
            )
            return False

        subject = f"[Document QA API] Daily Request Limit Exceeded"
        body = f"""
Alert: Your Document QA API has exceeded its daily request limit.

Details:
- Date: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- Requests made: {current_count}
- Daily limit: {max_limit}

The API will reject all further requests until midnight UTC.

This may indicate:
1. Legitimate high usage
2. A potential abuse attempt (e.g., IP rotation attack)

Recommended actions:
- Review your MongoDB rate_limits collection for request patterns
- Check your server logs for suspicious activity
- Consider increasing the limit if usage is legitimate

--
Document QA API - Automated Alert
        """.strip()

        return await cls._send_email(
            to_email=settings.ALERT_EMAIL,
            subject=subject,
            body=body
        )

    @classmethod
    async def _send_email(cls, to_email: str, subject: str, body: str) -> bool:
        """Send an email using SMTP."""
        try:
            message = EmailMessage()
            message["From"] = settings.SMTP_FROM or settings.SMTP_USER
            message["To"] = to_email
            message["Subject"] = subject
            message.set_content(body)

            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )

            logger.info(f"Alert email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
