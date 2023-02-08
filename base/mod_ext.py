import logging
import inspect
from base.module import BaseModule, Handler
from base import command_registry

from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters

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

        # Save base ref
        self.__base_mod = base_mod

        # Register methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if hasattr(func, "bot_cmds"):
                for cmd in func.bot_cmds:
                    if command_registry.check_command(cmd):
                        logger.warning(
                            f"Command conflict! "
                            f"Module {base_mod.module_info.name} tried to register command {cmd}, which is already used! "
                            f"Skipping this command")
                    else:
                        command_registry.register_command(base_mod.module_info.name, cmd)
                        self.bot.add_handler(MessageHandler(func, filters.command(cmd)))

        for handler in self.message_handlers:
            # TODO: implement command registry check
            self.bot.add_handler(MessageHandler(handler.func, handler.filter))

        for handler in self.callback_handlers:
            self.bot.add_handler(CallbackQueryHandler(handler.func, handler.filter))

    @property
    def db(self):
        return self.__base_mod.db

    @property
    def message_handlers(self) -> list[Handler]:
        """
        Custom handlers for something that exceeds function name autogeneration (extended input validation, aliases, etc.)
        Override if necessary
        """
        return []

    @property
    def callback_handlers(self) -> list[Handler]:
        """
        Handlers for button callbacks
        Override if necessary
        """
        return []
