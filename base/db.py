from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import config
import logging
import traceback

logger = logging.getLogger(__name__)

engine = None
session = None
try:
    engine = create_engine(config.db_url)
    session = Session(engine)
except:
    logger.error("Failed to initialize database! Disabling for runtime!")
    traceback.print_exc()
