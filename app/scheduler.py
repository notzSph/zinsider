from __future__ import annotations

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.modules.config import get_settings
from app.main import run_daily_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def start_scheduler() -> None:
    settings = get_settings()

    if settings["run_on_start"]:
        logging.info("RUN_ON_START enabled; running job immediately.")
        try:
            run_daily_scan()
        except Exception:
            logging.exception("Immediate run failed")

    scheduler = BlockingScheduler(timezone=settings["ny_timezone"])

    trigger = CronTrigger(
        day_of_week=settings["schedule_dow"],
        hour=settings["schedule_hour"],
        minute=settings["schedule_minute"],
        timezone=settings["ny_timezone"],
    )

    scheduler.add_job(
        run_daily_scan,
        trigger=trigger,
        id="inside_day_scan",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=6 * 60 * 60,
    )

    logging.info(
        "Scheduled scan: %s %02d:%02d (%s)",
        settings["schedule_dow"],
        settings["schedule_hour"],
        settings["schedule_minute"],
        settings["ny_timezone"],
    )

    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
