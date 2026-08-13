"""Poll due future-visit reminders and fire ntfy pushes (Phase 0 / FR-P14).

Usage:
    python -m project.workers.reminder_worker --once
    python -m project.workers.reminder_worker

Env:
    REMINDER_POLL_SECONDS  sleep between ticks (default 60)
    REMINDER_DUE_DAYS      due window in days (default 7)
"""

from __future__ import annotations

import argparse
import logging
import os
import time

from project.agents import reminders
from project.db.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("medbridge.reminder_worker")


def tick(days: int) -> int:
    sent = reminders.process_due(days=days)
    if sent:
        logger.info("Fired %s reminder push(es)", sent)
    else:
        logger.debug("No due reminders")
    return sent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MedBridge AI reminder worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process due reminders once and exit (for demos/CI)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("REMINDER_DUE_DAYS", "7")),
        help="Due window in days (default 7)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("REMINDER_POLL_SECONDS", "60")),
        help="Seconds between polls when looping (default 60)",
    )
    args = parser.parse_args(argv)

    init_db(seed=True)
    if args.once:
        tick(args.days)
        return 0

    logger.info("Reminder worker started (interval=%ss, days=%s)", args.interval, args.days)
    while True:
        try:
            tick(args.days)
        except Exception:
            logger.exception("Reminder tick failed")
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
