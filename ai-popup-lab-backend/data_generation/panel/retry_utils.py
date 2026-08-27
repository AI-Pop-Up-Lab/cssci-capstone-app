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
    **kwargs,
) -> T:
    """
    Call `func(*args, **kwargs)`, retrying up to `max_attempts` times with
    exponential backoff (base_delay * 2**attempt, capped at max_delay) on any
    exception matching `retry_on`. Raises RetryExhausted if every attempt
    fails.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except retry_on as exc:
            last_exc = exc
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                getattr(func, "__name__", repr(func)), attempt, max_attempts, exc, delay,
            )
            time.sleep(delay)

    raise RetryExhausted(getattr(func, "__name__", repr(func)), max_attempts, last_exc)


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
