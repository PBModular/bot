from base.module import BaseModule, ModuleInfo, Permissions
from base.base_ext import BaseExtension
from base.db import Database
from config import config

from pyrogram import Client

import requirements

import importlib
import inspect
import logging
import os
import sys
import shutil
import subprocess
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
        self.__modules_deps: dict[str, list[str]] = {}
        self.__root_dir = root_dir
        self.__hash_backups: dict[str, str] = {}

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
        # Force core module to load first
        if "core" in modules:
            modules.remove("core")
            modules.insert(0, "core")

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
                    if "requirements.txt" in os.listdir():
                        # Check for dependencies update / install them
                        if config.update_deps_at_load:
                            self.install_deps(name, "modules")

                        # Load dependencies into dict
                        self.__modules_deps[name] = []
                        for req in requirements.parse(open("requirements.txt", encoding='utf-8')):
                            self.__modules_deps[name].append(req.name.lower())

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

                    # Remove hash backup
                    if self.__hash_backups.get(name) is not None:
                        self.__hash_backups.pop(name)

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

    def get_module(self, name: str) -> Optional[BaseModule]:
        """
        Get module instance object
        :param name: Name of Python module inside modules dir
        :return: Module object
        """
        return self.__modules.get(name)

    def get_modules_info(self) -> dict[str, ModuleInfo]:
        """
        Get info about all loaded modules

        :return: Dictionary with ModuleInfo objects
        """
        return self.__modules_info

    def get_module_info(self, name: str) -> Optional[ModuleInfo]:
        """
        Get module info
        :param name: Name of Python module inside modules dir
        :return: Object with module info
        """
        mod = self.__modules.get(name)
        if mod is None:
            return None
        else:
            return mod.module_info

    def get_module_help(self, name: str) -> Optional[str]:
        """
        Get module help page
        :param name: Name of Python module inside modules dir
        :return: Help page as string
        """
        mod = self.__modules.get(name)
        if mod is None:
            return None
        else:
            return mod.help_page

    def get_module_perms(self, name: str) -> list[Permissions]:
        """
        Get module permissions
        :param name: Name of Python module inside modules dir
        :return: Object with permissions
        """
        mod = self.__modules.get(name)
        if mod is None:
            return []
        else:
            return mod.module_permissions

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

    def update_from_git(self, name: str, directory: str) -> (int, str):
        """
        Method to update git repository (module or extensions)
        Remembers commit hash for reverting and executes git pull
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :return: Exit code and output of git pull
        """
        # Unload first
        self.unload_module(name)
        logger.info(f"Updating {name}!")

        # Backup
        hash_cmd = f"cd {self.__root_dir}/{directory}/{name}/\n" \
                   f"git rev-parse HEAD"
        hash_p = subprocess.run(hash_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if hash_p.returncode != 0:
            logger.error(f"Wtf, failed to retrieve HEAD hash... STDOUT below")
            logger.error(hash_p.stdout.decode("utf-8"))
            return hash_p.returncode, hash_p.stdout.decode("utf-8")

        self.__hash_backups[name] = hash_p.stdout.decode("utf-8")

        cmd = f"cd {self.__root_dir}/{directory}/{name}/\n" \
              f"git pull"
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if p.returncode != 0:
            logger.error(f"Error while updating module {name}!")
            logger.error(f"Printing STDOUT and STDERR:")
            logger.error(p.stdout.decode("utf-8"))

        return p.returncode, p.stdout.decode("utf-8")

    def revert_update(self, name: str, directory: str) -> bool:
        """
        Reverts update caused by update_from_git(). Removes updated dir and places backup
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :return: Boolean (success or not)
        """
        try:
            cmd = f"cd {self.__root_dir}/{directory}/{name}/\n" \
                  f"git reset --hard {self.__hash_backups[name]}"
            p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            if p.returncode != 0:
                logger.error(f"Failed to revert update of module {name}! Printing STDOUT")
                logger.error(p.stdout.decode("utf-8"))
                return False

            logger.info(f"Update of module {name} reverted!")
            return True
        except KeyError:
            logger.error(f"Tried to revert module {name} with no pending update!")
            return False

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
                reqs = [dep.removesuffix("\n") for dep in f]
                if reqs[-1] == "":
                    reqs.pop(-1)

                return r.returncode, reqs

    def uninstall_mod_deps(self, name: str):
        """
        Method to uninstall module dependencies. Removes package only if it isn't required by other module
        :param name: Name of module
        :return:
        """
        for mod_dep in self.__modules_deps[name]:
            found = False
            for other_name, deps in self.__modules_deps.items():
                if other_name == name:
                    continue
                if mod_dep in deps:
                    found = True
                    break
            if found:
                continue

            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", mod_dep],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

    def uninstall_packages(self, pkgs: list[str]):
        for dep in pkgs:
            found = False
            for other_name, deps in self.__modules_deps.items():
                if dep in deps:
                    found = True
                    break
            if found:
                continue

            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", dep],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

    def uninstall_module(self, name: str) -> bool:
        """
        Module uninstallation method. Unloads and removes module directory
        :param name: Name of Python module inside modules dir
        :return: Bool, representing success or not
        """
        try:
            # Unload first
            self.unload_module(name)
            # Remove deps
            self.uninstall_mod_deps(name)
            self.__modules_deps.pop(name)
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
