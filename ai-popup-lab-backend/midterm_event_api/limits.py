"""
Daily message limit per visitor: EFFECTIVELY DISABLED FOR THE EVENT.

FLAG: the limit defaults to 10,000 messages per IP address per day (MIDTERM_DAILY_MESSAGE_LIMIT),
which in practice means no limit. This is deliberate: the chat is for an in-person event, and
everyone on the venue Wi-Fi shares one public IP address, so a realistic per-IP limit (the old
chat used 25 a day) would block the whole room after a few messages.

If this API stays public after the event, lower MIDTERM_DAILY_MESSAGE_LIMIT, ideally together
with a per-browser session ID so people sharing a network don't share a limit.

The counts are kept in memory: they reset at midnight UTC and when the app restarts. This does
not use the old chat's file-based limiter in user_limiting/.
"""

from datetime import date, datetime, timezone

from fastapi import Request


class DailyLimiter:
    def __init__(self):
        self._day = None
        self._counts = {}

    def allow(self, client_key: str, limit: int, today: date | None = None) -> bool:
        """Count one message for `client_key`; return False if they are over today's limit."""
        today = today or datetime.now(timezone.utc).date()
        if today != self._day:
            self._day = today
            self._counts = {}

        count = self._counts.get(client_key, 0)
        if count >= limit:
            return False
        self._counts[client_key] = count + 1
        return True

    def reset(self):
        self._day = None
        self._counts = {}


limiter = DailyLimiter()


def client_key(request: Request) -> str:
    # Azure App Service puts the visitor's IP first in X-Forwarded-For, sometimes with a port
    # ("1.2.3.4:56789") that changes per connection, so the port is dropped
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
        if ip.startswith("["):
            return ip[1:].split("]")[0]
        if ip.count(":") == 1:
            return ip.split(":")[0]
        return ip
    return request.client.host if request.client else "unknown"
