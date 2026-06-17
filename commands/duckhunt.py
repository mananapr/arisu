import asyncio
from datetime import datetime, timedelta, timezone
from random import randint
from typing import ClassVar

from signalbot import Context, regex_triggered
from signalbot.bot import SignalBot

from commands.help import CommandWithHelpMessage


class DuckHuntCommand(CommandWithHelpMessage):
    SPAWN_MIN_MINUTES = 60
    SPAWN_MAX_MINUTES = 180
    ACTIVE_WINDOW_SECONDS = 30

    _active_ducks: ClassVar[dict[str, datetime]] = {}
    _locks: ClassVar[dict[str, asyncio.Lock]] = {}

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
        for group in groups:
            if group not in cls._active_ducks:
                cls._schedule_next_spawn(bot, group)

    @classmethod
    def _schedule_next_spawn(cls, bot: SignalBot, group: str) -> None:
        delay_minutes = randint(cls.SPAWN_MIN_MINUTES, cls.SPAWN_MAX_MINUTES)
        run_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

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
        lock = cls._lock_for(group)

        async with lock:
            if group in cls._active_ducks:
                cls._schedule_next_spawn(bot, group)
                return

            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=cls.ACTIVE_WINDOW_SECONDS
            )
            cls._active_ducks[group] = expires_at

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
        lock = cls._lock_for(group)

        async with lock:
            if group not in cls._active_ducks:
                return

            cls._active_ducks.pop(group, None)

        await bot.send(group, "The duck got away...")
        cls._schedule_next_spawn(bot, group)

    async def _handle_bang(self, context: Context) -> None:
        group = context.message.recipient()
        shooter = str(context.message.source_uuid)
        lock = self._lock_for(group)
        response = ""

        async with lock:
            expires_at = self._active_ducks.get(group)

            if not expires_at:
                self._record_shot(context, shooter, kill=False)
                response = "BANG! You scared the air. Miss recorded."
            elif expires_at <= datetime.now(timezone.utc):
                self._active_ducks.pop(group, None)
                self._remove_job(context.bot, self._expire_job_id(group))
                self._record_shot(context, shooter, kill=False)
                self._schedule_next_spawn(context.bot, group)
                response = "Too late. The duck was already gone. Miss recorded."
            else:
                self._active_ducks.pop(group, None)
                self._remove_job(context.bot, self._expire_job_id(group))
                self._record_shot(context, shooter, kill=True)
                self._schedule_next_spawn(context.bot, group)
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
    def _lock_for(cls, group: str) -> asyncio.Lock:
        lock = cls._locks.get(group)

        if lock is None:
            lock = asyncio.Lock()
            cls._locks[group] = lock

        return lock

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
