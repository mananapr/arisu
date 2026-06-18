import os
from signalbot import SignalBot
from dotenv import load_dotenv

from utils.db import init_db
from utils.logger import configure_logging, get_logger
from commands import (
    HelpCommand,
    TossCommand,
    QuoteCommand,
    TellCommand,
    TellService,
    GondolaCommand,
    SeenService,
    SeenCommand,
    ReminderCommand,
    UrbanDictionaryCommand,
    DictionaryCommand,
    WeatherCommand,
    ChatGPTCommand,
    DuckHuntCommand,
    RouletteCommand,
    DrugCommand,
    YTCommand,
    SedCommand,
    OverCommand,
)

load_dotenv()

GROUPS = [os.environ["GROUP_NAME"]]

COMMANDS = [
    HelpCommand,
    TossCommand,
    QuoteCommand,
    TellCommand,
    TellService,
    GondolaCommand,
    SeenCommand,
    SeenService,
    ReminderCommand,
    UrbanDictionaryCommand,
    DictionaryCommand,
    WeatherCommand,
    ChatGPTCommand,
    DuckHuntCommand,
    RouletteCommand,
    DrugCommand,
    YTCommand,
    SedCommand,
    OverCommand,
]


def main() -> None:
    bot = SignalBot(
        config={
            "signal_service": os.environ["SIGNAL_SERVICE"],
            "phone_number": os.environ["PHONE_NUMBER"],
            "download_attachments": False,
            "storage": {
                "type": "sqlite",
                "sqlite_db": "arisu.db",
                "check_same_thread": False,
            },
        }
    )

    configure_logging(debug=False)
    log = get_logger()

    init_db(bot)
    log.info("DB_INIT_OK")

    for CommandCls in COMMANDS:
        bot.register(
            CommandCls(),
            contacts=False,
            groups=GROUPS,
        )

    DuckHuntCommand.schedule_spawns(bot, GROUPS)
    log.info("CMD_INIT_OK")

    bot.register
    bot.start()

    log.info("BOT_INIT_OK")


if __name__ == "__main__":
    main()
