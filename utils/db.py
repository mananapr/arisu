from datetime import datetime, timezone
from signalbot.bot import SignalBot
from signalbot.storage import SQLiteStorage

from commands.reminder import ReminderCommand

INIT_SQL = """
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        text TEXT NOT NULL,
        ts TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS seen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        ts TEXT NOT NULL,
        last_text TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tell (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        target TEXT NOT NULL,
        message TEXT NOT NULL,
        ts TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receiver TEXT NOT NULL,
        member TEXT NOT NULL,
        message TEXT NOT NULL,
        run_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS duckhunt_stats (
        group_id TEXT NOT NULL,
        player_uuid TEXT NOT NULL,
        kills INTEGER NOT NULL DEFAULT 0,
        misses INTEGER NOT NULL DEFAULT 0,
        last_kill_at TEXT,
        PRIMARY KEY (group_id, player_uuid)
    );
"""


def init_db(bot: SignalBot):
    store: SQLiteStorage = bot.storage  # type: ignore
    store._sqlite.executescript(INIT_SQL)
    store._sqlite.commit()

    rows = store._sqlite.execute(
        "SELECT receiver, member, message, run_at FROM reminders"
    ).fetchall()

    for receiver, member, message, run_at in rows:
        run_at_dt = datetime.fromisoformat(run_at)

        if run_at_dt > datetime.now(timezone.utc):
            bot.scheduler.add_job(
                ReminderCommand()._send_reminder,
                "date",
                run_date=run_at_dt,
                args=[bot, member, receiver, message],
            )
