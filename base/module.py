import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable
import inspect
import os

from aiogram.dispatcher.router import Router
from aiogram.filters import Command, Filter

import yaml
from config import config

logger = logging.getLogger(__name__)


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


class BaseModule(ABC):
    def __init__(self, loader: Optional = None):
        self.router = Router()

        if loader is not None:
            self.__loader = loader

        # Register all methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if "_cmd" in name:
                self.router.message.register(func, Command(name.removesuffix("_cmd")))

        for handler in self.message_handlers:
            self.router.message.register(handler.func, handler.filter)

        for handler in self.callback_handlers:
            self.router.callback_query.register(handler.func, handler.filter)

        # Load translations if available
        files = os.listdir("./")
        if "strings.yml" in files or "strings.yaml" in files:
            self.rawS: dict = yaml.safe_load(
                open("./strings.yaml" if "strings.yaml" in files else "strings.yml")
            )
            logger.info(f"Available translations: {list(self.rawS.keys())}")
            if config.language in self.rawS.keys():
                self.S = self.rawS[config.language]
            elif config.fallback_language in self.rawS.keys():
                logger.warning(
                    f"Language {config.language} not found! Falling back to {config.fallback_language}"
                )
                self.S = self.rawS[config.fallback_language]
            else:
                logger.warning(
                    f"Can't select language... Using first in list, you've been warned!"
                )
                self.S = list(self.rawS.values())[0]

    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """Module info. Must be set"""
        pass

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
    def loaded_modules(self) -> list[ModuleInfo]:
        """
        Method for querying loaded modules from child instance
        :return: List of loaded modules info
        """
        return self.__loader.get_modules_info()
