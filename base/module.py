from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import inspect

from aiogram.dispatcher.router import Router
from aiogram.filters import Command

@dataclass
class ModuleInfo:
    name: str
    author: str
    version: str
    src_url: Optional[str] = None
    requires_packages: Optional[list[str]] = None  # Not used for now


class BaseModule(ABC):
    def __init__(self, loader: Optional = None):
        self.router = Router()

        if loader is not None:
            self.__loader = loader

        # Register all methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if '_cmd' in name:
                self.router.message.register(func, Command(name.removesuffix('_cmd')))

    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """Module info. Must be set"""
        pass

    def on_init(self):
        """Called when module should initialize itself. Optional"""
        pass

    def get_loaded_modules(self) -> list[ModuleInfo]:
        """
        Method for querying loaded modules from child instance
        :return: List of loaded modules info
        """
        return self.__loader.get_modules_info()
