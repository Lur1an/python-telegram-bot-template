import asyncio
import logging.config
import structlog
import sys
import os
from src.db.config import create_engine
from src.settings import DBSettings

log = structlog.getLogger()


async def create_db():
    db_path = DBSettings().DB_PATH
    if os.path.exists(db_path):
        log.info("Database already exists, re-using", db_path=db_path)
        return
    log.info("Creating database from scratch", db_path=db_path)
    engine = create_engine(db_path)
    from src.db.tables import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def main(prod: bool = False):
    loop = asyncio.new_event_loop()
    if not prod:
        import dotenv

        log.info("Loading .env file")
        dotenv.load_dotenv()
        # DB creation not needed since dev db can be created with alembic
        loop.run_until_complete(create_db())

    from src.bot.application import application

    application.run_polling()


if __name__ == "__main__":
    # stdlib compatible structlog config
    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
    pre_chain = [
        # Add the log level and a timestamp to the event_dict if the log entry
        # is not from structlog.
        structlog.stdlib.add_log_level,
        # Add extra attributes of LogRecord objects to the event dictionary
        # so that values passed in the extra parameter of log methods pass
        # through to log output.
        structlog.stdlib.ExtraAdder(),
        timestamper,
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),
                    ],
                    "foreign_pre_chain": pre_chain,
                },
                "colored": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.dev.ConsoleRenderer(colors=True),
                    ],
                    "foreign_pre_chain": pre_chain,
                },
            },
            "handlers": {
                "default": {
                    "level": "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "colored",
                },
                "file": {
                    "level": "DEBUG",
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": "app.log",
                    "formatter": "plain",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default", "file"],
                    "level": "INFO",
                    "propagate": True,
                },
                "httpx": {
                    "level": "WARNING",
                    "propagate": True,
                },
                "apscheduler.scheduler": {
                    "level": "WARNING",
                    "propagate": True,
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    prod = True
    for arg in sys.argv:
        if arg == "--dev":
            log.info("Running in development mode")
            prod = False
    main(prod=prod)
