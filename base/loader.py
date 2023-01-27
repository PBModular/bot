import importlib
import inspect
import logging
import os
from typing import Optional
from base.module import BaseModule, ModuleInfo, Permissions
from aiogram import Dispatcher
from sqlalchemy.orm import Session
from sqlalchemy import Engine


logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(self, dispatcher: Dispatcher, db_base: Optional[Session] = None, db_engine: Optional[Engine] = None):
        self.__dp = dispatcher
        self.__modules: list[BaseModule] = []
        self.__modules_info: list[ModuleInfo] = []
        self.__modules_help: dict[str, str] = {}
        self.__db_session: Optional = db_base
        self.__db_engine = db_engine

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
                instance: BaseModule = obj(self.get_modules_info)
                perms = instance.module_permissions
                if Permissions.use_db in perms and self.__db_session:
                    self.__init_db(instance)

                if Permissions.use_loader in perms:
                    instance.loader = self

                info = instance.module_info
                self.__dp.include_router(instance.router)
                self.__modules.append(instance)
                self.__modules_info.append(info)

                help_page = instance.help_page
                if help_page:
                    self.__modules_help[info.name.lower()] = help_page

                # Custom init execution
                instance.on_init()

                logger.info(f"Successfully imported module {info.name}!")
                os.chdir("../../")

    def __init_db(self, instance: BaseModule):
        # Insert db session into module
        instance.db_session = self.__db_session

        # Emit tables to database
        instance.db_meta.create_all(self.__db_engine)

    def get_modules_info(self) -> list[ModuleInfo]:
        """
        Get info about all loaded modules

        :return: List of ModuleInfo objects
        """
        return self.__modules_info

    def get_module_help(self, name: str) -> Optional[str]:
        return self.__modules_help.get(name)
