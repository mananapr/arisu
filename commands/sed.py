import re
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


SED_REGEX = r"^/sed\s+s/([^/]+)/([^/]+)$"


class SedCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "sed: ✏️ Reply + /sed s/find/replace — fix a message."

    @regex_triggered(SED_REGEX)
    async def handle(self, context: Context) -> None:
        quoted = context.message.quote

        if not quoted or not quoted.text:
            await context.reply("Reply to a message to use sed.")
            return

        original_sender = context.message.quote.author_uuid  # type: ignore
        text = quoted.text

        match = re.match(SED_REGEX, context.message.text)
        if not match:
            await context.reply("Format: /sed s/find/replace")
            return

        find, replace = match.groups()

        try:
            if find not in text:
                await context.react("❌")
                return

            updated = text.replace(find, replace, 1)

            await context.send(
                f"name says: {updated}",
                text_mode="styled",
                mentions=[{"author": original_sender, "start": 0, "length": 4}],
            )

        except Exception:
            context.bot._logger.exception("SED_ERR")  # type: ignore
            await context.reply("⚠️ sed failed.")
