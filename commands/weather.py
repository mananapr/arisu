import aiohttp

from signalbot import Context, regex_triggered
from commands.help import CommandWithHelpMessage


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "weather: 🌤 /weather <city> — current weather (Open-Meteo)"

    @regex_triggered(r"^/weather\s+.+")
    async def handle(self, context: Context) -> None:
        city = context.message.text[len("/weather ") :].strip()

        try:
            lat, lon, name, country = await self._geocode(city)

            weather = await self._fetch_weather(lat, lon)

            temp = weather["temperature_2m"]
            wind = weather["wind_speed_10m"]
            code = weather["weather_code"]

            desc = self._weather_desc(code)

            msg = f"🌥️ {name}, {country}\n{desc}\n🌡 {temp}°C | 💨 {wind} km/h"

            await context.reply(msg)

        except Exception:
            await context.reply("Couldn't fetch weather 😔")

    async def _geocode(self, city: str):
        params = {"name": city, "count": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(GEOCODE_URL, params=params) as resp:
                data = await resp.json()

        if not data.get("results"):
            raise ValueError("City not found")

        res = data["results"][0]

        return (
            res["latitude"],
            res["longitude"],
            res["name"],
            res.get("country", ""),
        )

    async def _fetch_weather(self, lat: float, lon: float):
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "timezone": "UTC",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(WEATHER_URL, params=params) as resp:
                data = await resp.json()

        return data["current"]

    def _weather_desc(self, code: int) -> str:
        return {
            0: "☀️ Clear",
            1: "🌤 Mainly clear",
            2: "⛅ Partly cloudy",
            3: "☁️ Overcast",
            45: "🌫 Fog",
            48: "🌫 Rime fog",
            51: "🌦 Light drizzle",
            53: "🌦 Drizzle",
            55: "🌧 Heavy drizzle",
            61: "🌧 Rain",
            63: "🌧 Moderate rain",
            65: "🌧 Heavy rain",
            71: "🌨 Snow",
            80: "🌦 Showers",
            95: "⛈ Thunderstorm",
        }.get(code, "🌈 Weather unknown")
