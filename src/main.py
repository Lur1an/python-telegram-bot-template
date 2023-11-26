import logging
import sys
import asyncio

from src.db.config import AsyncSessionLocal, engine
from src.db.tables import Base

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

def main(prod: bool = False):
    loop = asyncio.new_event_loop()
    if not prod:
        import dotenv

        log.info("Loading .env file")
        dotenv.load_dotenv()
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
