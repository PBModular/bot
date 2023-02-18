from base.module import BaseModule
from base.module import command
from base.loader import ModuleLoader
from base.mod_ext import ModuleExtension

from pyrogram.types import Message
from pyrogram import Client, filters
from typing import Type

# Extensions
from .extensions.mod_manage import ModManageExtension
from .extensions.logs import LogsExtension


class CoreModule(BaseModule):
    @property
    def module_extensions(self) -> list[Type[ModuleExtension]]:
        return [
            ModManageExtension,
            LogsExtension
        ]

    @command('help')
    async def help_cmd(self, _, message: Message):
        """Displays help page"""
        if len(message.text.split()) > 1:
            self.loader: ModuleLoader
            name = " ".join(message.text.split()[1:])
            data = self.loader.get_module_help(self.loader.get_int_name(name))
            if data is None:
                await message.reply(self.S["help"]["module_not_found"].format(name))
            else:
                await message.reply(f"{self.S['help']['module_found'].format(name)}\n\n{data}")

        else:
            text = self.S["help"]["header"]
            for module in self.loaded_modules.values():
                text += f"<b>{module.name}</b> [{module.version}] - {module.author} \n"

            text += "\n"
            text += self.S["help"]["footer"]
            await message.reply(text)

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
        module.start_cmd(bot, message)
