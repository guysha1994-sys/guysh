from __future__ import annotations

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.screener import run_screener, save_screener_results
from app.universe import get_universe_tickers, refresh_universe

_scheduler: BackgroundScheduler | None = None


def run_daily_job(settings: Settings) -> None:
    try:
        refresh_universe(settings.db_path)
    except Exception:
        # כשלון רענון היוניברס משאיר את הרשימה השמורה האחרונה —
        # לא זורקים מתוך job מתוזמן.
        pass

    tickers = get_universe_tickers(settings.db_path)
    if not tickers:
        return

    results = run_screener(tickers)
    save_screener_results(settings.db_path, results, date.today())


def start_scheduler(settings: Settings) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/New_York")
    _scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri"),
        args=[settings],
        id="daily_screener",
    )
    _scheduler.start()
    return _scheduler
