from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.screener import run_screener, save_screener_results
from app.universe import get_universe_tickers, refresh_universe

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_daily_job(settings: Settings) -> None:
    try:
        refresh_universe(settings.db_path)
    except Exception as exc:
        # כשלון רענון היוניברס משאיר את הרשימה השמורה האחרונה —
        # לא זורקים מתוך job מתוזמן.
        logger.warning("Universe refresh failed, keeping previously stored list: %s", exc)

    tickers = get_universe_tickers(settings.db_path)
    if not tickers:
        logger.warning("No universe tickers available; skipping screener run")
        return

    results = run_screener(tickers)
    save_screener_results(settings.db_path, results, date.today())
    logger.info(
        "Daily screener run complete: screened %d tickers, saved %d results",
        len(tickers),
        len(results),
    )


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/New_York")
    _scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri", timezone="America/New_York"),
        args=[settings],
        id="daily_screener",
    )
    _scheduler.start()
    return _scheduler


if __name__ == "__main__":
    from app.config import Settings

    run_daily_job(Settings.from_env())
