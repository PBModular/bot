import importlib
import inspect
import os
from base.module import BaseModule, ModuleInfo
from aiogram import Dispatcher


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(self, dispatcher: Dispatcher):
        self.dp = dispatcher
        self.modules: list[ModuleInfo] = []

    def load_everything(self):
        """Load all modules"""
        modules = os.listdir(path='./modules/')
        for module in modules:
            self.load_module(module)

    def load_module(self, name: str):
        """
        Main loading method

        :param name: Name of Python module inside modules dir
        """
        imported = importlib.import_module('modules.' + name)
        for name, obj in inspect.getmembers(imported, inspect.isclass):
            if 'Module' in name:
                instance: BaseModule = obj(self)
                info = instance.module_info
                self.dp.include_router(instance.router)
                self.modules.append(info)
                print(f'Successfully imported module {info.name}!')

    def get_modules_info(self) -> list[ModuleInfo]:
        """
        Get info about all loaded modules

        :return: List of ModuleInfo objects
        """
        return self.modules
