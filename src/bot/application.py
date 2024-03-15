from fast_depends import Depends, inject
from pydantic_core.core_schema import arguments_schema
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker
from sqlalchemy.sql.selectable import Exists
from telegram import Update
from telegram.ext import ApplicationBuilder, Application
from src.bot.common.context import ApplicationContext, context_types
from src.bot.common.wrappers import command_handler, restricted_action
from src.bot.extractors import tx, user
from src.db.config import create_engine
from src.db.tables import User, UserRole
from src.settings import Settings
from ptb_ext.logging_ext import ErrorForwarder
import logging


log = logging.getLogger(__name__)

settings = Settings()  # type: ignore


@command_handler("role")
@inject
async def set_role(
    update: Update,
    context: ApplicationContext,
    session: AsyncSession = Depends(tx),
    user: User = Depends(user),
):
    if not user.role == UserRole.ADMIN:
        await update.effective_message.reply_text("Unauthorized")
        return
    if context.args is None or len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /admin <user_id> <role>")
        return
    user_id, role = context.args
    user_id = int(user_id)
    role = UserRole(role.lower())
    if target_user := await session.scalar(select(User).where(User.telegram_id == user_id)):
        target_user.role = role
    else:
        await update.effective_message.reply_text("User not found")
        return


@command_handler("start")
@inject
async def start(
    update: Update, context: ApplicationContext, session: AsyncSession = Depends(tx)
):
    tg_user = update.effective_user
    if await session.scalar(select(User).where(User.telegram_id == tg_user.id)):
        return
    user = User(
        telegram_id=tg_user.id,
        is_bot=tg_user.is_bot,
        telegram_username=tg_user.username,
    )
    if tg_user.id == context.settings.FIRST_ADMIN:
        user.role = UserRole.ADMIN
    session.add(user)


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
