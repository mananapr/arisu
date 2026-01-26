import random
from typing import Optional
from datetime import datetime, timezone
from signalbot import Context, regex_triggered
from signalbot.storage import SQLiteStorage
from commands.help import CommandWithHelpMessage


class QuoteCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "quote: 📌 Reply to save | /quote @user to fetch."

    @regex_triggered(r"^/quote(?:\s+.{1,2})?$")
    async def handle(self, context: Context) -> None:
        store: SQLiteStorage = self.bot.storage  # type: ignore

        quote = context.message.quote
        mentions = context.message.mentions
        mention: Optional[dict] = mentions[0] if mentions else None  # type: ignore

        cursor = store._sqlite.cursor()

        if not quote and not mention:
            await context.reply("Nothing to save 🤷")
            return

        elif not quote:
            cursor.execute(
                """
                SELECT text FROM quotes
                WHERE sender = ?
                """,
                (mention["uuid"],),  # type: ignore
            )

            rows = cursor.fetchall()

            if not rows:
                await context.react("❌")
                return

            text = random.choice(rows)[0]

            await context.reply(f"💬 *{text}*", text_mode="styled")
            return

        elif not mention:
            cursor.execute(
                """
                INSERT INTO quotes (sender, text, ts)
                VALUES (?, ?, ?)
                """,
                (
                    quote.author_uuid,
                    quote.text,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            store._sqlite.commit()

            await context.react("📌")
            return
