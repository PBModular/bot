from base.module import BaseModule, ModuleInfo, Permissions
from base.module import command, callback_query
from base.loader import ModuleLoader

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters

from urllib.parse import urlparse
import os
from typing import Callable
import shutil


class CoreModule(BaseModule):
    def __init__(self, bot: Client, loaded_info_func: Callable):
        super().__init__(bot, loaded_info_func)

        self.install_confirmations = {}

    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(name="Core", author="Developers", version="0.0.1")

    @command('help')
    async def help_cmd(self, _, message: Message):
        """Displays help page"""
        if len(message.text.split()) > 1:
            self.loader: ModuleLoader
            name = " ".join(message.text.split()[1:])
            data = self.loader.get_module_help(name.lower())
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

    @command('mod_install')
    async def mod_install_cmd(self, _, message: Message):
        """Install new module from git repo"""
        self.loader: ModuleLoader
        if len(message.text.split()) == 1:
            await message.reply(self.S["install"]["args_err"])
            return

        url = message.text.split()[1]
        name = urlparse(url).path.split('/')[-1].removesuffix('.git')

        msg = await message.reply(self.S["install"]["start"].format(name))

        # Start downloading
        code, stdout = self.loader.install_from_git(url)
        if code != 0:
            await msg.edit_text(self.S["install"]["down_err"].format(name, stdout))
            return

        # Check for permissions
        perms = self.loader.get_module_perms(name)
        text = self.S["install"]["confirm"].format(name=name) + "\n"
        perm_list = ""
        for p in perms:
            perm_list += f"- {self.S['install']['perms'][p.value]}\n"

        if len(perms) > 0:
            text += self.S["install"]["confirm_perms"].format(perms=perm_list)
        if Permissions.use_loader in perms:
            text += self.S["install"]["confirm_warn_perms"]

        self.install_confirmations[msg.id] = [msg, name]

        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(self.S["yes_btn"], callback_data=f"install_yes"),
                InlineKeyboardButton(self.S["no_btn"], callback_data=f"install_no")
            ]]
        )
        await msg.edit_text(text, reply_markup=keyboard)

    @callback_query(filters.regex("install_yes"))
    async def install_yes(self, _, call: CallbackQuery):
        msg, name = self.install_confirmations[call.message.id]
        self.install_confirmations.pop(call.message.id)

        await call.answer()

        if os.path.exists(f"{os.getcwd()}/modules/{name}/requirements.txt"):
            # Install deps
            await msg.edit_text(self.S["install"]["down_reqs_next"].format(name))
            code, data = self.loader.install_deps(name, "modules")
            if code != 0:
                await msg.edit_text(self.S["install"]["reqs_err"].format(name, data))
                return

            # Load module
            result = self.loader.load_module(name)
            if result is None:
                await msg.edit_text(self.S["install"]["load_err"].format(name))
                return

            reqs_list = ""
            for req in data:
                reqs_list += f"- {req}\n"

            await msg.edit_text(self.S["install"]["end_reqs"].format(result, reqs_list))

        else:
            await msg.edit_text(self.S["install"]["down_end_next"].format(name))

            # Load module
            result = self.loader.load_module(name)
            if result is None:
                await msg.edit_text(self.S["install"]["load_err"].format(name))
                return

            await msg.edit_text(self.S["install"]["end"].format(result))

    @callback_query(filters.regex("install_no"))
    async def install_no(self, _, call: CallbackQuery):
        msg, name = self.install_confirmations[call.message.id]
        self.install_confirmations.pop(call.message.id)

        shutil.rmtree(f"./modules/{name}")
        await call.answer(self.S["install"]["aborted"])
        await msg.delete()

    @command('mod_uninstall')
    async def mod_uninstall_cmd(self, _, message: Message):
        """Uninstall module"""
        self.loader: ModuleLoader
        if len(message.text.split()) == 1:
            await message.reply(self.S["uninstall"]["args_err"])
            return

        name = " ".join(message.text.split()[1:])

        # Uninstall module
        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return

        result = self.loader.uninstall_module(int_name)
        await message.reply((self.S["uninstall"]["ok"] if result else self.S["uninstall"]["err"]).format(name))

    #  Logs
    @command('logs')
    async def logs_cmd(self, _, message: Message):
        """Get logs in a message"""
        logs = ""
        with open("bot.log") as file:
            for line in (file.readlines()[-10:]):
                logs += line
        await message.reply(f"<code>{logs}</code>")

    @command("log_file")
    async def log_file_cmd(self, _, message: Message):
        """Get logs as a file"""
        await message.reply_document("bot.log", caption=self.S["log_file"]["answer_caption_file"])

    @command("clear_log")
    async def clear_log_cmd(self, _, message: Message):
        """Clear logfile"""
        with open("bot.log", 'w'):
            pass

        await message.reply(f"<code>{self.S['log_file']['answer_log_cleared']}</code>")
        self.logger.info("Log file cleared")
