"""
Notification Services
Email, Slack, and Push notification implementations
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class EmailService:
    """Email notification service"""

    def __init__(self, smtp_config: Dict = None):
        """Initialize email service"""
        self.smtp_config = smtp_config or {
            "hostname": "smtp.gmail.com",
            "port": 587,
            "use_tls": True
        }

    async def send(self, to_email: str, message: Dict) -> bool:
        """Send email notification"""
        try:
            # Check if aiosmtplib is available
            try:
                import aiosmtplib
                from email.message import EmailMessage
            except ImportError:
                logger.warning("aiosmtplib not installed, email sending disabled")
                return False

            msg = EmailMessage()
            msg["From"] = "noreply@paperpulse.ai"
            msg["To"] = to_email
            msg["Subject"] = message["title"]

            # Create HTML email
            html = self._create_email_html(message)
            msg.set_content(html, subtype='html')

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_config["hostname"],
                port=self.smtp_config["port"],
                start_tls=self.smtp_config["use_tls"]
            )

            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False

    async def send_digest(self, to_email: str, digest: Dict) -> bool:
        """Send digest email"""
        try:
            try:
                import aiosmtplib
                from email.message import EmailMessage
            except ImportError:
                logger.warning("aiosmtplib not installed")
                return False

            msg = EmailMessage()
            msg["From"] = "noreply@paperpulse.ai"
            msg["To"] = to_email
            msg["Subject"] = digest["title"]

            # Create digest HTML
            html = self._create_digest_html(digest)
            msg.set_content(html, subtype='html')

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_config["hostname"],
                port=self.smtp_config["port"],
                start_tls=self.smtp_config["use_tls"]
            )

            logger.info(f"Digest sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Digest sending failed: {e}")
            return False

    def _create_email_html(self, message: Dict) -> str:
        """Create HTML email template"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9fafb; margin-top: 20px; border-radius: 5px; }}
                .relevance {{ color: #059669; font-weight: bold; }}
                .button {{ background: #2563eb; color: white; padding: 10px 20px;
                          text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{message['title']}</h2>
                </div>
                <div class="content">
                    <p><strong>Relevance Score:</strong> <span class="relevance">{message['relevance']}</span></p>
                    <p><strong>Authors:</strong> {message['authors']}</p>
                    <p><strong>Categories:</strong> {message.get('categories', 'N/A')}</p>
                    <p>{message['abstract']}</p>
                    <div style="margin-top: 20px;">
                        {"".join([f'<a href="{action.get("url", "#")}" class="button">{action["label"]}</a>'
                                  for action in message.get('actions', []) if action.get('url')])}
                    </div>
                </div>
                <div class="footer">
                    <p>You received this because you subscribed to PaperPulse notifications.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_digest_html(self, digest: Dict) -> str:
        """Create HTML digest template"""
        papers_html = ""
        for paper in digest.get("papers", []):
            papers_html += f"""
            <div style="padding: 15px; background: white; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2563eb;">
                <h3 style="margin-top: 0;">{paper['title']}</h3>
                <p><strong>Authors:</strong> {paper['authors']}</p>
                <p><strong>Relevance:</strong> <span style="color: #059669;">{paper['relevance']}</span></p>
                <a href="{paper['url']}" style="color: #2563eb;">Read Paper →</a>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{digest['title']}</h2>
                    <p>Found {digest['count']} relevant papers for you</p>
                </div>
                <div style="margin-top: 20px;">
                    {papers_html}
                </div>
            </div>
        </body>
        </html>
        """


class SlackService:
    """Slack notification service"""

    async def send(self, webhook_url: str, message: Dict) -> bool:
        """Send Slack notification"""
        try:
            try:
                import aiohttp
            except ImportError:
                logger.warning("aiohttp not installed, Slack notifications disabled")
                return False

            # Create Slack blocks
            payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": message["title"]
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Relevance:* {message['relevance']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Authors:* {message['authors']}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message["abstract"]
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": action["label"]
                                },
                                "url": action.get("url", ""),
                                "style": "primary" if i == 0 else "default"
                            }
                            for i, action in enumerate(message.get("actions", []))
                            if action.get("url")
                        ]
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent")
                        return True
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False


class PushService:
    """Push notification service (placeholder)"""

    async def send(self, user_id: str, message: Dict) -> bool:
        """Send push notification"""
        # This would integrate with a push notification service
        # like Firebase Cloud Messaging, OneSignal, etc.
        logger.info(f"Push notification would be sent to user {user_id}")
        logger.debug(f"Message: {message['title']}")

        # Placeholder implementation
        return True
