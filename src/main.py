import asyncio
import logging
import sys

from src.settings import DBSettings

log = logging.getLogger(__name__)


async def create_db():
    from src.db.config import create_engine

    engine = create_engine(DBSettings().DB_PATH)
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
    prod = True
    for arg in sys.argv:
        if arg == "--dev":
            log.info("Running in development mode")
            prod = False

    main(prod=prod)
