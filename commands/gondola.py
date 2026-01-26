import aiohttp
from bs4 import BeautifulSoup

from signalbot import Context, regex_triggered
from signalbot.api import base64
from utils.logger import get_logger
from commands.help import CommandWithHelpMessage


GONDOLA_PAGE = "https://gondola.nabein.me/random"
BASE_URL = "https://gondola.nabein.me"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


class GondolaCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "gondola: 🚡 Send a random gondola clip."

    @regex_triggered(r"^/gondola$")
    async def handle(self, context: Context) -> None:
        log = get_logger()
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(GONDOLA_PAGE) as resp:
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")

            source = soup.find("source")

            if not source or not source.get("src"):
                await context.reply("🚡 Gondola broke 😔")
                return

            media_url = BASE_URL + source["src"]  # type: ignore
            filename = media_url.split("/")[-1]

            await context.start_typing()
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(media_url) as resp:
                    data = str(base64.b64encode(await resp.read()), encoding="utf-8")
                    await context.send(filename, base64_attachments=[data])
            await context.stop_typing()

        except Exception as e:
            await context.reply(
                f"🚡 Gondola derailed 😵\n*{str(e)}*", text_mode="styled"
            )
            log.error("GONDOLA_ERR", exc_info=True)
            await context.stop_typing()
