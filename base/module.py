import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union, Callable, Type
import inspect
import os

from aiogram import Bot
from aiogram.dispatcher.router import Router
from aiogram.filters import Command, Filter

from base.db import Database
from sqlalchemy import MetaData

import yaml
from config import config
from base import command_registry


@dataclass
class ModuleInfo:
    name: str
    author: str
    version: str
    src_url: Optional[str] = None


@dataclass
class Handler:
    filter: Filter
    func: Callable


class Permissions(str, Enum):
    use_db = 'use_db'
    require_db = 'require_db'
    use_loader = 'use_loader'


class BaseModule(ABC):
    """
    Bot module superclass
    """
    def __init__(self, bot: Bot, loaded_info_func: Callable):
        self.logger = logging.getLogger(__name__)
        self.router = Router()

        self.bot = bot
        self.__loaded_info = loaded_info_func

        # Load translations if available
        self.cur_lang = config.language
        try:
            files = os.listdir("./strings/")
            self.rawS = {}
            for file in files:
                self.rawS[file.removesuffix('.yaml')] = yaml.safe_load(open(f"./strings/{file}", encoding="utf-8"))

            self.logger.info(f"Available translations: {list(self.rawS.keys())}")
            if config.language in self.rawS.keys():
                self.S = self.rawS[config.language]
            elif config.fallback_language in self.rawS.keys():
                self.logger.warning(
                    f"Language {config.language} not found! Falling back to {config.fallback_language}"
                )
                self.cur_lang = config.fallback_language
                self.S = self.rawS[config.fallback_language]
            else:
                self.logger.warning(
                    f"Can't select language... Using first in list, you've been warned!"
                )
                self.S = list(self.rawS.values())[0]
        except FileNotFoundError:
            pass

        # Place for database session. Will be set by loader if necessary
        self.__db: Optional[Database] = None

        # Place for loader
        self.loader = None

        # Load extensions
        self.__extensions = []
        for ext in self.module_extensions:
            self.__extensions.append(ext(self))

    def register_all(self):
        """
        Method that initiates method registering. Must be called only from loader!
        """
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if hasattr(func, "bot_cmds"):
                for cmd in func.bot_cmds:
                    self.router.message.register(func, Command(cmd))
                    command_registry.register_command(self.module_info.name, cmd)

        for handler in self.message_handlers:
            if isinstance(handler.filter, Command):
                for cmd in handler.filter.commands:
                    if command_registry.check_command(cmd):
                        self.logger.warning(
                            f"Command conflict! "
                            f"Module {self.module_info.name} tried to register command {cmd}, which is already used! "
                            f"Skipping this command")
                    else:
                        self.router.message.register(handler.func, handler.filter)
                        command_registry.register_command(self.module_info.name, cmd)
            else:
                self.router.message.register(handler.func, handler.filter)

        for handler in self.callback_handlers:
            self.router.callback_query.register(handler.func, handler.filter)

    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """Module info. Must be set"""
        pass

    @property
    def module_permissions(self) -> list[Permissions]:
        """
        Permissions requested by the module. WIP
        """
        return []

    @property
    def module_extensions(self) -> list[Type]:
        """
        List of module extension classes. Override if necessary.
        """
        return []

    @property
    def db(self):
        return self.__db

    @db.setter
    def db(self, value):
        """
        Setter for DB object. Creates tables from db_meta if available
        """
        self.__db = value
        if self.db_meta:
            self.db_meta.create_all(self.__db.engine)

    @property
    def db_meta(self):
        """
        SQLAlchemy MetaData object. Must be set if using database
        :rtype: MetaData
        """
        return None

    @property
    def help_page(self) -> Optional[str]:
        """
        Help string to be displayed in Core module help command. Highly recommended to set this!
        """
        return None

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

    def on_init(self):
        """Called when module should initialize itself. Optional"""
        pass

    @property
    def loaded_modules(self) -> dict[str, ModuleInfo]:
        """
        Method for querying loaded modules from child instance
        :return: List of loaded modules info
        """
        return self.__loaded_info()


def command(cmds: Union[list[str], str]):
    """
    Decorator for registering module command
    Note: if you need more complex validation, use message_handlers property
    """
    def wrapper(func: Callable):
        func.bot_cmds = cmds if type(cmds) == list else [cmds]
        return func

    return wrapper
