from aiogram import Bot, Dispatcher
from aiogram.utils.token import TokenValidationError
import logging
from base.loader import ModuleLoader
from config import config, CONF_FILE
import os

dp = Dispatcher()

# Logger .-.
FORMAT = '%(asctime)s | %(levelname)s | %(name)s %(message)s'
logging.basicConfig(format=FORMAT, level="INFO")
logger = logging.getLogger(__name__)

# Root path
ROOT_DIR = os.getcwd()


def main(update_conf: bool = False):
    if config.token:
        # Try to run bot
        try:
            bot = Bot(config.token, parse_mode="HTML")

        # Reset token and again run main
        except TokenValidationError:
            config.token = None
            main(update_conf=True)

        # All ok, write token to config
        if update_conf:
            config.to_yaml_file(CONF_FILE)

        logger.info("Bot starting...")

        if config.enable_db:
            logger.info("Initializing database...")
            import base.db as db
            loader = ModuleLoader(dp, root_dir=ROOT_DIR, db_base=db.session, db_engine=db.engine)
        else:
            loader = ModuleLoader(dp, root_dir=ROOT_DIR)

        # Load modules
        loader.load_everything()
        dp.run_polling(bot)
    else:
        config.token = input("Input token: ")
        main(update_conf=True)


if __name__ == "__main__":
    logger.info("Bot starting")
    print(
        """


        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            



    """
    )
    main(update_conf=False)

