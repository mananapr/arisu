import aiohttp
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


class DictionaryCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "dict: 📚 /dict <word> — dictionary definition"

    @regex_triggered(r"^/dict\s+.+")
    async def handle(self, context: Context) -> None:
        word = context.message.text[len("/dict ") :].strip()

        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            meanings = data[0]["meanings"]

            defs = []
            for meaning in meanings:
                for d in meaning["definitions"]:
                    defs.append(f"- {d['definition']}")
                    if len(defs) >= 3:
                        break

            msg = f"📚 **{word}**\n" + "\n".join(defs)

            await context.reply(msg, text_mode="styled")

        except Exception:
            await context.reply("No definition found 😔")
