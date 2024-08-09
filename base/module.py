import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union, Callable, Type
import inspect
import os
from functools import wraps
import asyncio
from copy import deepcopy

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton
from pyrogram.filters import Filter
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.handlers.handler import Handler
from pyrogram.enums import ChatMemberStatus

from base.db import Database
from sqlalchemy import MetaData, Engine, select
from sqlalchemy.orm import Session
from db import CommandPermission, User

import yaml
from config import config
from base import command_registry
from dataclass_wizard import YAMLWizard
from base.states import StateMachine, State


@dataclass
class ModuleInfo:
    name: str
    author: str
    version: str
    description: str
    src_url: Optional[str] = None
    python: Optional[str] = None


class Permissions(str, Enum):
    use_db = "use_db"
    require_db = "require_db"
    use_loader = "use_loader"


@dataclass
class InfoFile(YAMLWizard):
    info: ModuleInfo
    permissions: list[Permissions] = field(default_factory=list)


@dataclass
class HelpPage:
    text: str
    buttons: Optional[list[list[InlineKeyboardButton]]] = None


def merge_dicts(dict_a: dict, dict_b: dict):
    for key in dict_b.keys():
        if key in dict_a and isinstance(dict_a[key], dict) and isinstance(dict_b[key], dict):
            merge_dicts(dict_a[key], dict_b[key])
        else:
            dict_a[key] = dict_b[key]


class BaseModule(ABC):
    """
    Bot module superclass
    """

    def __init__(
        self,
        bot: Client,
        loaded_info_func: Callable,
        bot_db_session: Session,
        bot_db_engine: Engine,
    ):
        self.bot = bot
        self.__loaded_info = loaded_info_func

        # Parse info and extensions
        info_file = InfoFile.from_yaml_file("./info.yaml")
        self.module_info = info_file.info
        self.module_permissions = info_file.permissions

        self.logger = logging.getLogger(self.module_info.name)

        # Load translations if available
        self.cur_lang = config.language
        try:
            files = os.listdir("./strings/")
            self.rawS = {}
            for file in files:
                self.rawS[file.removesuffix(".yaml")] = yaml.safe_load(
                    open(f"./strings/{file}", encoding="utf-8")
                )

            self.logger.info(f"Available translations: {list(self.rawS.keys())}")
            if config.language in self.rawS.keys():
                if config.fallback_language in self.rawS.keys():
                    self.S = deepcopy(self.rawS[config.fallback_language])

                    # Merge fallback lang and main, eliminating missing items
                    merge_dicts(self.S, self.rawS[config.language])
                else:
                    self.logger.warning(
                        f"Fallback language is not found, unable to merge translations!"
                    )
                    self.S = self.rawS[config.language]
            elif config.fallback_language in self.rawS.keys():
                self.logger.warning(
                    f"Language {config.language} not found! Falling back to {config.fallback_language}"
                )
                self.cur_lang = config.fallback_language
                self.S = self.rawS[config.fallback_language]
            else:
                self.logger.warning(
                    f"Can't select language... Using first in list, you've been warned!"
                )
                self.S = list(self.rawS.values())[0]
        except FileNotFoundError:
            pass

        # Global bot database
        self.__bot_db_session = bot_db_session
        self.__bot_db_engine = bot_db_engine

        # Place for database session. Will be set by loader if necessary
        self.__db: Optional[Database] = None

        # Place for loader
        self.loader = None

        # Place for message handlers and extensions
        self.__extensions = []
        self.__handlers = []

        # Auto-generated help
        self.__auto_help: Optional[HelpPage] = None

        # State machines for users
        self.__state_machines = {}

    def stage2(self):
        self.register_all()
        # Load extensions
        for ext in self.module_extensions:
            self.__extensions.append(ext(self))

    def unregister_all(self):
        """Unregister handlers"""
        del self.__extensions

        # Unregister handlers
        for handler in self.__handlers:
            self.bot.remove_handler(handler)
        
        self.__handlers = {}

        command_registry.remove_all(self.module_info.name)

        # Close database
        async def _close_db():
            if self.__db:
                await self.__db.engine.dispose()
                self.__db = None
        
        asyncio.create_task(_close_db())

    def register_all(self, ext = None):
        """
        Method that initiates method registering. Must be called only from loader or extension!
        """
        methods = inspect.getmembers(ext if ext else self, inspect.ismethod)
        for name, func in methods:
            if hasattr(func, "bot_cmds"):
                # Func with @command decorator
                for cmd in func.bot_cmds:
                    if command_registry.check_command(cmd):
                        self.logger.warning(
                            f"Command conflict! "
                            f"Module {self.module_info.name} tried to register command {cmd}, which is already used! "
                            f"Skipping this command"
                        )
                    else:
                        command_registry.register_command(self.module_info.name, cmd)
                        final_filter = (
                            filters.command(cmd) & func.bot_msg_filter
                            if func.bot_msg_filter
                            else filters.command(cmd)
                        ) & filters.create(
                            self.__check_role,
                            handler=func,
                            session=self.__bot_db_session,
                        )
                        final_filter = self.__add_fsm_filter(func, final_filter)

                        handler = MessageHandler(func, final_filter)
                        self.bot.add_handler(handler)
                        self.__handlers.append(handler)

                        if self.__auto_help is None:
                            self.__auto_help = HelpPage("")
                        
                        self.__auto_help.text += (
                            f"<code>/{cmd}</code>"
                            + (f" - {func.__doc__}" if func.__doc__ else "")
                            + "\n"
                        )

            elif hasattr(func, "bot_callback_filter"):
                # Func with @callback_query decorator
                final_filter = filters.create(
                    self.__check_role, handler=func, session=self.__bot_db_session
                )
                if func.bot_callback_filter is not None:
                    final_filter = final_filter & func.bot_callback_filter

                final_filter = self.__add_fsm_filter(func, final_filter)

                handler = CallbackQueryHandler(func, final_filter)
                self.bot.add_handler(handler)
                self.__handlers.append(handler)

            elif hasattr(func, "bot_msg_filter"):
                # Func with @message decorator
                final_filter = filters.create(
                    self.__check_role, handler=func, session=self.__bot_db_session
                )
                if func.bot_msg_filter is not None:
                    final_filter = final_filter & func.bot_msg_filter

                final_filter = self.__add_fsm_filter(func, final_filter)

                handler = MessageHandler(func, final_filter)
                self.bot.add_handler(handler)
                self.__handlers.append(handler)

        # Custom handlers
        for handler in ext.custom_handlers if ext else self.custom_handlers:
            self.bot.add_handler(handler)
            self.__handlers.append(handler)
    
    def __add_fsm_filter(self, func: Callable, final_filter: Filter) -> Filter:
        if hasattr(func, "bot_fsm_states"):
            if self.state_machine is None:
                self.logger.warning(f"Handler {func.__name__} tries to use FSM, but it wasn't defined!")
                return

            return final_filter & filters.create(
                self.__check_fsm_state,
                handler=func,
                state_machines=self.__state_machines,
                state_machine=self.state_machine
            )
        else:
            return final_filter

    @staticmethod
    async def __check_role(flt: Filter, client: Client, update) -> bool:
        async with flt.session() as session:
            if hasattr(flt.handler, "bot_cmds"):
                db_command = await session.scalar(
                    select(CommandPermission).where(
                        CommandPermission.command == update.text.split()[0][1:]
                    )
                )
                if db_command is None and not hasattr(flt.handler, "bot_allowed_for"):
                    return True

                allowed_to = (
                    db_command.allowed_for.split(":")
                    if db_command
                    else flt.handler.bot_allowed_for
                )
            else:
                if not hasattr(flt.handler, "bot_allowed_for"):
                    return True

                allowed_to = flt.handler.bot_allowed_for

            db_user = await session.scalar(
                select(User).where(User.id == update.from_user.id)
            )
            if (
                "all" in allowed_to
                or f"@{update.from_user.username}" in allowed_to
                or (db_user is not None and db_user.role in allowed_to)
                or update.from_user.username == config.owner
                or update.from_user.id == config.owner
            ):
                return True
            if "owner" in allowed_to and (
                update.from_user.id == config.owner
                or update.from_user.username == config.owner
            ):
                return True

            if "chat_owner" in allowed_to or "chat_admins" in allowed_to:
                member = await client.get_chat_member(
                    chat_id=update.chat.id, user_id=update.from_user.id
                )
                if (
                    "chat_owner" in allowed_to
                    and member.status == ChatMemberStatus.OWNER
                ) or (
                    "chat_admins" in allowed_to
                    and member.status == ChatMemberStatus.ADMINISTRATOR
                ):
                    return True

            return False
    
    @staticmethod
    async def __check_fsm_state(flt: Filter, client: Client, update) -> bool:
        machine = flt.state_machines.get(update.from_user.id)
        if machine is None:
            machine = flt.state_machine()
            flt.state_machines[update.from_user.id] = machine
        
        for state in flt.handler.bot_fsm_states:
            if machine.cur_state == state:
                return True
        
        return False

    @property
    def module_extensions(self) -> list[Type]:
        """
        List of module extension classes. Override if necessary.
        """
        return []

    @property
    def db(self):
        return self.__db

    async def set_db(self, value):
        """
        Setter for DB object. Creates tables from db_meta if available
        """
        self.__db = value
        if self.db_meta:
            async with self.__db.engine.begin() as conn:
                await conn.run_sync(self.db_meta.create_all)
                await self.on_db_ready()

    @property
    def db_meta(self):
        """
        SQLAlchemy MetaData object. Must be set if using database
        :rtype: MetaData
        """
        return None
    
    @property
    def state_machine(self):
        """
        StateMachine class for usage in handlers. Override if necessary.
        :rtype: Type[StateMachine]
        """
        return None

    async def start_cmd(self, bot: Client, message: Message):
        """
        Start command handler, which will be called from main start dispatcher.
        For example: /start BestModule will execute this func in BestModule
        :return:
        """

    @property
    def help_page(self) -> Optional[Union[HelpPage, str]]:
        """
        Help page to be displayed in Core module help command. Highly recommended to set this!
        Defaults to auto-generated command listing, which uses callback func __doc__ for description
        Can be a string for backward compatibility
        """
        return self.__auto_help

    @property
    def custom_handlers(self) -> list[Handler]:
        """
        Custom handlers for something that exceeds message / callback query validation (raw messages, etc.)
        Override if necessary
        """
        return []

    def on_init(self):
        """Called when module should initialize itself. Optional"""
        pass

    async def on_db_ready(self):
        """Called when module's database is fully initialized. Optional"""
        pass

    def on_unload(self):
        """Called on module unloading. Optional"""
        pass

    @property
    def loaded_modules(self) -> dict[str, ModuleInfo]:
        """
        Method for querying loaded modules from child instance
        :return: List of loaded modules info
        """
        return self.__loaded_info()
    
    def get_sm(self, update) -> Optional[StateMachine]:
        """
        Get state machine for current user session
        :param update: Pyrogram update object (Message, CallbackQuery, etc.)
        """
        machine = self.__state_machines.get(update.from_user.id)
        if machine is None:
            machine = self.state_machine()
            self.__state_machines[update.from_user.id] = machine
        
        return machine


def command(cmds: Union[list[str], str], filters: Optional[Filter] = None, fsm_state: Optional[Union[State, list[State]]] = None):
    """
    Decorator for registering module command.
    If FSM is present and the handler func has 4 args, then FSM for current user session is passed as a fourth parameter.
    :param cmds: List of commands w/o prefix. It may be a string if there's only one command
    :param filters: Final combined filter for validation. See https://docs.pyrogram.org/topics/use-filters
    :param fsm_state: FSM states at which this handler is allowed to run
    """

    def _command(func: Callable):
        @wraps(func)
        async def inner(self: BaseModule, client, update):
            await _launch_handler(func, self, client, update)
        
        inner.bot_cmds = cmds if type(cmds) == list else [cmds]
        inner.bot_msg_filter = filters
        
        if fsm_state is not None:
            inner.bot_fsm_states = fsm_state if type(fsm_state) == list else [fsm_state]
        
        return inner

    return _command


def callback_query(filters: Optional[Filter] = None, fsm_state: Optional[Union[State, list[State]]] = None):
    """
    Decorator for registering callback query handlers
    If FSM is present and the handler func has 4 args, then FSM for current user session is passed as a fourth parameter.
    :param filters: Final combined filter for validation. See https://docs.pyrogram.org/topics/use-filters
    :param fsm_state: FSM states at which this handler is allowed to run
    """

    def _callback_query(func: Callable):
        @wraps(func)
        async def inner(self: BaseModule, client, update):
            await _launch_handler(func, self, client, update)
        
        inner.bot_callback_filter = filters
        
        if fsm_state is not None:
            inner.bot_fsm_states = fsm_state if type(fsm_state) == list else [fsm_state]
        
        return inner

    return _callback_query


def message(filters: Optional[Filter] = None, fsm_state: Optional[Union[State, list[State]]] = None):
    """
    Decorator for registering all messages handler.
    If FSM is present and the handler func has 4 args, then FSM for current user session is passed as a fourth parameter.
    :param filters: Final combined filter for validation. See https://docs.pyrogram.org/topics/use-filters. Highly recommended to set this!
    :param fsm_state: FSM states at which this handler is allowed to run
    """

    def _message(func: Callable):
        @wraps(func)
        async def inner(self: BaseModule, client, update):
            await _launch_handler(func, self, client, update)
        
        inner.bot_msg_filter = filters
        
        if fsm_state is not None:
            inner.bot_fsm_states = fsm_state if type(fsm_state) == list else [fsm_state]
        
        return inner

    return _message


async def _launch_handler(func: Callable, self: BaseModule, client, update):
    params = inspect.signature(func).parameters
    if len(params) == 2:
        # FSM is not used, client obj is not used
        await func(self, update)
    elif self.state_machine is None and len(params) >= 3:
        # FSM is not used, client obj used
        await func(self, client, update)
    elif self.state_machine is not None and len(params) == 3:
        # FSM is used, client obj isn't
        await func(self, update, self.get_sm(update))
    elif self.state_machine is not None and len(params) >= 4:
        await func(self, client, update, self.get_sm(update))


def allowed_for(roles: Union[list[str], str]):
    """
    Decorator for built-in permission system. Allows certain roles or users to use this command.
    May be overwritten by user
    """

    def wrapper(func: Callable):
        func.bot_allowed_for = roles if type(roles) == list else [roles]
        return func

    return wrapper
