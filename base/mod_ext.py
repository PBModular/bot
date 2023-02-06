import logging
import inspect

from aiogram.filters import Command

from base.module import BaseModule, Handler
from base import command_registry

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

        # Save base ref
        self.__base_mod = base_mod

        # Register methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if hasattr(func, "bot_cmds"):
                for cmd in func.bot_cmds:
                    base_mod.router.message.register(func, Command(cmd))
                    command_registry.register_command(base_mod.module_info.name, cmd)

        for handler in self.message_handlers:
            if isinstance(handler.filter, Command):
                for cmd in handler.filter.commands:
                    if command_registry.check_command(cmd):
                        logger.warning(
                            f"Command conflict! "
                            f"Module {base_mod.module_info.name} tried to register command {cmd}, "
                            f"which is already used! Skipping this command")
                    else:
                        base_mod.router.message.register(handler.func, handler.filter)
                        command_registry.register_command(base_mod.module_info.name, cmd)
            else:
                base_mod.router.message.register(handler.func, handler.filter)

        for handler in self.callback_handlers:
            base_mod.router.callback_query.register(handler.func, handler.filter)

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
