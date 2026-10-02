"""
Shared retry helper for network/LLM calls (Azure OpenAI, Cohere, GDELT
downloads, article scraping). Every external call in the panel generation
pipeline should be wrapped with `retry_call` (or the `@with_retry` decorator)
rather than hand-rolling its own attempt loop, so the retry policy — max 5
attempts, exponential backoff — stays consistent across the whole pipeline.

Callers that want a row/persona to be skipped-and-logged rather than the
whole run aborted should catch `RetryExhausted` specifically at the
per-row/per-persona level (see panel.biography.populate_panel and
panel.runner.run_survey).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 30.0


class RetryExhausted(RuntimeError):
    """Raised when a wrapped call has failed on every one of its attempts."""

    def __init__(self, func_name: str, attempts: int, last_exc: BaseException):
        super().__init__(f"{func_name} failed after {attempts} attempts: {last_exc}")
        self.func_name = func_name
        self.attempts = attempts
        self.last_exc = last_exc


def retry_call(
    func: Callable[..., T],
    *args,
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    max_delay: float = MAX_DELAY_SECONDS,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    should_retry: Callable[[BaseException], bool] | None = None,
    **kwargs,
) -> T:
    """
    Call `func(*args, **kwargs)`, retrying up to `max_attempts` times with
    exponential backoff (base_delay * 2**attempt, capped at max_delay) on any
    exception matching `retry_on`. Raises RetryExhausted if every attempt
    fails.

    `should_retry`, if given, is called with each caught exception; if it
    returns False, the call fails immediately (as RetryExhausted) without
    burning through the remaining attempts/backoff delay. Use this for
    errors that are known to be permanent (e.g. HTTP 404/403) rather than
    transient — retrying those wastes time for no chance of success.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except retry_on as exc:
            last_exc = exc
            if should_retry is not None and not should_retry(exc):
                logger.warning(
                    "%s failed with a non-retryable error on attempt %d: %s — giving up immediately.",
                    getattr(func, "__name__", repr(func)), attempt, exc,
                )
                break
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                getattr(func, "__name__", repr(func)), attempt, max_attempts, exc, delay,
            )
            time.sleep(delay)

    raise RetryExhausted(getattr(func, "__name__", repr(func)), attempt, last_exc)


def with_retry(
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    max_delay: float = MAX_DELAY_SECONDS,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
):
    """Decorator form of retry_call, for wrapping a function definition directly."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapped(*args, **kwargs) -> T:
            return retry_call(
                func, *args,
                max_attempts=max_attempts, base_delay=base_delay, max_delay=max_delay,
                retry_on=retry_on, **kwargs,
            )

        wrapped.__name__ = getattr(func, "__name__", "wrapped")
        wrapped.__wrapped__ = func
        return wrapped

    return decorator


_HTTP_STATUS_RE = re.compile(r"\b(\d{3})\s+Client Error\b")


def is_permanent_http_error(exc: BaseException) -> bool:
    """
    should_retry predicate: returns False (don't retry) for HTTP 4xx errors
    that are permanent — the request will never succeed no matter how many
    times it's retried (404 Not Found, 403 Forbidden, 406 Not Acceptable,
    410 Gone, etc). 429 (Too Many Requests) is excluded since that's rate
    limiting, a transient condition worth retrying. Anything else (network
    errors, timeouts, 5xx, or an exception whose message doesn't mention a
    status code at all) returns True — retry as normal.

    Matches on the exception's message text via regex rather than a
    specific exception type/attribute, since requests.HTTPError and
    newspaper3k's wrapped download exceptions don't share an exception
    hierarchy, but both embed the status code in their message the same way
    ("403 Client Error: ...", "404 Client Error: ...") — confirmed against
    production logs.
    """
    match = _HTTP_STATUS_RE.search(str(exc))
    if not match:
        return True
    status = int(match.group(1))
    if status == 429:
        return True
    if 400 <= status < 500:
        return False
    return True
