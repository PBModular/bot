import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import inspect
import os

from aiogram.dispatcher.router import Router
from aiogram.filters import Command, Filter

from sqlalchemy.orm import Session
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
    requires_packages: Optional[list[str]] = None  # Not used for now


@dataclass
class Handler:
    filter: Filter
    func: Callable


class Permissions(str, Enum):
    use_db = 'use_db'
    use_loader = 'use_loader'


class BaseModule(ABC):
    def __init__(self, loaded_info_func: Callable):
        self.logger = logging.getLogger(__name__)
        self.router = Router()

        self.__loaded_info = loaded_info_func

        # Register all methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if "_cmd" in name:
                self.router.message.register(func, Command(name.removesuffix("_cmd")))
                command_registry.register_command(self.module_info.name, name.removesuffix("_cmd"))

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

        # Load translations if available
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
                self.S = self.rawS[config.fallback_language]
            else:
                self.logger.warning(
                    f"Can't select language... Using first in list, you've been warned!"
                )
                self.S = list(self.rawS.values())[0]
        except FileNotFoundError:
            pass

        # Place for database session. Will be set by loader if necessary
        self.db_session: Optional[Session] = None

        # Place for loader
        self.loader = None

    def __del__(self):
        self.router.emit_shutdown()

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
