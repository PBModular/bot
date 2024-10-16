from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from pyrogram.errors.exceptions.bad_request_400 import BadRequest
from base.loader import ModuleLoader
from config import config, CONF_FILE
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db import Base

import os
import logging
import subprocess

init()  # initialize colorama

class ColorFormatter(logging.Formatter):
    status_colors = {
        logging.DEBUG: "",
        logging.INFO: f"{Fore.GREEN}",
        logging.WARN: f"{Fore.YELLOW}",
        logging.ERROR: f"{Fore.RED}",
        logging.CRITICAL: f"{Fore.RED}",
    }
    text_colors = {
        logging.DEBUG: "",
        logging.INFO: "",
        logging.WARN: "",
        logging.ERROR: "",
        logging.CRITICAL: "",
    }
    name_color = f"{Fore.WHITE}"
    reset = f"{Style.RESET_ALL}"
    text_spacing = "\t" * 8

    def format(self, record: logging.LogRecord) -> str:
        f = (
            f"%(asctime)s | "
            f"{self.status_colors[record.levelno]}%(levelname)s{self.reset} | "
            f"{self.name_color}%(name)s{self.reset} "
            f"\r{self.text_spacing}{self.text_colors[record.levelno]}%(message)s{self.reset}"
        )

        return logging.Formatter(f).format(record)


# File/Console Logger
file_handler = RotatingFileHandler(
    filename="bot.log", maxBytes=128 * 1024
)  # 128 MB limit

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(ColorFormatter())

handlers = [file_handler, stdout_handler]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s %(message)s",
    level="INFO",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

# Root path
ROOT_DIR = os.getcwd()


def get_last_commit_info():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode("utf-8")
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=short"]
        ).strip().decode("utf-8")
        return sha, date
    except subprocess.CalledProcessError:
        return "Unknown", "Unknown"


def main(update_conf: bool = False):
    if config.token and config.api_id and config.api_hash:
        # Try to run bot
        try:
            bot = Client(
                name="bot",
                api_id=config.api_id,
                api_hash=config.api_hash,
                bot_token=config.token,
                parse_mode=ParseMode.HTML,
            )

        # Reset token and again run main
        except BadRequest:
            config.token = None
            config.api_id = None
            config.api_hash = None
            main(update_conf=True)

        # All ok, write token to config
        if update_conf:
            config.to_yaml_file(CONF_FILE)

        logger.info("Bot starting...")

        async def start():
            # Init database
            engine = create_async_engine("sqlite+aiosqlite:///bot_db.sqlite3")
            session_maker = async_sessionmaker(engine, expire_on_commit=False)

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Load modules
            loader = ModuleLoader(
                bot,
                root_dir=ROOT_DIR,
                bot_db_session=session_maker,
                bot_db_engine=engine,
            )
            loader.load_everything()

            # Launch bot
            await bot.start()
            await idle()
            await bot.stop()

        bot.run(start())
    else:
        config.token = input("Input token: ")
        config.api_id = int(input("Input api_id: "))
        config.api_hash = input("Input api_hash: ")
        main(update_conf=True)


if __name__ == "__main__":
    sha, date = get_last_commit_info()
    print(
        f"""
        {Fore.CYAN}
        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            

    Commit: {sha[:6]}
    Date: {date}
    {Style.RESET_ALL}
    """
    )
    main(update_conf=False)
