from datetime import datetime, timezone
from signalbot import Context, Command, regex_triggered

from commands.help import CommandWithHelpMessage


class TellCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "tell: 📬 /tell @user <message> — leave a message for someone."

    @regex_triggered(r"^/tell\s+.+")
    async def handle(self, context: Context) -> None:
        mentions = context.message.mentions
        text = context.message.text

        if not mentions:
            await context.reply("Usage: /tell @user <message>")
            return

        target = mentions[0]["uuid"]  # type: ignore

        parts = text.split(maxsplit=2)

        if len(parts) < 3:
            await context.reply("Please provide a message to send.")
            return

        message = parts[2]

        sender = context.message.source_uuid
        ts = datetime.now(timezone.utc).isoformat()

        store = context.bot.storage._sqlite  # type: ignore

        store.execute(
            """
            INSERT INTO tell (sender, target, message, ts)
            VALUES (?, ?, ?, ?)
            """,
            (str(sender), str(target), message, ts),
        )

        store.commit()

        await context.react("📬")


class TellService(Command):
    @regex_triggered(r".*")
    async def handle(self, context: Context) -> None:
        user = context.message.source_uuid
        store = context.bot.storage._sqlite  # type: ignore

        cursor = store.execute(
            "SELECT id, sender, message FROM tell WHERE target = ?",
            (str(user),),
        )

        rows = cursor.fetchall()

        if not rows:
            return

        for _, sender, message in rows:
            await context.send(
                f"name - 📬 Message from sender :\n*{message}*",
                text_mode="styled",
                mentions=[
                    {"author": user, "start": 0, "length": 4},
                    {"author": sender, "start": 22, "length": 6},
                ],
            )

        store.execute(
            "DELETE FROM tell WHERE target = ?",
            (str(user),),
        )
        store.commit()
