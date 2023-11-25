import logging
import sys

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)


def main(prod: bool = False):
    if not prod:
        import dotenv

        log.info("Loading .env file")
        dotenv.load_dotenv()

    from src.bot.application import application
    application.run_polling()


if __name__ == "__main__":
    prod = True
    for arg in sys.argv:
        if arg == "--dev":
            log.info("Running in development mode")
            prod = False

    main(prod=prod)
