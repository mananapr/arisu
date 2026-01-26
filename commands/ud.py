import aiohttp
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


class UrbanDictionaryCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "ud: 📖 /ud <word> — Urban Dictionary meaning"

    @regex_triggered(r"^/ud\s+.+")
    async def handle(self, context: Context) -> None:
        term = context.message.text[len("/ud ") :].strip()

        url = f"https://api.urbandictionary.com/v0/define?term={term}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            if not data["list"]:
                await context.reply("No results found.")
                return

            entry = data["list"][0]

            definition = entry["definition"][:700]
            example = entry.get("example", "")

            msg = f"📖 **{term}**\n\n{definition}"

            if example:
                msg += f"\n\nExample:\n*{example}*"

            await context.reply(msg, text_mode="styled")

        except Exception:
            await context.reply("Urban Dictionary failed 😔")
