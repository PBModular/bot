from base.module import BaseModule, ModuleInfo, Permissions
from base.loader import ModuleLoader
from aiogram.types import Message


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
            for module in self.loaded_modules:
                text += f"<b>{module.name}</b> [{module.version}] - {module.author} \n"

            text += "\n"
            text += self.S["help"]["footer"]
            await message.answer(text)
