from base.mod_ext import ModuleExtension
from base.module import command, callback_query, Permissions
from base.loader import ModuleLoader

from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters
from urllib.parse import urlparse
import os
import shutil


class ModManageExtension(ModuleExtension):
    def on_init(self):
        self.install_confirmations = {}

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
