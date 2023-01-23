from aiogram import Bot, Dispatcher
from base.loader import ModuleLoader
import config

dp = Dispatcher()


def main():
    bot = Bot(config.token, parse_mode="HTML")
    loader = ModuleLoader(dp)
    loader.load_everything()
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
