import logging
import sys
import os
from base.module import BaseModule, Handler
from typing import Union, Tuple

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
        self.state_machine = base_mod.state_machine
        self.get_sm = base_mod.get_sm
        self.module_path = base_mod.module_path

        # Save base ref
        self.__base_mod = base_mod

        # Set the extension's path to the directory of its code file
        self.extension_path = os.path.dirname(sys.modules[self.__class__.__module__].__file__)

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
    def custom_handlers(self) -> list[Union[Handler, Tuple[Handler, int]]]:
        """
        Custom handlers for specialized use cases (e.g., raw updates, specific message types).
        Override if necessary.

        Each item in the list should be either:
        1. A Pyrogram Handler instance (e.g., MessageHandler, CallbackQueryHandler, RawUpdateHandler).
           These handlers will be added to the default group (0).
        2. A tuple containing (Handler, int), where the integer specifies the Pyrogram handler group.

        Handlers are processed by group number, lowest first. Within a group, order is determined by PyroTGFork.
        See: https://telegramplayground.github.io/pyrogram/topics/more-on-updates.html#handler-groups
        """
        return []
