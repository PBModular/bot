from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import config
import logging
import traceback

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, modname: str):
        try:
            self.engine = create_async_engine(self.decide_url(modname))
            self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        except:
            logger.error("Failed to initialize database! Disabling for runtime!")
            traceback.print_exc()

    @staticmethod
    def decide_url(modname: str) -> str:
        if 'sqlite' in config.db_url:
            return config.db_url + f"/modules/{modname}/{config.db_file_name}"
        else:
            return config.db_url + f"/{modname}"
