import importlib
import inspect
import logging
import os
from base.module import BaseModule, ModuleInfo
from aiogram import Dispatcher


logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(self, dispatcher: Dispatcher):
        self.__dp = dispatcher
        self.__modules: list[BaseModule] = []
        self.__modules_info: list[ModuleInfo] = []

    def load_everything(self):
        """Load all modules"""
        modules = os.listdir(path="./modules/")
        for module in modules:
            self.load_module(module)

    def load_module(self, name: str):
        """
        Main loading method

        :param name: Name of Python module inside modules dir
        """
        imported = importlib.import_module("modules." + name)
        for obj_name, obj in inspect.getmembers(imported, inspect.isclass):
            if "Module" in obj_name:
                os.chdir(f"./modules/{name}")
                instance: BaseModule = obj(self)
                info = instance.module_info
                self.__dp.include_router(instance.router)
                self.__modules.append(instance)
                self.__modules_info.append(info)
                logger.info(f"Successfully imported module {info.name}!")

    def get_modules_info(self) -> list[ModuleInfo]:
        """
        Get info about all loaded modules

        :return: List of ModuleInfo objects
        """
        return self.__modules_info
