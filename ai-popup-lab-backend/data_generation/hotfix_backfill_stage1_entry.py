"""
Entry point for hotfix backfill stage 1 (attrition + biography), USA only.

Meant to run inside a single ACI container. Weeks are processed strictly
in the order given, one after another — never reordered, never
parallelized — because attrition for week N reads whatever week N-1 left
in `get_hotfix_backfill_active_panel_path("usa")`.

Run locally (no Docker):
    export $(cat .env | xargs)
    HOTFIX_WEEKS="2026-14,2026-15,2026-16" python -m data_generation.hotfix_backfill_stage1_entry

Env variables:
    HOTFIX_WEEKS   comma-separated ISO weeks, oldest first, e.g.
                   "2026-14,2026-15,2026-16,2026-17,2026-18,2026-19,2026-20,
                    2026-21,2026-22,2026-23,2026-24"
    HOTFIX_FORCE   "true"/"false" — force rerun even if a week's stage-1
                   lock already exists (default: false)

Before the very first run, seed hotfix_backfill's active-panel blob
(`get_hotfix_backfill_active_panel_path("usa")`) with a genuine
week-(t-1) panel — e.g. a copy of the production active panel, or the
production historical panel for the week immediately before the first
week in HOTFIX_WEEKS. This script never does that seeding itself; if the
blob is missing it will cold-start a brand-new panel instead, which is
usually not what you want for a backfill.

On failure, this stops immediately rather than skipping ahead to the next
week — every later week depends on the failed week's output, so
continuing past it would silently corrupt the sequence.
"""
from __future__ import annotations

import logging
import os
import sys

from .hotfix_backfill_stage1 import run_stage1_week

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

COUNTRY = "usa"


def _parse_weeks(raw: str) -> list[tuple[int, int]]:
    weeks = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        year_str, week_str = part.split("-")
        weeks.append((int(year_str), int(week_str)))
    return weeks


def main() -> None:
    raw_weeks = os.environ.get("HOTFIX_WEEKS", "").strip()
    if not raw_weeks:
        raise ValueError(
            "HOTFIX_WEEKS env var is required, e.g. '2026-14,2026-15,2026-16' (oldest first)."
        )
    force = os.environ.get("HOTFIX_FORCE", "false").strip().lower() in ("true", "1", "yes")

    weeks = _parse_weeks(raw_weeks)
    logger.info("Hotfix backfill stage 1: %d week(s) in order: %s", len(weeks), weeks)

    for year, week in weeks:
        label = f"{year}-{week:02d}"
        logger.info("=== Stage 1: %s %s ===", COUNTRY, label)
        try:
            run_stage1_week(COUNTRY, year, week, force=force)
        except Exception:
            logger.exception(
                "Stage 1 failed for week %s — stopping here. Later weeks depend on this "
                "one's output, so they cannot safely be attempted.",
                label,
            )
            sys.exit(1)
        logger.info("=== Stage 1 done: %s %s ===", COUNTRY, label)

    logger.info("Hotfix backfill stage 1 complete for all %d week(s).", len(weeks))


if __name__ == "__main__":
    main()
