import logging
from base.module import BaseModule, Handler

logger = logging.getLogger(__name__)


class ModuleExtension:
    """
    Module extension for BaseModule. Allows to split code in several files
    """
    def __init__(self, base_mod: BaseModule):
        # Inherit some attrs from BaseModule object
        self.bot = base_mod.bot
        self.S = base_mod.S
        self.rawS = base_mod.rawS
        self.cur_lang = base_mod.cur_lang
        self.loader = base_mod.loader
        self.logger = base_mod.logger

        # Save base ref
        self.__base_mod = base_mod

        # Register methods
        base_mod.register_all(ext=self)

        # Execute custom init
        self.on_init()

    def on_init(self):
        """Custom init goes here"""
        pass

    @property
    def db(self):
        return self.__base_mod.db

    @property
    def custom_handlers(self) -> list[Handler]:
        """
        Custom handlers for something that exceeds message / callback query validation (raw messages, etc.)
        Override if necessary
        """
        return []
