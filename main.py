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

init(autoreset=True)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class ColorFormatter(logging.Formatter):
    status_colors = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.WHITE,
        logging.WARN: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.DIM,
    }
    name_color = Fore.CYAN + Style.BRIGHT
    reset = Style.RESET_ALL
    time_color = Fore.LIGHTBLACK_EX
    separator_color = Fore.LIGHTBLACK_EX

    def format(self, record: logging.LogRecord) -> str:
        log_level = record.levelno
        level_color = self.status_colors.get(log_level, Fore.WHITE)

        f = (
            f"{self.time_color}%(asctime)s{self.reset}"
            f"{self.separator_color} | {self.reset}"
            f"{level_color}%(levelname)-8s{self.reset}"
            f"{self.separator_color} | {self.reset}"
            f"{self.name_color}%(name)s{self.reset}"
            f"{self.separator_color} » {self.reset}"
            f"{level_color}%(message)s{self.reset}"
        )

        formatter = logging.Formatter(f, datefmt=DATE_FORMAT)
        return formatter.format(record)

# File/Console Logger
file_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s:%(module)s:%(funcName)s:%(lineno)d | %(message)s",
    datefmt=DATE_FORMAT
)
file_handler = RotatingFileHandler(
    filename="bot.log", maxBytes=128 * 1024, encoding='utf-8'
)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.INFO) # Change to DEBUG if you need

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(ColorFormatter())

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stdout_handler)

logger = logging.getLogger(__name__)

# Root path
ROOT_DIR = os.getcwd()


def get_last_commit_info():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).strip().decode("utf-8")
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cd", "--date=short"], stderr=subprocess.DEVNULL
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
            try:
                # Use the URL from config if DB is enabled
                db_uri = config.db_url if config.enable_db else f"sqlite+aiosqlite:///{config.db_file_name}"
                if config.enable_db:
                    logger.info(f"Database enabled. Connecting to: {db_uri.split('@')[-1]}")
                else:
                    logger.info(f"Database disabled. Using file: {config.db_file_name}")

                engine = create_async_engine(db_uri)
                session_maker = async_sessionmaker(engine, expire_on_commit=False)

                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("Database initialized and tables created/checked.")
            except Exception as e:
                logger.critical(f"Database initialization failed: {e}")
                session_maker = None
                engine = None
                return

            # Load modules
            logger.info("Initializing Module Loader...")
            loader = ModuleLoader(
                bot,
                root_dir=ROOT_DIR,
                bot_db_session=session_maker,
                bot_db_engine=engine,
            )
            loader.load_everything()
            logger.info("Module loading complete.")

            # Launch bot
            try:
                await bot.start()
                user = await bot.get_me()
                logger.info(f"Bot started as @{user.username} (ID: {user.id})")
                await idle()
            except Exception as e:
                logger.exception("An error occurred during bot runtime.")
            finally:
                logger.warning("Stopping bot...")
                await bot.stop()
                if engine:
                    await engine.dispose()
                logger.info("Bot stopped.")


        # Run the async start function
        try:
            bot.run(start())
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user (KeyboardInterrupt).")
        except Exception as e:
            logger.exception("Critical error in main loop.")

    else:
        logger.warning("Credentials not found in config. Requesting input.")
        try:
            token_in = input(f"{Fore.YELLOW}Input Bot Token: {Style.RESET_ALL}")
            api_id_in = input(f"{Fore.YELLOW}Input API ID: {Style.RESET_ALL}")
            api_hash_in = input(f"{Fore.YELLOW}Input API Hash: {Style.RESET_ALL}")

            # Basic validation
            if not token_in or not api_id_in.isdigit() or not api_hash_in:
                logger.error("Invalid input. Token and API Hash cannot be empty, API ID must be a number.")
                return

            config.token = token_in
            config.api_id = int(api_id_in)
            config.api_hash = api_hash_in
            main(update_conf=True)
        except EOFError:
            logger.critical("Input stream closed unexpectedly. Exiting.")
        except ValueError:
            logger.error("Invalid API ID provided. It must be an integer.")
        except Exception as e:
            logger.exception(f"An error occurred during credential input: {e}")


if __name__ == "__main__":
    sha, date = get_last_commit_info()
    print(
        f"""
        {Fore.CYAN}
██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ 
██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██╔══██╗██╔══██╗
██████╔╝██████╔╝██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ███████║██████╔╝
██╔═══╝ ██╔══██╗██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██╔══██║██╔══██╗
██║     ██████╔╝██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║
╚═╝     ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
    {Style.RESET_ALL}
        {Fore.LIGHTBLACK_EX}------------------------------------------------------------{Style.RESET_ALL}
         {Fore.CYAN}Commit:{Style.RESET_ALL} {Fore.YELLOW}{sha[:7]}{Style.RESET_ALL}
         {Fore.CYAN}Date:{Style.RESET_ALL}   {date}
        {Fore.LIGHTBLACK_EX}------------------------------------------------------------{Style.RESET_ALL}
    """
    )
    try:
        main(update_conf=False)
    except Exception as e:
        logging.getLogger(__name__).exception("An uncaught exception occurred at the top level.")
    finally:
        print(f"{Fore.LIGHTBLACK_EX}Execution finished.{Style.RESET_ALL}")
