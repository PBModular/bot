from aiogram import Bot, Dispatcher
from aiogram.utils.token import TokenValidationError
import logging
from base.loader import ModuleLoader
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

dp = Dispatcher()

# Logger .-.
FORMAT = '%(asctime)s %(name)s %(levelname)s %(message)s'
logging.basicConfig(format=FORMAT, level="INFO")
logger = logging.getLogger(__name__)


def main():
    if config["Bot"]["token"]:
        # Try to run bot
        try:
            bot = Bot(config["Bot"]["token"], parse_mode="HTML")

        # Reset token and again run main
        except TokenValidationError:
            config.set("Bot", "token", "")
            main()

        # All ok, write config
        with open("config.ini", 'w') as configfile:
            config.write(configfile)

        logger.info("Bot starting")

        loader = ModuleLoader(dp)
        loader.load_everything()
        dp.run_polling(bot)
    else:
        config.set("Bot", "token", input("Input token: "))
        main()


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
    main()

