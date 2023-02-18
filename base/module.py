import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union, Callable, Type
import inspect
import os

from pyrogram import Client
from pyrogram import filters
from pyrogram.filters import Filter
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.handlers.handler import Handler

from base.db import Database
from sqlalchemy import MetaData

import yaml
from config import config
from base import command_registry
from dataclass_wizard import YAMLWizard


@dataclass
class ModuleInfo:
    name: str
    author: str
    version: str
    description: str
    src_url: Optional[str] = None


class Permissions(str, Enum):
    use_db = 'use_db'
    require_db = 'require_db'
    use_loader = 'use_loader'


@dataclass
class InfoFile(YAMLWizard):
    info: ModuleInfo
    permissions: list[Permissions] = field(default_factory=list)


class BaseModule(ABC):
    """
    Bot module superclass
    """
    def __init__(self, bot: Client, loaded_info_func: Callable):
        self.bot = bot
        self.__loaded_info = loaded_info_func

        # Parse info and extensions
        info_file = InfoFile.from_yaml_file("./info.yaml")
        self.module_info = info_file.info
        self.module_permissions = info_file.permissions

        self.logger = logging.getLogger(self.module_info.name)

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

        # Place for message handlers and extensions
        self.__extensions = []
        self.__handlers = []

        # Auto-generated help
        self.__auto_help = None

    def stage2(self):
        self.register_all()
        # Load extensions
        for ext in self.module_extensions:
            self.__extensions.append(ext(self))

    def unregister_all(self):
        """Unregister handlers"""
        del self.__extensions

        # Unregister handlers
        for handler in self.__handlers:
            self.bot.remove_handler(handler)

        command_registry.remove_all(self.module_info.name)

    def register_all(self, ext: Optional = None):
        """
        Method that initiates method registering. Must be called only from loader or extension!
        """
        methods = inspect.getmembers(ext if ext else self, inspect.ismethod)
        for name, func in methods:
            if hasattr(func, "bot_cmds"):
                # Func with @command decorator
                for cmd in func.bot_cmds:
                    if command_registry.check_command(cmd):
                        self.logger.warning(
                            f"Command conflict! "
                            f"Module {self.module_info.name} tried to register command {cmd}, which is already used! "
                            f"Skipping this command")
                    else:
                        command_registry.register_command(self.module_info.name, cmd)
                        final_filter = filters.command(cmd) & func.bot_msg_filter if func.bot_msg_filter \
                            else filters.command(cmd)
                        handler = MessageHandler(func, final_filter)
                        self.bot.add_handler(handler)
                        self.__handlers.append(handler)

                        if self.__auto_help is None:
                            self.__auto_help = "Available commands:\n"
                        self.__auto_help += f"/{cmd}" + (f" - {func.__doc__}" if func.__doc__ else "") + "\n"

            elif hasattr(func, "bot_callback_filter"):
                # Func with @callback_query decorator
                handler = CallbackQueryHandler(func, func.bot_callback_filter)
                self.bot.add_handler(handler)
                self.__handlers.append(handler)

        # Custom handlers
        for handler in ext.custom_handlers if ext else self.custom_handlers:
            self.bot.add_handler(handler)
            self.__handlers.append(handler)

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
        Defaults to auto-generated command listing, which uses callback func __doc__ for description
        """
        return self.__auto_help

    @property
    def custom_handlers(self) -> list[Handler]:
        """
        Custom handlers for something that exceeds message / callback query validation (raw messages, etc.)
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


def command(cmds: Union[list[str], str], filters: Optional[Filter] = None):
    """
    Decorator for registering module command
    :param cmds: List of commands w/o prefix. It may be a string if there's only one command
    :param filters: Final combined filter for validation. See https://docs.pyrogram.org/topics/use-filters
    """
    def wrapper(func: Callable):
        func.bot_cmds = cmds if type(cmds) == list else [cmds]
        func.bot_msg_filter = filters
        return func

    return wrapper


def callback_query(filters: Optional[Filter] = None):
    """
    Decorator for registering callback query handlers
    :param filters: Final combined filter for validation. See https://docs.pyrogram.org/topics/use-filters
    """
    def wrapper(func: Callable):
        func.bot_callback_filter = filters
        return func

    return wrapper
