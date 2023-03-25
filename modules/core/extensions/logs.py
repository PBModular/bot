from base.mod_ext import ModuleExtension
from base.module import command, allowed_for

from pyrogram.types import Message


class LogsExtension(ModuleExtension):
    @allowed_for("owner")
    @command("logs")
    async def logs_cmd(self, _, message: Message):
        """Get logs in a message"""
        logs = ""
        with open("bot.log") as file:
            for line in file.readlines()[-10:]:
                logs += line
        await message.reply(f"<code>{logs}</code>")

    @allowed_for("owner")
    @command("log_file")
    async def log_file_cmd(self, _, message: Message):
        """Get logs as a file"""
        await message.reply_document(
            "bot.log", caption=self.S["log_file"]["answer_caption_file"]
        )

    @allowed_for("owner")
    @command("clear_log")
    async def clear_log_cmd(self, _, message: Message):
        """Clear logfile"""
        with open("bot.log", "w"):
            pass

        await message.reply(f"<code>{self.S['log_file']['answer_log_cleared']}</code>")
        self.logger.info("Log file cleared")
