from base.module import BaseModule, ModuleInfo, Permissions
from base.module import command
from base.loader import ModuleLoader

from pyrogram import Client
from pyrogram.types import Message

from urllib.parse import urlparse
import os
import sys


class CoreModule(BaseModule):
    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(name="Core", author="Developers", version="0.0.1")

    # Use raw loader object. Very dangerous permission!
    @property
    def module_permissions(self) -> list[Permissions]:
        return [Permissions.use_loader]

    @command('help')
    async def help_cmd(self, bot: Client, message: Message):
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

    @command('mod_uninstall')
    async def mod_uninstall_cmd(self, _, message: Message):
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
        logs = ""
        with open("bot.log") as file:
            for line in (file.readlines()[-10:]):
                logs += line
        await message.reply(f"<code>{logs}</code>")

    @command("log_file")
    async def log_file_cmd(self, message: Message):
        await message.reply_document("bot.log", caption=self.S["log_file"]["answer_caption_file"])

    @command("clear_log")
    async def clear_log_cmd(self, message: Message):
        with open("bot.log", 'w'):
            pass

        await message.reply(f"<code>{self.S['log_file']['answer_log_cleared']}</code>")
        self.logger.info("Log file cleared")
