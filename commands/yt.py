import asyncio
import base64
import aiohttp
from yt_dlp import YoutubeDL
from signalbot import Context, regex_triggered

from commands.help import CommandWithHelpMessage


YTDLP_OPTS = {
    "quiet": True,
    "skip_download": True,
    "extract_flat": False,
    "default_search": "ytsearch1",
}


class YTCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "yt: 📺 /yt <query> — get first YouTube result with thumbnail."

    @regex_triggered(r"^/yt\s+.+")
    async def handle(self, context: Context) -> None:
        query = context.message.text.split(maxsplit=1)[1]

        loop = asyncio.get_event_loop()

        try:
            info = await loop.run_in_executor(
                None,
                self._search,
                query,
            )

            if not info:
                await context.reply("❌ No results found.")
                return

            title = info.get("title", "Unknown title")
            uploader = info.get("uploader", "Unknown channel")
            duration = info.get("duration")
            url = info.get("webpage_url")
            views = info.get("view_count")
            thumb_url = info.get("thumbnail")

            dur_str = self._format_duration(duration)
            views_str = f"{views:,}" if views else "N/A"

            metadata = (
                f"📺 **{title}**\n"
                f"👤 {uploader}\n"
                f"⏱ {dur_str}\n"
                f"👁 {views_str} views\n"
                f"🔗 {url}"
            )

            thumbnail_b64 = None

            if thumb_url:
                thumbnail_b64 = await self._fetch_thumbnail(thumb_url)

            if thumbnail_b64:
                await context.reply(
                    metadata,
                    base64_attachments=[thumbnail_b64],
                )
            else:
                await context.send(metadata)

        except Exception:
            context.bot._logger.exception("YT_ERR")
            await context.reply("⚠️ Failed to fetch YouTube result.")

    def _search(self, query: str):
        with YoutubeDL(YTDLP_OPTS) as ydl:  # type: ignore
            result = ydl.extract_info(query, download=False)

        if not result or "entries" not in result:
            return None

        entries = result["entries"]
        if not entries:
            return None

        return entries[0]

    async def _fetch_thumbnail(self, url: str) -> str | None:
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

    def _format_duration(self, seconds):
        if not seconds:
            return "N/A"

        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)

        if h:
            return f"{h}:{m:02}:{s:02}"
        return f"{m}:{s:02}"
