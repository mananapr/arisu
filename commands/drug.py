import aiohttp
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage
from utils.logger import get_logger


PSYCHONAUT_API = "https://psychonautwiki.org/w/api.php"


class DrugCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "drug: 💊 /drug <substance> — get info from Psychonaut Wiki"

    @regex_triggered(r"^/drug\s+.+")
    async def handle(self, context: Context) -> None:
        term = context.message.text.split(maxsplit=1)[1].strip()

        await context.bot.start_typing(context.message.recipient())

        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "action": "query",
                    "list": "search",
                    "format": "json",
                    "srsearch": term,
                    "srlimit": 1,
                }
                async with session.get(PSYCHONAUT_API, params=params) as resp:
                    search_data = await resp.json()
            except Exception:
                await context.reply("⚠️ Could not reach Psychonaut Wiki API.")
                await context.bot.stop_typing(context.message.recipient())
                return

            results = search_data.get("query", {}).get("search", [])

            if not results:
                await context.reply(f"No results found for '{term}' 😔")
                await context.bot.stop_typing(context.message.recipient())
                return

            title = results[0]["title"]

            try:
                params = {
                    "action": "query",
                    "prop": "extracts",
                    "exintro": "1",
                    "explaintext": "1",
                    "format": "json",
                    "titles": title,
                }
                async with session.get(PSYCHONAUT_API, params=params) as resp:
                    page_data = await resp.json()
            except Exception:
                await context.reply("⚠️ Failed to fetch drug info.")
                await context.bot.stop_typing(context.message.recipient())
                get_logger().error("DRUG_ERR", exc_info=True)
                return

        await context.bot.stop_typing(context.message.recipient())

        pages = page_data.get("query", {}).get("pages", {})
        if not pages:
            await context.reply(f"No info available for '{term}' 😔")
            return

        first_page = next(iter(pages.values()))
        extract = first_page.get("extract", "").strip()

        if not extract:
            await context.reply(f"No description found for '{term}' 😔")
            return

        if len(extract) > 1500:
            extract = extract[:1500] + "..."

        message = f"💊 *Psychonaut Wiki — {title}*\n\n{extract}"
        await context.reply(message)
