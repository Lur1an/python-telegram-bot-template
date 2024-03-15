from fast_depends import Depends, inject
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker
from sqlalchemy.sql.selectable import Exists
from telegram import Update
from telegram.ext import ApplicationBuilder, Application
from src.bot.common.context import ApplicationContext, context_types
from src.bot.common.wrappers import command_handler, restricted_action
from src.bot.extractors import tx
from src.db.config import create_engine
from src.db.tables import User
from src.settings import Settings
from ptb_ext.logging_ext import ErrorForwarder
import logging


log = logging.getLogger(__name__)

settings = Settings()  # type: ignore


@command_handler("admin")
async def add_admin(update: Update, context: ApplicationContext):
    pass


@command_handler("start")
@inject
async def start(
    update: Update, context: ApplicationContext, db: AsyncSession = Depends(tx)
):
    tg_user = update.effective_user
    if await db.scalar(select(User).where(User.telegram_id == tg_user.id)):
        return
    user = User(
        telegram_id=tg_user.id,
        is_bot=tg_user.is_bot,
        telegram_username=tg_user.username,
    )
    db.add(user)


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

application.add_handler(start)
