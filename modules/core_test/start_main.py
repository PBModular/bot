from base.module import BaseModule, ModuleInfo
from aiogram.types import Message


class StartModule(BaseModule):
    @property
    def module_info(self) -> ModuleInfo:
        return ModuleInfo(name="Start!", author="Developers", version="0.0.1")

    async def test_cmd(self, message: Message):
        await message.answer("Hello! It's testing start!")
