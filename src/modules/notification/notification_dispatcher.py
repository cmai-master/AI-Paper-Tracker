"""
Notification Dispatcher
Routes notifications to appropriate channels
"""
import logging
from typing import Dict
from datetime import datetime

from src.core.models import UserProfile, NotificationChannel
from .notification_services import EmailService, SlackService, PushService

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatch notifications to multiple channels"""

    def __init__(self):
        """Initialize notification dispatcher"""
        self.email_service = EmailService()
        self.slack_service = SlackService()
        self.push_service = PushService()

    async def dispatch(
        self,
        user: UserProfile,
        paper: Dict,
        relevance_score: float
    ) -> Dict[str, bool]:
        """
        Dispatch notification to user's configured channels

        Args:
            user: User profile
            paper: Paper information
            relevance_score: Relevance score (0-1)

        Returns:
            Dictionary of channel -> success status
        """
        # Check minimum relevance score
        if relevance_score < user.notification_settings.min_relevance_score:
            logger.debug(
                f"Paper {paper.get('id')} below threshold for user {user.user_id}"
            )
            return {}

        # Check quiet hours
        if self._is_quiet_hours(user):
            logger.info(f"Quiet hours for user {user.user_id}, queuing notification")
            # In production, this would queue the notification
            return {}

        # Format notification message
        message = self._format_notification(paper, relevance_score)

        # Send to each configured channel
        results = {}

        for channel in user.notification_settings.channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    if user.email:
                        success = await self.email_service.send(user.email, message)
                        results[channel.value] = success
                    else:
                        logger.warning(f"No email for user {user.user_id}")
                        results[channel.value] = False

                elif channel == NotificationChannel.SLACK:
                    slack_webhook = user.notification_settings.__dict__.get("slack_webhook")
                    if slack_webhook:
                        success = await self.slack_service.send(slack_webhook, message)
                        results[channel.value] = success
                    else:
                        logger.warning(f"No Slack webhook for user {user.user_id}")
                        results[channel.value] = False

                elif channel == NotificationChannel.PUSH:
                    success = await self.push_service.send(user.user_id, message)
                    results[channel.value] = success

            except Exception as e:
                logger.error(f"Notification failed for {channel}: {e}")
                results[channel.value] = False

        return results

    def _is_quiet_hours(self, user: UserProfile) -> bool:
        """Check if current time is in user's quiet hours"""
        current_hour = datetime.now().hour
        quiet_start, quiet_end = user.notification_settings.quiet_hours

        if quiet_start < quiet_end:
            # Normal range (e.g., 22-8 means 10 PM to 8 AM next day)
            return quiet_start <= current_hour < quiet_end
        else:
            # Wrap around midnight (e.g., 22-8)
            return current_hour >= quiet_start or current_hour < quiet_end

    def _format_notification(
        self,
        paper: Dict,
        score: float
    ) -> Dict:
        """Format notification message"""
        authors = paper.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in authors[:3]])
        if len(authors) > 3:
            author_names += " et al."

        return {
            "title": f"📄 New Paper: {paper.get('title', 'Untitled')[:60]}...",
            "relevance": f"{score*100:.0f}%",
            "authors": author_names,
            "abstract": paper.get("abstract", "")[:200] + "...",
            "url": paper.get("url", ""),
            "arxiv_id": paper.get("arxiv_id", ""),
            "published": paper.get("published_at", ""),
            "categories": ", ".join(paper.get("categories", [])[:3]),
            "actions": [
                {"label": "Read Paper", "url": paper.get("pdf_url", "")},
                {"label": "View on arXiv", "url": paper.get("url", "")},
                {"label": "Find Similar", "action": "find_similar"}
            ]
        }

    async def send_digest(
        self,
        user: UserProfile,
        papers: list,
        period: str = "daily"
    ) -> bool:
        """
        Send a digest of multiple papers

        Args:
            user: User profile
            papers: List of papers to include
            period: "daily" or "weekly"

        Returns:
            Success status
        """
        if not papers:
            logger.info(f"No papers for digest for user {user.user_id}")
            return False

        digest_message = {
            "title": f"📚 Your {period.capitalize()} Paper Digest",
            "period": period,
            "count": len(papers),
            "papers": [
                {
                    "title": p.get("title"),
                    "authors": ", ".join([a.get("name", "") for a in p.get("authors", [])[:2]]),
                    "relevance": f"{p.get('relevance_score', 0)*100:.0f}%",
                    "url": p.get("url")
                }
                for p in papers[:10]  # Limit to top 10
            ]
        }

        # Send digest via email (primary channel for digests)
        if user.email:
            try:
                success = await self.email_service.send_digest(user.email, digest_message)
                return success
            except Exception as e:
                logger.error(f"Digest sending failed: {e}")
                return False

        return False
