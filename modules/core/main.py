from base.module import BaseModule, ModuleInfo, Permissions
from base.loader import ModuleLoader
from aiogram.types import Message, FSInputFile
from urllib.parse import urlparse


class CoreModule(BaseModule):
    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(name="Core", author="Developers", version="0.0.1")

    # Use raw loader object. Very dangerous permission!
    @property
    def module_permissions(self) -> list[Permissions]:
        return [Permissions.use_loader]

    async def help_cmd(self, message: Message):
        if len(message.text.split()) > 1:
            self.loader: ModuleLoader
            name = " ".join(message.text.split()[1:])
            data = self.loader.get_module_help(name.lower())
            if data is None:
                await message.answer(self.S["help"]["module_not_found"].format(name))
            else:
                await message.answer(f"{self.S['help']['module_found'].format(name)}\n\n{data}")

        else:
            text = self.S["help"]["header"]
            for module in self.loaded_modules.values():
                text += f"<b>{module.name}</b> [{module.version}] - {module.author} \n"

            text += "\n"
            text += self.S["help"]["footer"]
            await message.answer(text)

    async def mod_install_cmd(self, message: Message):
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
            await msg.edit_text(self.S["install"]["down_err"].format(name, stdout.decode('utf-8')))
            return

        await msg.edit_text(self.S["install"]["down_ok"].format(name))

        # Load module
        result = self.loader.load_module(name)
        if result is None:
            await msg.edit_text(self.S["install"]["load_err"].format(name))
            return

        await msg.edit_text(self.S["install"]["end"].format(result))

    async def mod_uninstall_cmd(self, message: Message):
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

    async def logs_cmd(self, message: Message):
        logs = ""
        with open("bot.log") as file:
            for line in (file.readlines()[-10:]):
                logs += line
        await message.answer(f"<code>{logs}</code>")

    async def log_file_cmd(self, message: Message):
        await message.answer_document(FSInputFile("bot.log"), caption=self.S["log_file"]["answer_caption_file"])

    async def clear_log_cmd(self, message: Message):
        with open("bot.log", 'w'):
            pass

        await message.answer(f"<code>{self.S['log_file']['answer_log_cleared']}</code>")
        self.logger.info("Log file cleared")
