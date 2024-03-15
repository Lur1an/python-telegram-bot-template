from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker
from telegram.ext import ApplicationBuilder, Application
from src.bot.common.context import context_types
from src.db.config import create_engine
from src.db.tables import User
from src.settings import Settings
from ptb_ext.logging_ext import ErrorForwarder
import logging

from telegram import Update
from src.bot.common.context import ApplicationContext
from src.bot.common.wrappers import command_handler
from fast_depends import inject, Depends

log = logging.getLogger(__name__)

settings = Settings()  # type: ignore


def ConversationState(t: type):
    def extract_state(update: Update, context: ApplicationContext):
        return context.user_data.get_conversation_state(t)
    return Depends(extract_state)

async def tx(context: ApplicationContext):
    async with context.session() as session:
        try:
            yield session
        except Exception as e:
            log.error("Unhandled exception in SQL session", e)
            await session.rollback()


@command_handler("stuff")
@inject
async def random_handler(
    update: Update, context: ApplicationContext, db: AsyncSession = Depends(tx), convo = ConversationState(User)
):
    log.info("Handling random command")


async def on_startup(app: Application):
    db_path = settings.DB_PATH
    engine = create_engine(db_path)

    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    app.bot_data._db = AsyncSessionLocal
    app.bot_data._settings = settings

    app.add_handler(random_handler)

    # Set up log forwarding
    handlers = []
    handlers.append(logging.StreamHandler(None))
    error_forwarding = []
    if settings.LOGGING_CHANNEL:
        error_forwarding.append(settings.LOGGING_CHANNEL)
    handlers.append(ErrorForwarder(app.bot, error_forwarding))

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=handlers,
    )


application: Application = (
    ApplicationBuilder()
    .token(settings.BOT_TOKEN)
    .context_types(context_types)
    .arbitrary_callback_data(True)
    .post_init(on_startup)
    .build()
)
