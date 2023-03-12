import logging

from src.bot.application import application

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

log = logging.getLogger(__name__)

if __name__ == "__main__":
    application.run_polling()
