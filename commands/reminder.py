import dateparser
from datetime import datetime, timezone

from signalbot import Context, regex_triggered
from signalbot.bot import SignalBot
from commands.help import CommandWithHelpMessage
from utils import logger


class ReminderCommand(CommandWithHelpMessage):
    def help_message(self) -> str:
        return "remind: ⏰ /remind <time>|<message> (e.g. 'in 10 min|drink water')"

    @regex_triggered(r"^/remind\s+.+")
    async def handle(self, context: Context) -> None:
        text = context.message.text[len("/remind ") :].strip()

        if "|" not in text:
            await context.reply(
                "Usage examples:\n"
                "/remind in 10|minutes drink water\n"
                "/remind tomorrow 9am|meeting\n"
                "/remind 2026-01-30 14:00|call mom"
            )
            return

        run_at, message = self._parse_datetime_and_message(text)

        if not run_at or not message:
            await context.reply(
                "Usage examples:\n"
                "/remind in 10|minutes drink water\n"
                "/remind tomorrow 9am|meeting\n"
                "/remind 2026-01-30 14:00|call mom"
            )
            return

        receiver = context.message.recipient()
        member = context.message.source_uuid

        db = context.bot.storage._sqlite  # type: ignore
        db.execute(
            "INSERT INTO reminders (receiver, member, message, run_at) VALUES (?, ?, ?, ?)",
            (receiver, member, message, run_at.isoformat()),
        )
        db.commit()

        context.bot.scheduler.add_job(
            self._send_reminder,
            "date",
            run_date=run_at,
            args=[context.bot, member, receiver, message],
        )
        log = logger.get_logger()
        log.info(
            "ADD_REMINDER",
            run_date=run_at,
            receiver=receiver,
            member=member,
            message=message,
        )

        await context.react("⏰")

    def _parse_datetime_and_message(self, text: str):
        parts = text.split("|")

        time_part = parts[0]
        message_part = parts[1]

        dt = dateparser.parse(
            time_part,
            settings={
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": "UTC",
            },
        )

        if dt:
            if dt < datetime.now(timezone.utc):
                return None, None
            return dt, message_part

    async def _send_reminder(
        self, bot: SignalBot, member: str, receiver: str, message: str
    ):
        await bot.send(
            receiver,
            f"⏰ Reminder:\n{message}",
            mentions=[{"author": member, "start": 0, "length": 1}],
        )
