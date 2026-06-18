import asyncio
from datetime import datetime, timedelta, timezone
from random import randint
from typing import ClassVar
from zoneinfo import ZoneInfo

from signalbot import Context, regex_triggered
from signalbot.bot import SignalBot

from commands.help import CommandWithHelpMessage


class DuckHuntCommand(CommandWithHelpMessage):
    SPAWN_MIN_MINUTES = 20
    SPAWN_MAX_MINUTES = 60
    ACTIVE_WINDOW_SECONDS = 90
    QUIET_HOURS_TZ = ZoneInfo("Asia/Kolkata")
    QUIET_HOURS_START = 1
    QUIET_HOURS_END = 7

    _active_until: ClassVar[datetime | None] = None
    _active_recipient: ClassVar[str | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def help_message(self) -> str:
        return "duckhunt: random ducks appear - use /bang, /duckstats."

    @regex_triggered(r"^/(bang|duckstats)$")
    async def handle(self, context: Context) -> None:
        text = (context.message.text or "").strip()

        if text == "/bang":
            await self._handle_bang(context)
            return

        await self._handle_stats(context)

    @classmethod
    def schedule_spawns(cls, bot: SignalBot, groups: list[str]) -> None:
        if groups:
            cls._schedule_next_spawn(bot, groups[0])

    @classmethod
    def _schedule_next_spawn(cls, bot: SignalBot, group: str) -> None:
        delay_minutes = randint(cls.SPAWN_MIN_MINUTES, cls.SPAWN_MAX_MINUTES)
        run_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
        run_at = cls._next_allowed_spawn_time(run_at)

        bot.scheduler.add_job(
            cls._spawn_duck,
            "date",
            run_date=run_at,
            args=[bot, group],
            id=cls._spawn_job_id(group),
            replace_existing=True,
        )

    @classmethod
    async def _spawn_duck(cls, bot: SignalBot, group: str) -> None:
        async with cls._lock:
            if cls._active_until is not None:
                cls._schedule_next_spawn(bot, group)
                return

            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=cls.ACTIVE_WINDOW_SECONDS
            )
            cls._active_until = expires_at
            cls._active_recipient = group

            bot.scheduler.add_job(
                cls._expire_duck,
                "date",
                run_date=expires_at,
                args=[bot, group],
                id=cls._expire_job_id(group),
                replace_existing=True,
            )

        await bot.send(group, "A wild duck appears! /bang")

    @classmethod
    async def _expire_duck(cls, bot: SignalBot, group: str) -> None:
        async with cls._lock:
            if cls._active_until is None:
                return

            cls._active_until = None
            cls._active_recipient = None

        await bot.send(group, "The duck got away...")
        cls._schedule_next_spawn(bot, group)

    async def _handle_bang(self, context: Context) -> None:
        recipient = context.message.recipient()
        shooter = str(context.message.source_uuid)
        response = ""

        async with self._lock:
            expires_at = self._active_until

            if not expires_at:
                self._record_shot(context, shooter, kill=False)
                response = "BANG! You scared the air. Miss recorded."
            elif expires_at <= datetime.now(timezone.utc):
                active_recipient = self._active_recipient or recipient
                self._active_until = None
                self._active_recipient = None
                self._remove_job(context.bot, self._expire_job_id(active_recipient))
                self._record_shot(context, shooter, kill=False)
                self._schedule_next_spawn(context.bot, active_recipient)
                response = "Too late. The duck was already gone. Miss recorded."
            elif self._active_recipient != recipient:
                self._record_shot(context, shooter, kill=False)
                response = "BANG! You scared the air. Miss recorded."
            else:
                active_recipient = self._active_recipient or recipient
                self._active_until = None
                self._active_recipient = None
                self._remove_job(context.bot, self._expire_job_id(active_recipient))
                self._record_shot(context, shooter, kill=True)
                self._schedule_next_spawn(context.bot, active_recipient)
                response = "🦆💥 Nice shot!"

        await context.reply(response)

    async def _handle_stats(self, context: Context) -> None:
        group = context.message.recipient()
        db = context.bot.storage._sqlite  # type: ignore

        rows = db.execute(
            """
            SELECT player_uuid, kills, misses
            FROM duckhunt_stats
            WHERE group_id = ?
            ORDER BY kills DESC, misses ASC, player_uuid ASC
            LIMIT 10
            """,
            (group,),
        ).fetchall()

        if not rows:
            await context.reply("No duckhunt stats yet.")
            return

        lines = ["🦆 *Duckhunt leaderboard*", ""]
        mentions = []

        for idx, (player_uuid, kills, misses) in enumerate(rows, start=1):
            accuracy = 0
            total_shots = kills + misses

            if total_shots:
                accuracy = round((kills / total_shots) * 100)

            line = f"{idx}. hunter - {kills} kills, {misses} misses, {accuracy}%"
            start = len("\n".join(lines)) + 1 + len(f"{idx}. ")
            lines.append(line)
            mentions.append({"author": player_uuid, "start": start, "length": 6})

        await context.send("\n".join(lines), text_mode="styled", mentions=mentions)

    def _record_shot(self, context: Context, shooter: str, kill: bool) -> None:
        group = context.message.recipient()
        db = context.bot.storage._sqlite  # type: ignore
        now = datetime.now(timezone.utc).isoformat()

        db.execute(
            """
            INSERT INTO duckhunt_stats (group_id, player_uuid, kills, misses, last_kill_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(group_id, player_uuid)
            DO UPDATE SET
                kills = kills + excluded.kills,
                misses = misses + excluded.misses,
                last_kill_at = CASE
                    WHEN excluded.last_kill_at IS NOT NULL THEN excluded.last_kill_at
                    ELSE duckhunt_stats.last_kill_at
                END
            """,
            (group, shooter, 1 if kill else 0, 0 if kill else 1, now if kill else None),
        )
        db.commit()

    @classmethod
    def _next_allowed_spawn_time(cls, run_at: datetime) -> datetime:
        local_time = run_at.astimezone(cls.QUIET_HOURS_TZ)

        if cls.QUIET_HOURS_START <= local_time.hour < cls.QUIET_HOURS_END:
            local_time = local_time.replace(
                hour=cls.QUIET_HOURS_END,
                minute=0,
                second=0,
                microsecond=0,
            )

        return local_time.astimezone(timezone.utc)

    @staticmethod
    def _spawn_job_id(group: str) -> str:
        return f"duckhunt_spawn:{group}"

    @staticmethod
    def _expire_job_id(group: str) -> str:
        return f"duckhunt_expire:{group}"

    @staticmethod
    def _remove_job(bot: SignalBot, job_id: str) -> None:
        try:
            bot.scheduler.remove_job(job_id)
        except Exception:
            pass
