"""
Entry point for hotfix backfill stage 2 (survey + MRP extended frame),
USA only.

Meant to run inside one of several parallel ACI containers (up to
MAX_CONTAINERS in the calling workflow), each given a disjoint subset of the
target weeks via HOTFIX_WEEKS. Weeks within one container's subset are
processed one after another purely for simplicity — there's no correctness
reason they need to be sequential, since stage 2 for one week never depends
on stage 2 for any other week. The splitting-into-groups step lives in the
calling GitHub Actions workflow (hotfix-backfill-stage2.yml), not here.

Run locally (no Docker), for a single week or a manually-chosen subset:
    export $(cat .env | xargs)
    HOTFIX_WEEKS="2026-14,2026-19" python -m data_generation.hotfix_backfill_stage2_entry

Env variables:
    HOTFIX_WEEKS   comma-separated ISO weeks assigned to *this* container,
                   e.g. "2026-14,2026-19,2026-24"
    HOTFIX_FORCE   "true"/"false" — force rerun even if a week's stage-2
                   lock already exists (default: false)
    HOTFIX_MRP_ONLY "true"/"false" — skip the survey wave and run only the R
                   MRP step on each week's already-saved vote-choice panel
                   (default: false). Fails that week if the panel is missing.
                   Incomplete panels only log a warning (the completeness
                   hard stop is disabled).
    HOTFIX_RESUME  "true"/"false" — reuse each week's saved vote-choice panel
                   and generate only the rows whose vote is still empty, then
                   run MRP (default: false). Falls back to full generation
                   from the stage-1 biography panel when no saved vote panel
                   exists. Ignored if HOTFIX_MRP_ONLY is true.

Without MRP-only, each week in this container's subset must already have a
stage-1 biography-panel snapshot (see hotfix_backfill_stage1_entry.py) unless
resuming from a saved vote panel — this raises if the needed panel is missing
rather than silently skipping.

Unlike stage 1, a failure on one week does not stop the rest — weeks here
are independent, so this keeps going and reports every failure at the end.
"""
from __future__ import annotations

import logging
import os
import sys

from .run_scripts import check_r_available
from .hotfix_backfill_stage2 import run_stage2_week

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


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "false").strip().lower() in ("true", "1", "yes")


def main() -> None:
    raw_weeks = os.environ.get("HOTFIX_WEEKS", "").strip()
    if not raw_weeks:
        raise ValueError("HOTFIX_WEEKS env var is required, e.g. '2026-14,2026-19'.")
    force = _env_flag("HOTFIX_FORCE")
    mrp_only = _env_flag("HOTFIX_MRP_ONLY")
    resume = _env_flag("HOTFIX_RESUME")

    check_r_available()

    weeks = _parse_weeks(raw_weeks)
    if mrp_only:
        mode = "MRP only"
    elif resume:
        mode = "resume survey + MRP"
    else:
        mode = "survey + MRP"
    logger.info(
        "Hotfix backfill stage 2 (%s): %d week(s) assigned to this container: %s",
        mode, len(weeks), weeks,
    )

    failed: list[str] = []
    for year, week in weeks:
        label = f"{year}-{week:02d}"
        logger.info("=== Stage 2: %s %s ===", COUNTRY, label)
        try:
            run_stage2_week(COUNTRY, year, week, force=force, mrp_only=mrp_only, resume=resume)
        except Exception:
            logger.exception("Stage 2 failed for week %s — continuing with remaining weeks in this container.", label)
            failed.append(label)
            continue
        logger.info("=== Stage 2 done: %s %s ===", COUNTRY, label)

    if failed:
        logger.error("Hotfix backfill stage 2 finished with failures in this container: %s", failed)
        sys.exit(1)

    logger.info("Hotfix backfill stage 2 complete for all %d week(s) in this container.", len(weeks))


if __name__ == "__main__":
    main()
