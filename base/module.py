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
    def __init__(self):
        self.router = Router()

        # Register all methods
        methods = inspect.getmembers(self, inspect.ismethod)
        for name, func in methods:
            if '_cmd' in name:
                self.router.message.register(Command(name.removesuffix('_cmd')), func)

    @property
    @abstractmethod
    def module_info(self) -> ModuleInfo:
        """Module info. Must be set"""
        pass

    def on_init(self):
        """Called when module should initialize itself. Optional"""
        pass
    