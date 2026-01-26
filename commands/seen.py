from datetime import datetime, timezone
from signalbot import Context, Command, regex_triggered

from commands.help import CommandWithHelpMessage


class SeenCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "seen: 👀 /seen @user — shows when they were last active."

    @regex_triggered(r"^/seen\s+.+")
    async def handle(self, context: Context) -> None:
        mentions = context.message.mentions

        if not mentions:
            await context.reply("Usage: /seen @user")
            return

        target = mentions[0].get("uuid")  # type: ignore

        db = context.bot.storage._sqlite  # type: ignore

        cursor = db.execute(
            "SELECT ts, last_text FROM seen WHERE key = ?",
            (target,),
        )

        row = cursor.fetchone()

        if not row:
            await context.reply("I haven't seen them yet 🤷")
            return

        ts, last_text = row
        dt = datetime.fromisoformat(ts)
        pretty = dt.strftime("%Y-%m-%d %H:%M UTC")

        await context.reply(
            f"👀 Last seen at **{pretty}**\n💬 Last message: *{last_text}*",
            text_mode="styled",
        )


class SeenService(Command):
    @regex_triggered(r".*")
    async def handle(self, context: Context) -> None:
        user = context.message.source_uuid
        last_text = context.message.text or ""
        ts = datetime.now(timezone.utc).isoformat()

        db = context.bot.storage._sqlite  # type: ignore

        db.execute(
            """
            INSERT INTO seen (key, ts, last_text)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET ts = ?, last_text = ?
            """,
            (user, ts, last_text, ts, last_text),
        )

        db.commit()
