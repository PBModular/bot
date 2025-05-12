from base.module import BaseModule, ModuleInfo, Permissions, HelpPage
from base.base_ext import BaseExtension
from base.db import Database
from config import config
from base.mod_manager import ModuleManager

from pyrogram import Client
import requirements
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine

import asyncio
import importlib
import inspect
import logging
import os
import sys
import yaml
from typing import Optional, Union
import gc

logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Main module dispatcher
    Modules must be placed into modules/ directory as directories with __init__.py
    """

    def __init__(
        self,
        bot: Client,
        root_dir: str,
        bot_db_session: async_sessionmaker,
        bot_db_engine: AsyncEngine,
    ):
        self.__bot = bot
        self.__modules: dict[str, BaseModule] = {}
        self.__modules_info: dict[str, ModuleInfo] = {}
        self.__all_modules_info: dict[str, ModuleInfo] = {}
        self.__modules_deps: dict[str, list[str]] = {}
        self.__root_dir = root_dir
        self.bot_db_session = bot_db_session
        self.bot_db_engine = bot_db_engine
        
        # Initialize the module manager
        self.mod_manager = ModuleManager(root_dir)

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
                        if (
                            config.update_deps_at_load
                            and "requirements.txt" in os.listdir()
                        ):
                            self.mod_manager.install_deps(ext, "extensions")

                        instance: BaseExtension = obj()
                        name = instance.extension_info.name

                        self.__extensions[name] = instance

                        logger.info(f"Successfully loaded extension {name}!")
                        os.chdir("../../")
                    except Exception as e:
                        logger.error(
                            f"Error at loading extension {ext}! Printing traceback"
                        )
                        logger.exception(e)
                        os.chdir(self.__root_dir)

    def load_everything(self):
        """Load all modules with auto_load enabled and gather info for all modules"""
        modules = os.listdir(path="./modules/")
        if "core" in modules:
            modules.remove("core")
            modules.insert(0, "core")

        modules_to_load = []
        all_modules = []
        
        for module in modules:
            if not os.path.isdir(f"./modules/{module}"):
                continue
                
            all_modules.append(module)
            auto_load = True
            
            config_path = f"./modules/{module}/config.yaml"
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r") as f:
                        config_data = yaml.safe_load(f) or {}
                    auto_load = config_data.get("info", {}).get("auto_load", True)
                except Exception as e:
                    logger.error(f"Error reading config.yaml for module {module}: {e}")

            if auto_load:
                modules_to_load.append(module)
            else:
                logger.info(f"Module {module} has auto_load set to False, skipping loading")
        
        for module in modules_to_load:
            self.load_module(module)
        
        # Populate info for all modules (loaded or not)
        for module in all_modules:
            if module not in self.__modules_info:
                # Create basic info for non-loaded modules
                try:
                    config_path = f"./modules/{module}/config.yaml"
                    if os.path.exists(config_path):
                        with open(config_path, "r") as f:
                            config_data = yaml.safe_load(f) or {}
                        info_block = config_data.get("info", {})
                        mod_info = ModuleInfo(
                            name=info_block.get("name", module),
                            author=info_block.get("author", ""),
                            version=info_block.get("version", ""),
                            description=info_block.get("description", ""),
                            src_url=info_block.get("src_url", ""),
                            python=info_block.get("python", ""),
                            auto_load=info_block.get("auto_load", True)
                        )
                    else:
                        mod_info = ModuleInfo(
                            name=module,
                            author="",
                            version="0.0.0",
                            description="config.yaml not found.",
                            src_url="",
                            python="",
                            auto_load=True
                        )
                    self.__all_modules_info[module] = mod_info
                except Exception as e:
                    logger.error(f"Error creating info for non-loaded module {module}: {e}")

    def load_module(self, name: str, skip_deps: bool = False) -> Optional[str]:
        """
        Main loading method

        :param name: Name of Python module inside modules dir
        """
        module_path = f"./modules/{name}"
        if not os.path.exists(module_path):
            logger.error(f"Module directory {module_path} does not exist")
            return None
        
        try:
            os.chdir(module_path)

            if "requirements.txt" in os.listdir():
                if config.update_deps_at_load and not skip_deps:
                    self.mod_manager.install_deps(name, "modules")

                # Load dependencies into dict
                self.__modules_deps[name] = []
                for req in requirements.parse(
                        open("requirements.txt", encoding="utf-8")
                ):
                    self.__modules_deps[name].append(req.name.lower())

            try:
                imported = importlib.import_module("modules." + name)
            except ImportError as e:
                logger.error(f"ImportError has occurred while loading module {name}!")
                logger.exception(e)
                return None

            for obj_name, obj in inspect.getmembers(imported, inspect.isclass):
                if BaseModule in inspect.getmro(obj):
                    try:
                        instance: BaseModule = obj(
                            self.__bot,
                            self.get_modules_info,
                            self.bot_db_session,
                            self.bot_db_engine,
                        )
                        perms = instance.module_permissions
                        info = instance.module_info

                        # Version check
                        if info.python:
                            parts = tuple(map(int, info.python.split('.')))
                            current_version = '.'.join(map(str, sys.version_info[:3]))
                            if sys.version_info[1] != parts[1]:
                                logger.warning(
                                    f"Module {name} tested on Python {info.python}, "
                                    f"current version is {current_version}, proceed with caution!"
                                )

                        # Don't allow modules with more than 1 word in name
                        if len(info.name.split()) > 1:
                            logger.warning(f"Module {name} has invalid name. Skipping!")
                            del instance
                            return None

                        if Permissions.require_db in perms and not config.enable_db:
                            logger.warning(f"Module {name} requires DB, but it's disabled. Skipping!")
                            del instance
                            return None

                        if (Permissions.use_db in perms or Permissions.require_db in perms) and config.enable_db:
                            os.chdir(self.__root_dir)
                            asyncio.create_task(instance.set_db(Database(name)))
                            os.chdir(module_path)

                        if Permissions.use_loader in perms:
                            instance.loader = self

                        # Stage 1 init passed ok, applying extensions
                        for ext_name, ext in self.__extensions.items():
                            try:
                                ext.on_module(instance)
                            except Exception as e:
                                logger.error(f"Extension {ext_name} failed on module {info.name}!")
                                logger.exception(e)

                        # Stage 2
                        # Register everything for pyrogram
                        instance.stage2()

                        self.__modules[name] = instance
                        self.__modules_info[name] = info
                        self.__all_modules_info[name] = info

                        # Custom init execution
                        instance.on_init()

                        # Clear hash backup if present
                        self.mod_manager.clear_hash_backup(name)
                        logger.info(f"Successfully imported module {info.name}!")
                        return info.name
                    except Exception as e:
                        logger.error(f"Error loading module {name}! Printing traceback")
                        logger.exception(e)
                        return None
            return None
        finally:
            os.chdir(self.__root_dir)

    async def unload_module(self, name: str):
        """
        Method for unloading modules.

        :param name: Name of Python module inside modules dir
        """
        # Before unloading, store the module info
        if name in self.__modules_info:
            self.__all_modules_info[name] = self.__modules_info[name]

        if module := self.__modules.get(name):
            module._BaseModule__state_machines.clear()

        self.__modules[name].on_unload()
        await self.__modules[name].unregister_all()
        self.__modules.pop(name)
        self.__modules_info.pop(name)
        try:
            self.__modules_deps.pop(name)
        except KeyError:
            pass

        # Clear imports
        del_keys = [key for key in sys.modules.keys() if name in key]
        for key in del_keys:
            del sys.modules[key]
        
        gc.collect()
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

    def get_all_modules_info(self) -> dict[str, ModuleInfo]:
        """
        Get info about all modules, including unloaded ones
        
        :return: Dictionary with ModuleInfo objects for all modules
        """
        return self.__all_modules_info

    def get_module_info(self, name: str) -> Optional[ModuleInfo]:
        """
        Get module info regardless of load status

        :param name: Name of Python module inside modules dir
        :return: Object with module info
        """
        mod_info = self.__modules_info.get(name)
        if mod_info is None:
            return self.__all_modules_info.get(name)
        else:
            return mod_info

    def get_module_help(self, name: str) -> Optional[Union[HelpPage, str]]:
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

    def get_modules_deps(self) -> dict[str, list[str]]:
        """
        Get module deps

        :return: __modules_deps object
        """
        return self.__modules_deps

    def get_int_name(self, name: str) -> Optional[str]:
        """
        Get internal name (name of a directory) of a module from user-friendly name

        :param name: User-friendly name of a module
        :return: Internal name of a module
        """
        for n, info in self.__all_modules_info.items():
            if info.name.lower() == name.lower():
                return n

        return None

    async def prepare_for_module_update(self, name: str) -> Optional[BaseModule]:
        """
        Unload module if loaded to prepare for update

        :param name: Name of Python module inside modules dir
        :return: The module instance that was unloaded, or None if not loaded
        """
        module = None
        if name in self.__modules:
            module = self.__modules[name]
            await self.unload_module(name)
        return module
