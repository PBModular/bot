from aiogram import Bot, Dispatcher
from base.loader import ModuleLoader

TOKEN = "TOKEN HERE"
dp = Dispatcher()


def main() -> None:
    bot = Bot(TOKEN, parse_mode="HTML")
    loader = ModuleLoader(dp)
    loader.load_everything()
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
