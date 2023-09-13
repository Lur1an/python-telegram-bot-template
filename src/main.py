from src.bot.application import application

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
log = logging.getLogger(__name__)

def main():
    application.run_polling()


if __name__ == "__main__":
    main()
