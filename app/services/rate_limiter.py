from datetime import datetime, timezone
from app.db.session import db
from app.core.config import settings


class GlobalRateLimiter:
    """
    Tracks global daily API usage in MongoDB and enforces limits.
    This protects against IP rotation attacks by limiting total daily requests.
    """

    @staticmethod
    def _get_today_key() -> str:
        """Get today's date as a string key (UTC)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @classmethod
    async def get_daily_usage(cls) -> dict:
        """Get current daily usage stats."""
        today = cls._get_today_key()
        record = await db.rate_limits.find_one({"date": today})
        if not record:
            return {"date": today, "requests": 0, "limit_exceeded_notified": False}
        return record

    @classmethod
    async def check_and_increment(cls, request_type: str = "general") -> tuple[bool, int, int]:
        """
        Check if we're under the daily limit and increment the counter.

        Returns:
            tuple: (is_allowed, current_count, max_limit)
        """
        today = cls._get_today_key()
        max_requests = settings.GLOBAL_DAILY_REQUEST_LIMIT

        # Atomically increment and get the new count
        result = await db.rate_limits.find_one_and_update(
            {"date": today},
            {
                "$inc": {"requests": 1},
                "$setOnInsert": {"limit_exceeded_notified": False},
                "$push": {
                    "request_log": {
                        "type": request_type,
                        "timestamp": datetime.now(timezone.utc)
                    }
                }
            },
            upsert=True,
            return_document=True
        )

        current_count = result["requests"]
        is_allowed = current_count <= max_requests

        # If limit just exceeded and not yet notified, send notification
        if not is_allowed and not result.get("limit_exceeded_notified", False):
            await cls._mark_notified(today)
            await cls._send_limit_exceeded_notification(current_count, max_requests)

        return is_allowed, current_count, max_requests

    @classmethod
    async def _mark_notified(cls, date: str):
        """Mark that we've sent the notification for this day."""
        await db.rate_limits.update_one(
            {"date": date},
            {"$set": {"limit_exceeded_notified": True}}
        )

    @classmethod
    async def _send_limit_exceeded_notification(cls, current_count: int, max_limit: int):
        """Send email notification when limit is exceeded."""
        from app.services.notifications import EmailService

        await EmailService.send_limit_exceeded_alert(
            current_count=current_count,
            max_limit=max_limit
        )

    @classmethod
    async def get_remaining_requests(cls) -> int:
        """Get the number of remaining requests for today."""
        usage = await cls.get_daily_usage()
        remaining = settings.GLOBAL_DAILY_REQUEST_LIMIT - usage["requests"]
        return max(0, remaining)
