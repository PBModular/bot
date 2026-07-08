from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

from config import config
import logging
import traceback

logger = logging.getLogger(__name__)


def is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def sqlite_connect_args(url: str) -> dict:
    """Busy-timeout passed straight to sqlite3.connect(); no-op for other DBs."""
    return {"timeout": 15} if is_sqlite_url(url) else {}


def apply_sqlite_pragmas(engine: AsyncEngine, url: str) -> None:
    """
    Enable WAL journal mode + a real busy_timeout for sqlite engines.
    """
    if not is_sqlite_url(url):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


class Database:
    def __init__(self, modname: str):
        try:
            url = self.decide_url(modname)

            self.engine = create_async_engine(url, connect_args=sqlite_connect_args(url))
            apply_sqlite_pragmas(self.engine, url)

            self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        except Exception as e:
            logger.error("Failed to initialize database! Disabling for runtime! Error: %s", e)
            traceback.print_exc()
            self.engine = None
            self.session_maker = None

    @staticmethod
    def decide_url(modname: str) -> str:
        if "sqlite" in config.db_url:
            return config.db_url + f"/modules/{modname}/{config.db_file_name}"
        return config.db_url + f"/{modname}"
