"""
Backfill entry point — sequentially runs the panel generation cycle
(attrition -> biographies -> survey) and/or MRP frame extension for a set of
countries across a set of ISO weeks, entirely on the backfill storage track
(see azure_storage_utils.get_backfill_active_panel_path and friends) so a
backfill run never touches live production panel state.

Run with: python -m data_generation.backfill_entry

Env variables:
    COUNTRIES       comma-separated country names, e.g. "usa" or "usa,sweden"
    BACKFILL_WEEKS  comma-separated ISO weeks, e.g. "2026-20,2026-21,2026-22"
    JOB_TYPE        panel | mrp | both   (default: panel)
    BACKFILL_FORCE  true | false         (default: false)

Weeks for a given country are always processed in chronological order,
regardless of the order they're listed in BACKFILL_WEEKS — each backfilled
week depends on the panel state left behind by the previous one, so this
must never be parallelized across weeks for the same country. Different
countries are independent of each other and are simply processed one after
another here (see run_job.py for the equivalent weekly-job country loop).

If a week fails for a given country, later weeks for that same country are
skipped (their input state would be stale/incomplete) — the run moves on to
the next country instead. Other countries are unaffected.

Job locks live inside the per-job functions: generate_panel_results_backfill
writes its "panel_backfill" lock only after a successful run, and skips both
the run and the lock entirely for countries with no panel configured — a
lock without results would wedge the downstream MRP step. _run_mrp locks
under "mrp_backfill" the same way.
"""
from __future__ import annotations

import logging
import os
import sys

from .generate_panel_results import generate_panel_results_backfill
from .run_scripts import check_r_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

COUNTRIES = [c.strip() for c in os.environ.get("COUNTRIES", "usa").split(",") if c.strip()]
JOB_TYPE = os.environ.get("JOB_TYPE", "panel").lower()
FORCE = os.environ.get("BACKFILL_FORCE", "false").lower() == "true"

_RAW_WEEKS = os.environ.get("BACKFILL_WEEKS", "")


def _parse_weeks(raw: str) -> list[tuple[int, int]]:
    """Parse "2026-20,2026-21" -> [(2026, 20), (2026, 21)], sorted chronologically."""
    result = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split("-")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid week format: '{token}'. Expected YYYY-WW (e.g. 2026-20)."
            )
        result.append((int(parts[0]), int(parts[1])))
    return sorted(result)


def main() -> None:
    weeks = _parse_weeks(_RAW_WEEKS)
    if not weeks:
        logger.error("No weeks provided. Set BACKFILL_WEEKS=YYYY-WW[,YYYY-WW,...]")
        sys.exit(1)

    if JOB_TYPE in ("mrp", "both"):
        check_r_available()
        # Imported lazily so panel-only backfills never require run_job.py's
        # R/MRP dependencies to be importable.
        from .run_job import _run_mrp

    failed: list[str] = []

    for country in COUNTRIES:
        logger.info(
            "Backfilling %s across %d week(s): %s [job_type=%s, force=%s]",
            country, len(weeks), ", ".join(f"{y}-W{w:02d}" for y, w in weeks), JOB_TYPE, FORCE,
        )
        for year, week in weeks:
            label = f"{country} {year}-W{week:02d}"
            try:
                if JOB_TYPE in ("panel", "both"):
                    generate_panel_results_backfill(
                        country=country, year=year, week=week, force=FORCE,
                    )

                if JOB_TYPE in ("mrp", "both"):
                    _run_mrp(country=country, year=year, week=week, backfill=True, force=FORCE)

                logger.info("Done: %s", label)
            except Exception:
                logger.exception("Failed: %s — stopping this country's backfill here.", label)
                failed.append(label)
                # Later weeks for this country depend on this week's panel
                # state, so there's no safe way to continue past a failure —
                # move on to the next country instead.
                break

    if failed:
        logger.error("Backfill finished with failures: %s", failed)
        sys.exit(1)
    else:
        logger.info("Backfill complete.")


if __name__ == "__main__":
    main()
