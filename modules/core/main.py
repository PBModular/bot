from base.module import BaseModule, ModuleInfo
from aiogram.types import Message


class CoreModule(BaseModule):
    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(name="Core", author="Developers", version="0.0.1")

    async def help_cmd(self, message: Message):
        text = self.S["help"]["header"]
        for module in self.loaded_modules:
            text += f"<b>{module.name}</b> [{module.version}] - {module.author}"

        text += "\n"
        text += self.S["help"]["footer"]
        await message.answer(text)
