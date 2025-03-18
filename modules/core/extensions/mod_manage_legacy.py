from base.loader import ModuleLoader
from base.mod_ext import ModuleExtension
from base.module import command, allowed_for, Permissions, InfoFile
from pyrogram.types import Message
from urllib.parse import urlparse
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import os


class ModManageLegacyExtension(ModuleExtension):
    """Legacy command-based module management functions"""
    
    @allowed_for("owner")
    @command("mod_install")
    async def mod_install_cmd(self, _, message: Message):
        """Install new module from git repo"""
        self.loader: ModuleLoader
        if len(message.text.split()) == 1:
            await message.reply(self.S["install"]["args_err"])
            return

        url = message.text.split()[1]
        name = urlparse(url).path.split("/")[-1].removesuffix(".git")

        msg = await message.reply(self.S["install"]["start"].format(name))

        # Start downloading
        code, stdout = self.loader.install_from_git(url)
        if code != 0:
            await msg.edit_text(self.S["install"]["down_err"].format(name, stdout))
            return

        # Parse info file
        info_file = InfoFile.from_yaml_file(f"{os.getcwd()}/modules/{name}/info.yaml")
        info = info_file.info
        permissions = info_file.permissions

        text = (
            self.S["install"]["confirm"].format(
                name=name, author=info.author, version=info.version
            )
            + "\n"
        )

        # Check for permissions
        perm_list = ""
        for p in permissions:
            perm_list += f"- {self.S['install']['perms'][p.value]}\n"

        if len(permissions) > 0:
            text += self.S["install"]["confirm_perms"].format(perms=perm_list)
        if Permissions.use_loader in permissions:
            text += self.S["install"]["confirm_warn_perms"]

        self.install_confirmations[msg.id] = [msg, name]

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self.S["yes_btn"], callback_data=f"install_yes"
                    ),
                    InlineKeyboardButton(self.S["no_btn"], callback_data=f"install_no"),
                ]
            ]
        )
        await msg.edit_text(text, reply_markup=keyboard)

    @allowed_for("owner")
    @command("mod_uninstall")
    async def mod_uninstall_cmd(self, _, message: Message):
        if len(message.text.split()) == 1:
            await message.reply(self.S["uninstall"]["args_err"])
            return

        name = " ".join(message.text.split()[1:])
        await self.mod_uninstall(_, message, name)

    @allowed_for("owner")
    @command("mod_update")
    async def mod_update_cmd(self, _, message: Message):
        if len(message.text.split()) == 1:
            await message.reply(self.S["update"]["args_err"])
            return

        name = " ".join(message.text.split()[1:])
        await self.mod_update(_, message, name)

    @allowed_for("owner")
    @command("mod_backups")
    async def mod_backups_cmd(self, _, message: Message):
        """List available module backups"""
        if len(message.text.split()) == 1:
            # List all backups
            backups = self.loader.list_backups()
            if not backups:
                await message.reply(self.S["backup"]["no_backups"])
                return
                
            text = self.S["backup"]["list_all"] + "\n\n"
            # Group backups by module name
            modules = {}
            for backup in backups:
                base_name = os.path.basename(backup)
                module_name = base_name.split('_')[0]
                if module_name not in modules:
                    modules[module_name] = []
                modules[module_name].append(base_name)
                
            for module, mod_backups in modules.items():
                text += f"<b>{module}</b>:\n"
                for backup in mod_backups[:5]:  # Show only 5 most recent
                    text += f"- {backup}\n"
                if len(mod_backups) > 5:
                    text += f"  {self.S['backup']['more_backups'].format(count=len(mod_backups)-5)}\n"
                text += "\n"
            
            await message.reply(text, parse_mode="HTML")
        else:
            # List backups for specific module
            name = " ".join(message.text.split()[1:])
            int_name = self.loader.get_int_name(name)
            if int_name is None:
                await message.reply(self.S["uninstall"]["not_found"].format(name))
                return
                
            backups = self.loader.list_backups(int_name)
            if not backups:
                await message.reply(self.S["backup"]["no_backups_module"].format(name=name))
                return
                
            text = self.S["backup"]["list_module"].format(name=name) + "\n\n"
            for backup in backups:
                text += f"- {os.path.basename(backup)}\n"
                
            restore_keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(
                    self.S["backup"]["restore_latest_btn"], 
                    callback_data=f"restore_{int_name}"
                )]]
            )
            
            await message.reply(text, reply_markup=restore_keyboard, parse_mode="HTML")

    @allowed_for("owner")
    @command("mod_backup_cleanup")
    async def mod_backup_cleanup_cmd(self, _, message: Message):
        """Clean up old module backups"""
        args = message.text.split()
        keep_count = 5  # Default value
        
        if len(args) > 1:
            try:
                name = args[1]
                if len(args) > 2 and args[2].isdigit():
                    keep_count = int(args[2])
                
                int_name = self.loader.get_int_name(name)
                if int_name is None:
                    await message.reply(self.S["uninstall"]["not_found"].format(name))
                    return
                    
                deleted = self.loader.cleanup_old_backups(int_name, keep_count)
                await message.reply(
                    self.S["backup"]["cleanup_module"].format(
                        name=name, 
                        count=deleted, 
                        keep=keep_count
                    )
                )
            except ValueError:
                await message.reply(self.S["backup"]["cleanup_usage"])
        else:
            # Prompt for each module with backups
            modules = set()
            for backup in self.loader.list_backups():
                base_name = os.path.basename(backup)
                module_name = base_name.split('_')[0]
                modules.add(module_name)
                
            if not modules:
                await message.reply(self.S["backup"]["no_backups"])
                return
                
            keyboard = []
            for module in modules:
                keyboard.append([
                    InlineKeyboardButton(
                        module, 
                        callback_data=f"cleanup_{module}_{keep_count}"
                    )
                ])
                
            await message.reply(
                self.S["backup"]["cleanup_select"], 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    @allowed_for("owner")
    @command("mod_info")
    async def mod_info_cmd(self, _, message: Message):
        """Displays full info about module"""
        self.loader: ModuleLoader

        args = message.text.split()
        if len(args) != 2:
            await message.reply(self.S["info"]["args_err"], quote=True)
            return

        int_name = self.loader.get_int_name(args[-1])
        if int_name is None:
            await message.reply(self.S["info"]["not_found"], quote=True)
            return

        info = self.loader.get_module_info(int_name)
        text = self.S["info"]["header"].format(
            name=info.name, author=info.author, version=info.version
        )

        if info.src_url:
            text += self.S["info"]["src_url"].format(url=info.src_url)

        text += "\n" + self.S["info"]["description"].format(
            description=info.description
        )

        await message.reply(text, quote=True)

    @allowed_for("owner")
    @command("mod_load")
    async def mod_load_cmd(self, _, message: Message):
        """Loads module if not loaded. Accepts directory name of a module"""
        args = message.text.split()
        if len(args) != 2:
            await message.reply(self.S["load"]["args_err"])
            return
        
        await self.mod_load(message, args[1])

    @allowed_for("owner")
    @command("mod_unload")
    async def mod_unload_cmd(self, _, message: Message):
        """Unloads module if it is loaded already"""
        args = message.text.split()
        if len(args) != 2:
            await message.reply(self.S["unload"]["args_err"])
            return False
        
        await self.mod_unload(message, args[1])
    
    @allowed_for("owner")
    @command("mod_reload")
    async def mod_reload_cmd(self, message: Message):
        args = message.text.split()
        if len(args) != 2:
            await message.reply(self.S["reload"]["args_err"])
            return
                
        int_name = await self.mod_unload(message, args[1], True, False)
        if int_name is None:
            return
        
        msg = await message.reply(self.S["reload"]["loading"].format(args[1]))
        name = await self.mod_load(msg, int_name, True, True)
        if name is None:
            return
        
        await msg.edit_text(self.S["reload"]["ok"].format(name))