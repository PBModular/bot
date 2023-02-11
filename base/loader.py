from base.module import BaseModule, ModuleInfo, Permissions
from base.base_ext import BaseExtension
from base.db import Database
from config import config

from pyrogram import Client

import importlib
import inspect
import logging
import os
import sys
import shutil
import subprocess
import yaml
from urllib.parse import urlparse
from typing import Optional, Union


logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(self, bot: Client, root_dir: str):
        self.__bot = bot
        self.__modules: dict[str, BaseModule] = {}
        self.__modules_info: dict[str, ModuleInfo] = {}
        self.__root_dir = root_dir

        # Load extensions
        self.__extensions: dict[str, BaseExtension] = {}
        extensions = os.listdir(path="./extensions/")
        for ext in extensions:
            if not os.path.isdir(f"./extensions/{ext}"):
                continue

            try:
                imported = importlib.import_module("extensions." + ext)
            except ImportError as e:
                logger.error(f"ImportError has occurred while loading extension {ext}!")
                logger.exception(e)
                continue

            for obj_name, obj in inspect.getmembers(imported, inspect.isclass):
                if BaseExtension in inspect.getmro(obj):
                    os.chdir(f"./extensions/{ext}")
                    try:
                        # Check for dependencies update / install them
                        if config.update_deps_at_load and "requirements.txt" in os.listdir():
                            self.install_deps(ext, "extensions")

                        instance: BaseExtension = obj()
                        name = instance.extension_info.name

                        self.__extensions[name] = instance

                        logger.info(f"Successfully loaded extension {name}!")
                        os.chdir("../../")
                    except Exception as e:
                        logger.error(f"Error at loading extension {ext}! Printing traceback")
                        logger.exception(e)
                        os.chdir(self.__root_dir)

    def load_everything(self):
        """Load all modules"""
        modules = os.listdir(path="./modules/")
        for module in modules:
            if os.path.isdir(f"./modules/{module}"):
                self.load_module(module)

    def load_module(self, name: str) -> Optional[str]:
        """
        Main loading method

        :param name: Name of Python module inside modules dir
        """
        try:
            imported = importlib.import_module("modules." + name)
        except ImportError as e:
            logger.error(f"ImportError has occurred while loading module {name}!")
            logger.exception(e)
            return None

        for obj_name, obj in inspect.getmembers(imported, inspect.isclass):
            if BaseModule in inspect.getmro(obj):
                os.chdir(f"./modules/{name}")
                try:
                    # Check for dependencies update / install them
                    if config.update_deps_at_load and "requirements.txt" in os.listdir():
                        self.install_deps(name, "modules")

                    instance: BaseModule = obj(self.__bot, self.get_modules_info)
                    perms = self.get_module_perms(name)
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

                    # Stage 1 init passed ok, applying extensions
                    for ext_name, ext in self.__extensions.items():
                        try:
                            ext.on_module(instance)
                        except Exception as e:
                            logger.error(f"Extension {ext_name} failed to apply on module {info.name}!")
                            logger.exception(e)

                    # Stage 2
                    # Register everything for pyrogram
                    instance.stage2()

                    self.__modules[name] = instance
                    self.__modules_info[name] = info

                    # Custom init execution
                    instance.on_init()

                    logger.info(f"Successfully imported module {info.name}!")
                    os.chdir("../../")
                    return info.name
                except Exception as e:
                    logger.error(f"Error at loading module {name}! Printing traceback")
                    logger.exception(e)
                    os.chdir(self.__root_dir)
                    return None

    def unload_module(self, name: str):
        """
        Method for unloading modules. Note: restart is a mandatory!
        :param name: Name of Python module inside modules dir
        """
        self.__modules[name].unregister_all()
        self.__modules.pop(name)
        self.__modules_info.pop(name)
        logger.info(f"Successfully unloaded module {name}!")

    def get_modules_info(self) -> dict[str, ModuleInfo]:
        """
        Get info about all loaded modules

        :return: Dictionary with ModuleInfo objects
        """
        return self.__modules_info

    def get_module_help(self, name: str) -> Optional[str]:
        mod = self.__modules.get(name)
        if mod is None:
            return None
        else:
            return mod.help_page

    def get_module_perms(self, name: str) -> list[Permissions]:
        file_path = f"{self.__root_dir}/modules/{name}/permissions.yaml"
        if os.path.exists(file_path):
            return [Permissions[val] for val in yaml.safe_load(open(file_path, encoding="utf-8"))]
        else:
            return []

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

        return p.returncode, p.stdout.decode("utf-8")

    def install_deps(self, name: str, directory: str) -> (int, Union[str, list[str]]):
        """
        Method to install Python dependencies from requirements.txt file
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :return: Tuple with exit code and read STDOUT
        """
        logger.info(f"Upgrading dependencies for {name}!")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "-r",
             f"{self.__root_dir}/{directory}/{name}/requirements.txt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        if r.returncode != 0:
            logger.error(f"Error at upgrading deps for {name}!\nPip output:\n"
                         f"{r.stdout.decode('utf-8')}")
            return r.returncode, r.stdout.decode('utf-8')
        else:
            logger.info(f"Deps upgraded successfully!")
            with open(f"{self.__root_dir}/{directory}/{name}/requirements.txt") as f:
                reqs = [dep for dep in f]
                if reqs[-1] == "":
                    reqs.pop(-1)

                return r.returncode, reqs

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
        except Exception as e:
            logger.error(f"Error while removing module {name}! Printing traceback...")
            logger.exception(e)
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
