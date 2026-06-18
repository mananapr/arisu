from dataclasses import dataclass
from random import randint
from typing import ClassVar

from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


@dataclass
class DuelState:
    challenger: str
    challenged: str
    turn: str
    bullet_index: int
    chamber_index: int = 0
    accepted: bool = False


class RouletteCommand(CommandWithHelpMessage):
    _duel_state: ClassVar[DuelState | None] = None

    def help_message(self) -> str:
        return "roulette: 🎲 /roulette or /roulette @user, /roulettestats."

    @regex_triggered(r"^/(roulette|roulettestats)(?:\s+.+)?$")
    async def handle(self, context: Context) -> None:
        text = (context.message.text or "").strip()

        if text.startswith("/roulettestats"):
            await self._handle_stats(context)
            return

        if text == "/roulette decline":
            await self._decline_duel(context)
            return

        mentions = context.message.mentions
        if mentions:
            await self._start_duel(context)
            return

        await self._spin(context)

    async def _start_duel(self, context: Context) -> None:
        if self._duel_state is not None:
            await context.reply("A roulette challenge is already in progress.")
            return

        challenger = str(context.message.source_uuid)
        challenged = str(context.message.mentions[0]["uuid"])

        if challenger == challenged:
            await context.reply("You can't challenge yourself.")
            return

        self._duel_state = DuelState(
            challenger=challenger,
            challenged=challenged,
            turn=challenged,
            bullet_index=randint(0, 5),
        )

        await context.send(
            "name challenged name to roulette. name goes first. "
            "Use /roulette to accept or /roulette decline.",
            mentions=[
                {"author": challenger, "start": 0, "length": 4},
                {"author": challenged, "start": 15, "length": 4},
                {"author": challenged, "start": 33, "length": 4},
            ],
        )

    async def _decline_duel(self, context: Context) -> None:
        if self._duel_state is None or self._duel_state.accepted:
            await context.reply("No pending roulette challenge to decline.")
            return

        player = str(context.message.source_uuid)
        challenger = self._duel_state.challenger
        challenged = self._duel_state.challenged

        if player not in (challenger, challenged):
            await context.reply("Only the challenger or challenged player can decline.")
            return

        self._duel_state = None

        if player == challenger:
            await context.send(
                "name cancelled the roulette challenge for name.",
                mentions=[
                    {"author": challenger, "start": 0, "length": 4},
                    {"author": challenged, "start": 41, "length": 4},
                ],
            )
            return

        await context.send(
            "name declined name's roulette challenge.",
            mentions=[
                {"author": challenged, "start": 0, "length": 4},
                {"author": challenger, "start": 14, "length": 4},
            ],
        )

    async def _spin(self, context: Context) -> None:
        player = str(context.message.source_uuid)

        if self._duel_state is None:
            await self._spin_solo(context, player)
            return

        if not self._duel_state.accepted:
            await self._accept_or_reject_pending(context, player)
            return

        if player not in (self._duel_state.challenger, self._duel_state.challenged):
            await context.reply("A roulette duel is in progress. Wait your turn.")
            return

        if player != self._duel_state.turn:
            await context.reply("It's not your turn.")
            return

        await self._fire_duel_shot(context, player)

    async def _spin_solo(self, context: Context, player: str) -> None:
        if randint(0, 5) == 0:
            self._record_death(context, player, duel=False)
            await context.send(
                "BANG. name loses.",
                mentions=[{"author": player, "start": 6, "length": 4}],
            )
            return

        self._record_survival(context, player)
        await context.send(
            "click... name survives.",
            mentions=[{"author": player, "start": 9, "length": 4}],
        )

    async def _accept_or_reject_pending(self, context: Context, player: str) -> None:
        if player == self._duel_state.challenged:
            self._duel_state.accepted = True
            await self._fire_duel_shot(context, player, accepted_now=True)
            return

        if player == self._duel_state.challenger:
            await context.reply("Waiting for them to accept with /roulette.")
            return

        await context.reply("A roulette challenge is pending. Wait for it to finish.")

    async def _fire_duel_shot(
        self, context: Context, player: str, *, accepted_now: bool = False
    ) -> None:
        duel = self._duel_state

        if duel is None:
            return

        if duel.chamber_index == duel.bullet_index:
            winner = duel.challenger if player == duel.challenged else duel.challenged
            self._record_death(context, player, duel=True)
            self._record_duel_win(context, winner)
            self._duel_state = None

            await context.send(
                "BANG. name loses. name wins the duel.",
                mentions=[
                    {"author": player, "start": 6, "length": 4},
                    {"author": winner, "start": 19, "length": 4},
                ],
            )
            return

        duel.chamber_index += 1
        duel.turn = duel.challenger if player == duel.challenged else duel.challenged

        if accepted_now:
            await context.send(
                "click... name accepts and survives. name's turn.",
                mentions=[
                    {"author": player, "start": 9, "length": 4},
                    {"author": duel.turn, "start": 35, "length": 4},
                ],
            )
            return

        await context.send(
            "click... name survives. name's turn.",
            mentions=[
                {"author": player, "start": 9, "length": 4},
                {"author": duel.turn, "start": 24, "length": 4},
            ],
        )

    async def _handle_stats(self, context: Context) -> None:
        db = context.bot.storage._sqlite  # type: ignore
        rows = db.execute(
            """
            SELECT player_uuid, solo_survives, solo_deaths, duel_wins, duel_losses, best_streak
            FROM roulette_stats
            ORDER BY duel_wins DESC, solo_survives DESC, best_streak DESC, player_uuid ASC
            LIMIT 10
            """
        ).fetchall()

        if not rows:
            await context.reply("No roulette stats yet.")
            return

        lines = ["🎲 *Roulette leaderboard*", ""]
        mentions = []

        for idx, (player_uuid, solo_survives, solo_deaths, duel_wins, duel_losses, best_streak) in enumerate(rows, start=1):
            line = (
                f"{idx}. name - solo {solo_survives}/{solo_deaths}, "
                f"duels {duel_wins}/{duel_losses}, best streak {best_streak}"
            )
            start = len("\n".join(lines)) + 1 + len(f"{idx}. ")
            lines.append(line)
            mentions.append({"author": player_uuid, "start": start, "length": 4})

        await context.send("\n".join(lines), text_mode="styled", mentions=mentions)

    def _record_survival(self, context: Context, player: str) -> None:
        db = context.bot.storage._sqlite  # type: ignore
        db.execute(
            """
            INSERT INTO roulette_stats (
                player_uuid, solo_survives, solo_deaths, duel_wins, duel_losses, current_streak, best_streak
            )
            VALUES (?, 1, 0, 0, 0, 1, 1)
            ON CONFLICT(player_uuid)
            DO UPDATE SET
                solo_survives = solo_survives + 1,
                current_streak = current_streak + 1,
                best_streak = MAX(best_streak, current_streak + 1)
            """,
            (player,),
        )
        db.commit()

    def _record_death(self, context: Context, player: str, *, duel: bool) -> None:
        db = context.bot.storage._sqlite  # type: ignore
        death_column = "duel_losses" if duel else "solo_deaths"
        db.execute(
            f"""
            INSERT INTO roulette_stats (
                player_uuid, solo_survives, solo_deaths, duel_wins, duel_losses, current_streak, best_streak
            )
            VALUES (?, 0, ?, 0, ?, 0, 0)
            ON CONFLICT(player_uuid)
            DO UPDATE SET
                {death_column} = {death_column} + 1,
                current_streak = 0
            """,
            (player, 0 if duel else 1, 1 if duel else 0),
        )
        db.commit()

    def _record_duel_win(self, context: Context, player: str) -> None:
        db = context.bot.storage._sqlite  # type: ignore
        db.execute(
            """
            INSERT INTO roulette_stats (
                player_uuid, solo_survives, solo_deaths, duel_wins, duel_losses, current_streak, best_streak
            )
            VALUES (?, 0, 0, 1, 0, 1, 1)
            ON CONFLICT(player_uuid)
            DO UPDATE SET
                duel_wins = duel_wins + 1,
                current_streak = current_streak + 1,
                best_streak = MAX(best_streak, current_streak + 1)
            """,
            (player,),
        )
        db.commit()
