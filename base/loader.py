import importlib
import inspect
import logging
import os
import shutil
import subprocess
from urllib.parse import urlparse
import traceback
from typing import Optional
from base.module import BaseModule, ModuleInfo, Permissions
from aiogram import Dispatcher, Bot
from base.db import Database
from config import config


logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(self, bot: Bot, dispatcher: Dispatcher, root_dir: str):
        self.__bot = bot
        self.__dp = dispatcher
        self.__modules: dict[str, BaseModule] = {}
        self.__modules_info: dict[str, ModuleInfo] = {}
        self.__modules_help: dict[str, str] = {}
        self.__root_dir = root_dir

    def load_everything(self):
        """Load all modules"""
        modules = os.listdir(path="./modules/")
        for module in modules:
            self.load_module(module)

    def load_module(self, name: str) -> Optional[str]:
        """
        Main loading method

        :param name: Name of Python module inside modules dir
        """
        imported = importlib.import_module("modules." + name)
        for obj_name, obj in inspect.getmembers(imported, inspect.isclass):
            if BaseModule in inspect.getmro(obj):
                os.chdir(f"./modules/{name}")
                try:
                    instance: BaseModule = obj(self.__bot, self.get_modules_info)
                    perms = instance.module_permissions
                    info = instance.module_info

                    # Don't allow modules with more than 1 word in name
                    if len(info.name.split()) > 1:
                        logger.warning(f"Module {name} has more than 1 word in name. Fuck developer! I won't load it!")
                        del instance
                        os.chdir("../../")
                        return None

                    if Permissions.require_db in perms and not config.enable_db:
                        logger.warning(f"Module {name} requires DB, but it was disabled, skipping!")
                        del instance
                        os.chdir("../../")
                        return None

                    if (Permissions.use_db in perms or Permissions.require_db in perms) and config.enable_db:
                        os.chdir(self.__root_dir)
                        instance.db = Database(name)
                        os.chdir(f"./modules/{name}")

                    if Permissions.use_loader in perms:
                        instance.loader = self

                    # Register everything for aiogram
                    instance.register_all()

                    self.__dp.include_router(instance.router)
                    self.__modules[name] = instance
                    self.__modules_info[name] = info

                    help_page = instance.help_page
                    if help_page:
                        self.__modules_help[info.name.lower()] = help_page

                    # Custom init execution
                    instance.on_init()

                    logger.info(f"Successfully imported module {info.name}!")
                    os.chdir("../../")
                    return info.name
                except:
                    logger.error(f"Error at loading module {name}! Printing traceback")
                    traceback.print_exc()
                    os.chdir(self.__root_dir)
                    return None

    def unload_module(self, name: str):
        """
        Method for unloading modules. Note: restart is a mandatory!
        :param name: Name of Python module inside modules dir
        """
        self.__modules.pop(name)
        info = self.__modules_info.pop(name)
        try:
            self.__modules_help.pop(info.name.lower())
        except KeyError:
            pass
        logger.info(f"Successfully unloaded module {name}!")

    def get_modules_info(self) -> dict[str, ModuleInfo]:
        """
        Get info about all loaded modules

        :return: Dictionary with ModuleInfo objects
        """
        return self.__modules_info

    def get_module_help(self, name: str) -> Optional[str]:
        return self.__modules_help.get(name)

    def install_from_git(self, url: str) -> (int, str):
        """
        Module installation method. Clones git repository from the given URL and loads it
        :param url: Git repository URL
        :return: Tuple with exit code and read STDOUT
        """
        logger.info(f"Downloading module from git URL {url}!")
        name = urlparse(url).path.split('/')[-1].removesuffix('.git')
        cmd = f"cd {self.__root_dir}/modules\n" \
              f"git clone {url}"
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if p.returncode != 0:
            logger.error(f"Error while cloning module {name}!")
            logger.error(f"Printing STDOUT and STDERR:")
            logger.error(p.stdout.decode('utf-8'))
            subprocess.run(["rm", f"{self.__root_dir}/modules/{name}"])

        return p.returncode, p.stdout

    def uninstall_module(self, name: str) -> bool:
        """
        Module uninstallation method. Unloads and removes module directory
        :param name: Name of Python module inside modules dir
        :return: Bool, representing success or not
        """
        try:
            # Unload first
            self.unload_module(name)
            shutil.rmtree(f"./modules/{name}")
            logger.info(f"Successfully removed module {name}!")
            return True
        except:
            logger.error(f"Error while removing module {name}! Printing traceback...")
            traceback.print_exc()
            return False

    def get_int_name(self, name: str) -> Optional[str]:
        """
        Get internal name (name of a directory) of a module from user-friendly name
        :param name: User-friendly name of a module
        :return: Internal name of a module
        """
        for n, info in self.__modules_info.items():
            if info.name.lower() == name.lower():
                return n

        return None
