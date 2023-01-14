from base.module import BaseModule, ModuleInfo
from aiogram.types import Message


class CoreModule(BaseModule):
    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(
            name="Core",
            author="Developers",
            version="0.0.1"
        )

    async def help_cmd(self, message: Message):
        await message.answer("Hello! It's testing test!")
