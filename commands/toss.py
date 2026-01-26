from commands.help import CommandWithHelpMessage
from random import randint
from signalbot import Context, triggered


class TossCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "toss: 🪙 Flip a virtual coin."

    @triggered("/toss")
    async def handle(self, context: Context) -> None:
        await context.react("👍🏽" if randint(0, 1) else "👎🏽")
