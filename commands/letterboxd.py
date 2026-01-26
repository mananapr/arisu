import base64
import aiohttp
from bs4 import BeautifulSoup
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


SEARCH_URL = "https://letterboxd.com/search/{}"
BASE_URL = "https://letterboxd.com"


class LetterboxdCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "lb: 🎬 /lb <movie> — search Letterboxd with poster."

    @regex_triggered(r"^/lb\s+.+")
    async def handle(self, context: Context) -> None:
        query = context.message.text.split(maxsplit=1)[1]
        search_url = SEARCH_URL.format(query.replace(" ", "%20"))

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
                        ),
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Connection": "keep-alive",
                    },
                ) as resp:
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")

            film = soup.select_one("li.film-detail")

            if not film:
                await context.reply("❌ No movie found.")
                return

            link_tag = film.find("a", class_="frame")  # type: ignore
            slug = link_tag["href"]  # type: ignore
            movie_url = BASE_URL + slug  # type: ignore

            title = film.find("span", class_="film-title").text.strip()  # type: ignore
            year = film.find("small").text.strip() if film.find("small") else "?"  # type: ignore

            rating_tag = film.select_one(".rating")
            rating = rating_tag.text.strip() if rating_tag else "N/A"

            poster_url = link_tag.find("img")["src"]  # type: ignore

            poster_b64 = await self._fetch_image(poster_url)  # type: ignore

            message = f"🎬 *{title}* ({year})\n⭐ {rating}/5\n\n🔗 {movie_url}"

            if poster_b64:
                await context.send(
                    message,
                    base64_attachments=[poster_b64],
                )
            else:
                await context.send(message)

        except Exception:
            context.bot._logger.exception("LB_ERR")  # type: ignore
            await context.reply("⚠️ Failed to fetch movie info.")

    async def _fetch_image(self, url: str) -> str | None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                ) as resp:
                    if resp.status != 200:
                        return None

                    data = await resp.read()
                    return base64.b64encode(data).decode()

        except Exception:
            return None
