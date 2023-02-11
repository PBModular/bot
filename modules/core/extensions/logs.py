from base.mod_ext import ModuleExtension
from base.module import command

from pyrogram.types import Message


class LogsExtension(ModuleExtension):
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
