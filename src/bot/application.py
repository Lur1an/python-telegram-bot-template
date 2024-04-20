from fast_depends import Depends, inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession, async_sessionmaker
from telegram import Update
from telegram.ext import ApplicationBuilder, Application
from src.bot.common.context import ApplicationContext, context_types
from src.bot.common.wrappers import command_handler
from src.bot.errors import handle_error
from src.bot.extractors import tx, load_user
from src.db.config import create_engine
from src.db.tables import User, UserRole
from src.settings import Settings
from ptb_ext.logging_ext import ErrorForwarder

import logging
import structlog


log = structlog.get_logger()

settings = Settings()  # type: ignore

@command_handler("role")
@inject
async def set_role(
    update: Update,
    context: ApplicationContext,
    session: AsyncSession = Depends(tx),
    user: User = Depends(load_user),
):
    if not user.role == UserRole.ADMIN:
        log.warn("Unauthorized user tried admin command", user=user, command="set_role")
        await update.effective_message.reply_text("Unauthorized")
        return

    if context.args is None or len(context.args) != 2:
        await update.effective_message.reply_text("Usage: /role <user_id> <role>")
        return

    target_user_id, role = context.args
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        await update.effective_message.reply_text("User id must be an integer")
        return

    if target_user_id == user.telegram_id:
        await update.effective_message.reply_text("You can't change your own role")
        return

    try:
        role = UserRole(role.lower())
    except ValueError:
        await update.effective_message.reply_text("Invalid role")
        return

    log.info("Promoting user", target_user_id=target_user_id, role=role)
    if target_user := await session.scalar(
        select(User).where(User.telegram_id == target_user_id)
    ):
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
        full_name=tg_user.full_name,
    )
    if tg_user.id == context.settings.FIRST_ADMIN:
        log.warn("First admin detected", user=update.effective_user)
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

    # Setup log forwarder to telegram
    # When sending to telegram just send the raw json logs in pretty format
    telegram_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
        ],
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(indent=2),
        ],
    )
    telegram_logs = []
    if settings.LOGGING_CHANNEL:
        telegram_logs.append(settings.LOGGING_CHANNEL)
        await app.bot.send_message(
            chat_id=settings.LOGGING_CHANNEL,
            text="Bot started",
        )
    error_forwarder = ErrorForwarder(
        app.bot, telegram_logs, log_levels=["ERROR", "WARNING"]
    )
    error_forwarder.setFormatter(telegram_formatter)
    logging.getLogger().addHandler(error_forwarder)


application: Application = (
    ApplicationBuilder()
    .token(settings.BOT_TOKEN)
    .context_types(context_types)
    .arbitrary_callback_data(True)
    .post_init(on_startup)
    .build()
)

application.add_error_handler(handle_error) # type: ignore
application.add_handlers([start, set_role])
