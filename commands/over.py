import random

from signalbot import Context, regex_triggered
from commands.help import CommandWithHelpMessage


RESPONSES = [
    "truly over",
    "over",
    "never even began",
]


class OverCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "over: 💀 /over @user — owarida"

    @regex_triggered(r"^/over(?:\s+.+)?$")
    async def handle(self, context: Context) -> None:
        mentions = context.message.mentions

        if mentions:
            target = mentions[0].get("uuid")  # type: ignore
        else:
            target = context.message.source_uuid

        phrase = random.choice(RESPONSES)

        await context.send(
            f"name {phrase} for you",
            mentions=[{"author": target, "start": 0, "length": 4}],
        )
