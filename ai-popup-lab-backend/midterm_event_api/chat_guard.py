'''
user limiting for the midterm event persona chat (replaces the old user_limiting/chat_limiting.py + ip_reset.py)

three protections, all checked in ChatGuard.try_start():
  1. one request at a time per client (server side, so it can't be bypassed from the frontend)
  2. daily message limit per client (default 25)
  3. daily message limit across ALL clients (default 1000)

counters live in a small JSON file so they survive restarts, and they reset
automatically at UTC midnight (no cron / ip_reset.py needed).
the "request in progress" slots are in memory only, so a crash can never lock someone out.
'''

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

PER_IP_DAILY_LIMIT = int(os.getenv("MIDTERM_IP_DAILY_LIMIT", "25"))
GLOBAL_DAILY_LIMIT = int(os.getenv("MIDTERM_GLOBAL_DAILY_LIMIT", "1000"))

# a request slot older than this is treated as stuck and freed (safety net)
STALE_SLOT_SECS = 180

IS_DEV = os.getenv("ENV") == "development"

if IS_DEV:
    STATE_PATH = Path(__file__).resolve().parent / "midterm_daily_usage.json"
else:
    # mounted files in deployment
    STATE_PATH = Path("/mnt/data/midterm_daily_usage.json")

# results of try_start
OK = "ok"
BUSY = "busy"
IP_LIMIT = "ip_limit"
GLOBAL_LIMIT = "global_limit"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class ChatGuard:
    def __init__(self, state_path=STATE_PATH, ip_limit=PER_IP_DAILY_LIMIT,
                 global_limit=GLOBAL_DAILY_LIMIT, bypass_limits=IS_DEV):
        self._lock = threading.Lock()
        self._path = Path(state_path)
        self.ip_limit = ip_limit
        self.global_limit = global_limit
        self.bypass_limits = bypass_limits  # dev: skip the daily limits, like the old 'dev-ip' behaviour

        self._active: dict[str, float] = {}  # client key -> time the request started
        self._day = _today()
        self._global_count = 0
        self._ip_counts: dict[str, int] = {}
        self._load()

    # --- persistence ---
    def _load(self):
        try:
            data = json.loads(self._path.read_text())
            if data.get("date") == self._day:
                self._global_count = int(data.get("global", 0))
                self._ip_counts = {str(k): int(v) for k, v in data.get("ips", {}).items()}
        except (OSError, ValueError, AttributeError):
            pass  # missing or corrupt file -> start the day from zero

    def _save(self):
        payload = {"date": self._day, "global": self._global_count, "ips": self._ip_counts}
        try:
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload))
            os.replace(tmp, self._path)  # atomic, so a crash can't leave a half-written file
        except OSError as error:
            print(f"chat_guard: could not save usage file: {error}")

    def _roll_day(self):
        today = _today()
        if today != self._day:
            self._day = today
            self._global_count = 0
            self._ip_counts = {}
            self._save()

    # --- public API ---
    def try_start(self, key: str) -> str:
        """Reserve a request slot and count the message. Returns OK, BUSY, IP_LIMIT or GLOBAL_LIMIT.
        Only call finish(key) if this returned OK."""
        with self._lock:
            self._roll_day()
            now = time.monotonic()

            started = self._active.get(key)
            if started is not None and now - started < STALE_SLOT_SECS:
                return BUSY

            if not self.bypass_limits:
                if self._ip_counts.get(key, 0) >= self.ip_limit:
                    return IP_LIMIT
                if self._global_count >= self.global_limit:
                    return GLOBAL_LIMIT
                self._ip_counts[key] = self._ip_counts.get(key, 0) + 1
                self._global_count += 1
                self._save()

            self._active[key] = now
            return OK

    def finish(self, key: str):
        with self._lock:
            self._active.pop(key, None)

    def snapshot(self) -> dict:
        with self._lock:
            self._roll_day()
            return {
                "per_ip_daily_limit": self.ip_limit,
                "global_daily_limit": self.global_limit,
                "global_used_today": self._global_count,
                "distinct_ips_today": len(self._ip_counts),
                "requests_in_progress": len(self._active),
            }


guard = ChatGuard()
