from base.module import BaseModule
from base.module import command
from base.loader import ModuleLoader
from base.mod_ext import ModuleExtension

from pyrogram.types import Message
from pyrogram import Client, filters
from typing import Type
import time

# Extensions
from .extensions.mod_manage import ModManageExtension
from .extensions.logs import LogsExtension
from .extensions.permissions import PermissionsExtension


class CoreModule(BaseModule):
    @property
    def module_extensions(self) -> list[Type[ModuleExtension]]:
        return [ModManageExtension, LogsExtension, PermissionsExtension]

    @command("help")
    async def help_cmd(self, _, message: Message):
        """Displays help page"""
        text = self.S["help"]["header"]
        for module in self.loaded_modules.values():
            text += f"<b>{module.name}</b> [{module.version}] - {module.author} \n"

        text += "\n"
        text += self.S["help"]["footer"]
        await message.reply(text)
    
    @command(["mhelp", "mod_help"])
    async def mod_help_cmd(self, message: Message):
        if len(message.text.split()) > 1:
            self.loader: ModuleLoader
            name = " ".join(message.text.split()[1:])
            data = self.loader.get_module_help(self.loader.get_int_name(name))
            if data is None:
                await message.reply(self.S["mod_help"]["module_not_found"].format(name))
            else:
                await message.reply(
                    f"{self.S['mod_help']['module_found'].format(name)}\n\n{data}"
                )

        else:
            await message.reply(self.S["mod_help"]["args_err"])

    @command("ping")
    async def ping_cmd(self, _: Client, message: Message):
        """Execute a ping to get the processing time"""
        start_time = time.perf_counter()
        response_message = await message.reply("pong!")
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        formatted_time = f"{elapsed_time * 1000:.2f} ms"
        response_text = self.S["ping"]["response"].format(time=formatted_time, locale=self.cur_lang)
        await response_message.edit(response_text)

    @command("start", filters.regex(r"/start \w+$"))
    async def start_cmd(self, bot: Client, message: Message):
        """Execute start for specific module"""
        self.loader: ModuleLoader
        modname = message.text.split()[1]

        if modname.lower() == "core":
            return

        int_name = self.loader.get_int_name(modname)
        if int_name is None:
            return

        module = self.loader.get_module(int_name)
        await module.start_cmd(bot, message)
