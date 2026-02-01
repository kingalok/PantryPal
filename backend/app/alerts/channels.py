"""
Alert channels: Telegram (Bot API), Email (SMTP). Pluggable.
"""
import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx

# Optional aiosmtplib for email
try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    HAS_SMTP = True
except ImportError:
    HAS_SMTP = False


class AlertChannel(ABC):
    @abstractmethod
    async def send(self, subject: str, body: str, recipient: str) -> bool:
        """Return True if sent successfully."""
        ...


class TelegramChannel(AlertChannel):
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")

    async def send(self, subject: str, body: str, recipient: str) -> bool:
        if not self.bot_token or not recipient:
            return False
        chat_id = recipient.strip()
        text = f"*{subject}*\n\n{body}" if subject else body
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    url,
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                    timeout=10.0,
                )
                return r.status_code == 200
        except Exception:
            return False


class EmailChannel(AlertChannel):
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_addr: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
        self.smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD", "")
        self.from_addr = from_addr or os.environ.get("ALERT_FROM_EMAIL", self.smtp_user)

    async def send(self, subject: str, body: str, recipient: str) -> bool:
        if not HAS_SMTP or not self.smtp_host or not recipient:
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = recipient.strip()
            msg.attach(MIMEText(body, "plain"))
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user or None,
                password=self.smtp_password or None,
                use_tls=True,
            )
            return True
        except Exception:
            return False


def get_telegram_channel() -> TelegramChannel:
    return TelegramChannel()


def get_email_channel() -> EmailChannel:
    return EmailChannel()
