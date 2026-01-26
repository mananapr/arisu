from abc import abstractmethod
from signalbot import Command, Context, triggered


class CommandWithHelpMessage(Command):
    @abstractmethod
    def help_message(self) -> str:
        pass


class HelpCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "help: 🆘 Show this help message."

    @triggered("/help")
    async def handle(self, context: Context) -> None:
        lines = ["📖 *Available commands:*", ""]

        commands: list[CommandWithHelpMessage] = [
            cmd
            for cmd, _, _, _ in self.bot.commands  # type: ignore
            if "Command" in cmd.__class__.__name__
        ]

        commands.sort(key=lambda c: c.help_message())

        for command in commands:
            lines.append(f"• {command.help_message()}")

        message = "\n".join(lines)

        await context.send(message, text_mode="styled")
