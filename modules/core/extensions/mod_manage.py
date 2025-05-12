from base.mod_ext import ModuleExtension
from base.module import command, callback_query, allowed_for, Permissions, ModuleConfig
from base.loader import ModuleLoader
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters, errors
from urllib.parse import urlparse
import os
import shutil
import requirements
from asyncio import sleep
from typing import Optional, Dict, List, Tuple
import re

class ModManageExtension(ModuleExtension):
    def on_init(self):
        self.confirmations: Dict[str, Dict[int, Tuple[Message, str, ModuleConfig]]] = {
            'install': {},
            'update': {}
        }
        self.last_page: Dict[int, int] = {}

    def _generate_paginated_buttons(self, items: List[Tuple[str, ModuleConfig]],
                                    page: int, items_per_page: int = 5) -> InlineKeyboardMarkup:
        start, end = page * items_per_page, (page + 1) * items_per_page
        paginated_items = items[start:end]
        total_pages = (len(items) + items_per_page - 1) // items_per_page

        buttons = [
            [InlineKeyboardButton(info.name, callback_data=f"module_{name}_{page}")]
            for name, info in paginated_items
        ]

        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton(self.S["modules"]["prev_btn"], callback_data=f"modules_page_{page-1}"))
        if total_pages > 1:
            nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="dummy"))
        if end < len(items):
            nav_row.append(InlineKeyboardButton(self.S["modules"]["next_btn"], callback_data=f"modules_page_{page+1}"))

        if nav_row:
            buttons.append(nav_row)
        
        return InlineKeyboardMarkup(buttons)

    @allowed_for("owner")
    @command("modules")
    async def modules_cmd(self, _, message: Message):
        """Display a list of all modules with management options."""
        modules_info = sorted(self.loader.get_all_modules_info().items(), 
                            key=lambda x: x[1].name.lower())
        keyboard = self._generate_paginated_buttons(modules_info, 0)
        await message.reply(self.S["modules"]["list"], reply_markup=keyboard)

    async def _update_module_page(self, call: CallbackQuery, module_name: str) -> None:
        """Update module page with error handling."""
        self.loader: ModuleLoader
        try:
            info = self.loader.get_module_info(module_name)
            if not info:
                await call.answer(self.S["module_page"]["invalid_module"])
                return

            is_core = module_name == "core"
            auto_load = getattr(info, "auto_load", True)
            is_loaded = bool(self.loader.get_module(module_name))
            git_repo = os.path.join(os.getcwd(), "modules", module_name, ".git") if not is_core else None
            update_available = self.loader.mod_manager.check_for_updates(module_name, "modules") if git_repo and os.path.exists(git_repo) else None
            has_backups = len(self.loader.mod_manager.list_backups(module_name)) > 0

            # Build module info text
            text_parts = [
                f"{self.S['module_page']['name'].format(name=info.name)}\n" if info.name else "",
                f"{self.S['module_page']['author'].format(author=info.author)}\n" if info.author else "",
                f"{self.S['module_page']['version'].format(version=info.version)}\n" if info.version else "",
                f"{self.S['module_page']['src_url'].format(url=info.src_url)}\n" if info.src_url else "",
                f"{self.S['module_page']['auto_load'].format(status=self.S['module_page']['enabled'] if auto_load else self.S['module_page']['disabled'])}" if not is_core else "",
                f"\n{self.S['module_page']['description'].format(description=info.description)}" if info.description else "",
                f"\n\n{self.S['module_page']['updates_found'] if update_available else self.S['module_page']['no_updates_found']}"
            ]
            text = "".join(text_parts).strip()

            # Build buttons
            buttons = [
                [
                    InlineKeyboardButton(
                        self.S["module_page"][f"{'un' if is_loaded else ''}load_btn"],
                        callback_data=f"{'unload' if is_loaded else 'load'}_module_{module_name}"
                    ),
                    InlineKeyboardButton(self.S["module_page"]["reload_btn"], callback_data=f"reload_module_{module_name}")
                ],
                [InlineKeyboardButton(self.S["module_page"]["update_btn"], callback_data=f"update_module_{module_name}") if update_available else None,
                 InlineKeyboardButton(self.S["module_page"]["delete_btn"], callback_data=f"delete_module_{module_name}") if not is_core else None],
                [InlineKeyboardButton(self.S["module_page"][f"{'disable' if auto_load else 'enable'}_auto_load_btn"], callback_data=f"toggle_auto_load_{module_name}") if not is_core else None],
                [InlineKeyboardButton(self.S["backup"]["view_backups_btn"], callback_data=f"view_backups_{module_name}") if has_backups else None],
                [InlineKeyboardButton(self.S["module_page"]["refresh_page_btn"], callback_data=f"refresh_module_page_{module_name}")],
                [InlineKeyboardButton(self.S["module_page"]["back_btn"], callback_data="back_to_modules")]
            ]
            buttons = [list(filter(None, row)) for row in buttons if any(row)]

            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)
        except errors.MessageNotModified:
            await call.answer(self.S["module_page"]["no_changes"])
        except Exception as e:
            await call.message.edit_text(self.S["module_page"]["refresh_page_err"].format(module_name=module_name))
            self.logger.error(f"Failed to refresh {module_name} page! \n{e}")

    @allowed_for("owner")
    @callback_query(filters.regex(r"^back_to_modules$"))
    async def back_to_modules(self, _, call: CallbackQuery):
        """Handle back to modules list button."""
        page = self.last_page.get(call.message.id, 0)
        modules_info = sorted(self.loader.get_all_modules_info().items(), 
                            key=lambda x: x[1].name.lower())
        keyboard = self._generate_paginated_buttons(modules_info, page)
        await call.message.edit_text(self.S["modules"]["list"], reply_markup=keyboard)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^refresh_module_page_(.*)$"))
    async def refresh_module_page(self, _, call: CallbackQuery):
        """Handle refresh module page button."""
        module_name = call.data.split("_")[3]
        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^(modules_page|module)_(\d+|.*_\d+)$"))
    async def handle_pagination(self, _, call: CallbackQuery):
        parts = call.data.split("_")
        if parts[0] == "modules" and parts[1] == "page":
            page = int(parts[2])
            modules_info = sorted(self.loader.get_all_modules_info().items(), 
                                key=lambda x: x[1].name.lower())
            keyboard = self._generate_paginated_buttons(modules_info, page)
            await call.message.edit_text(self.S["modules"]["list"], reply_markup=keyboard)
        elif parts[0] == "module":
            module_name, page = parts[1], int(parts[2])
            self.last_page[call.message.id] = page
            await self._update_module_page(call, module_name)
        else:
            await call.answer("Invalid callback data")

    @allowed_for("owner")
    @callback_query(filters.regex(r"^(reload|load|unload|delete|update)_module_(.*)$"))
    async def handle_module_action(self, _, call: CallbackQuery):
        """Handle module management actions."""
        action, module_name = call.data.split("_")[0], call.data.split("_")[2]
        
        actions = {
            "reload": lambda: self._reload_module(call, module_name),
            "load": lambda: self._load_module(call, module_name),
            "unload": lambda: self._unload_module(call, module_name),
            "delete": lambda: self.mod_uninstall(call.message, module_name),
            "update": lambda: self.mod_update(call.message, module_name)
        }
        
        await actions[action]()
        if action != "delete":  # Delete already handles its own response
            await self._update_module_page(call, module_name)

    async def _reload_module(self, call: CallbackQuery, module_name: str):
        if await self.mod_unload(call.message, module_name, silent=True, edit=False) and \
           await self.mod_load(call.message, module_name, silent=True, edit=False):
            await call.answer(self.S["module_page"]["reload_ok"].format(module_name=module_name), show_alert=True)

    async def _load_module(self, call: CallbackQuery, module_name: str):
        await self.mod_load(call.message, module_name)

    async def _unload_module(self, call: CallbackQuery, module_name: str):
        await self.mod_unload(call.message, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^toggle_auto_load_(.*)$"))
    async def toggle_auto_load(self, _, call: CallbackQuery):
        """Toggle auto_load setting for a module."""
        module_name = call.data.split("_")[3]
        info = self.loader.get_module_info(module_name)
        if not info:
            await call.answer(self.S["module_page"]["invalid_module"])
            return

        current_status = getattr(info, "auto_load", True)
        new_status = not current_status
        
        if self.loader.mod_manager.set_module_auto_load(module_name, new_status):
            info.auto_load = new_status
            status_text = self.S["module_page"]["enabled"] if new_status else self.S["module_page"]["disabled"]
            await call.answer(self.S["module_page"]["auto_load_toggled"].format(status=status_text), show_alert=True)
            await self._update_module_page(call, module_name)
        else:
            await call.answer(self.S["module_page"]["auto_load_toggle_error"], show_alert=True)

    async def _generate_backup_buttons(self, module_name: str, backups: List[str], page: int) -> InlineKeyboardMarkup:
        """Generate buttons for backup management."""
        buttons = [
            [InlineKeyboardButton(
                f"{self.S['backup']['restore_btn']} {os.path.basename(backup)}",
                callback_data=f"restore_specific_{module_name}_{i}"
            )] for i, backup in enumerate(backups[:5])
        ]
        buttons.append([
            InlineKeyboardButton(self.S["backup"]["cleanup_btn"], callback_data=f"module_backup_cleanup_{module_name}"),
            InlineKeyboardButton(self.S["backup"]["restore_latest_btn"], callback_data=f"restore_specific_{module_name}_0")
        ])
        buttons.append([InlineKeyboardButton(
            self.S["backup"]["back_btn"],
            callback_data=f"module_{module_name}_{self.last_page.get(page, 0)}"
        )])
        return InlineKeyboardMarkup(buttons)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^view_backups_(.+)$"))
    async def view_backups(self, _, call: CallbackQuery):
        """Display available backups for a module."""
        module_name = call.data.split("_")[2]
        backups = self.loader.mod_manager.list_backups(module_name)
        
        if not backups:
            await call.message.reply(self.S["backup"]["no_backups_module"].format(name=module_name))
            return

        text = self.S["backup"]["list_module"].format(name=module_name) + "\n\n" + \
               "\n".join(f"- {os.path.basename(backup)}" for backup in backups)
        keyboard = await self._generate_backup_buttons(module_name, backups, call.message.id)
        
        await call.message.edit_text(text, reply_markup=keyboard)

    async def _restore_backup(self, call: CallbackQuery, module_name: str, backup_path: str) -> bool:
        """Common logic for restoring backups."""
        if self.loader.get_module(module_name):
            await self.loader.unload_module(module_name)
        
        success, skipped_files = self.loader.mod_manager.restore_from_backup(module_name, "modules", backup_path)
        
        if success:
            if skipped_files:
                # Log all skipped files
                for file in skipped_files:
                    self.logger.warning(f"Skipped file during restoration: {file}")
                
                # Message with first 5 skipped files
                if len(skipped_files) > 5:
                    message = "Skipped files during restoration:\n" + "\n".join(skipped_files[:5]) + "\n...and more (check logs)"
                else:
                    message = "Skipped files during restoration:\n" + "\n".join(skipped_files)
                await call.message.reply(message)
            
            result = self.loader.load_module(module_name)
            status_key = "restore_success" if result else "restore_load_err"
            await call.message.reply(self.S["backup"][status_key].format(
                name=module_name,
                backup=os.path.basename(backup_path)
            ))
        else:
            await call.message.reply(self.S["backup"]["restore_failed"].format(name=module_name))
        
        return success

    @allowed_for("owner")
    @callback_query(filters.regex(r"^restore_(specific_)?(.+?)(?:_(\d+))?$"))
    async def restore_handler(self, _, call: CallbackQuery):
        """Handle both specific and latest backup restoration."""
        match = re.match(r"^restore_(specific_)?(.+?)(?:_(\d+))?$", call.data)
        if not match:
            await call.answer(self.S["error"])
            return

        is_specific, module_name, index = match.groups()
        backups = self.loader.mod_manager.list_backups(module_name)
        
        if not backups:
            await call.message.reply(self.S["backup"]["no_backups_module"].format(name=module_name))
            return
            
        if is_specific:
            index = int(index or 0)
            if index >= len(backups):
                await call.message.reply(self.S["backup"]["invalid_backup"])
                return
            backup_path = backups[index]
            confirm_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(self.S["yes_btn"], callback_data=f"confirm_restore_{module_name}_{index}"),
                InlineKeyboardButton(self.S["no_btn"], callback_data=f"module_{module_name}_{self.last_page.get(call.message.id, 0)}")]
            ])
            # Send a new message instead of editing the existing one
            confirmation_msg = await call.message.reply(
                self.S["backup"]["confirm_restore"].format(name=module_name, backup=os.path.basename(backup_path)),
                reply_markup=confirm_keyboard
            )
            # self.confirmation_messages[confirmation_msg.id] = (module_name, index)
        else:
            await self._restore_backup(call, module_name, backups[0])

    @allowed_for("owner")
    @callback_query(filters.regex(r"^confirm_restore_(.+)_(\d+)$"))
    async def confirm_restore(self, _, call: CallbackQuery):
        """Confirm and execute specific backup restoration."""
        match = re.match(r"^confirm_restore_(.+)_(\d+)$", call.data)
        if not match:
            await call.answer(self.S["error"])
            return

        module_name, index = match.groups()
        backups = self.loader.mod_manager.list_backups(module_name)
        if int(index) >= len(backups):
            await call.message.reply(self.S["backup"]["invalid_backup"])
            return

        await self._restore_backup(call, module_name, backups[int(index)])

    @allowed_for("owner")
    @callback_query(filters.regex(r"^(confirm|cancel)_update_restore_(.*)$"))
    async def handle_update_restore(self, _, call: CallbackQuery):
        """Handle update failure restoration decisions."""
        action, module_name = call.data.split("_")[0], call.data.split("_")[3]
        msg = await call.message.edit_text(self.S["backup"]["restoring"].format(name=module_name))
        
        if action == "confirm":
            success = self.loader.mod_manager.revert_update(module_name, "modules")
            if success:
                self.loader.load_module(module_name)
            await msg.edit_text(self.S["backup"]["restore_success" if success else "restore_failed"].format(name=module_name))
        else:
            await msg.edit_text(self.S["backup"]["restore_canceled"].format(name=module_name))

    @allowed_for("owner")
    @callback_query(filters.regex(r"^module_backup_cleanup_(.+)$"))
    async def backup_cleanup_menu(self, _, call: CallbackQuery):
        """Display backup cleanup options."""
        module_name = call.data.split("_")[3]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(self.S["backup"]["all_except_latest"], callback_data=f"do_cleanup_{module_name}_all"),
             InlineKeyboardButton(self.S["backup"]["back_btn"], callback_data=f"module_{module_name}_{self.last_page.get(call.message.id, 0)}")]
        ])
        await call.message.edit_text(
            self.S["backup"]["cleanup_select_count"].format(name=module_name),
            reply_markup=keyboard
        )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^do_cleanup_(.+)_(all|\d+)$"))
    async def execute_cleanup(self, _, call: CallbackQuery):
        """Execute backup cleanup."""
        match = re.match(r"^do_cleanup_(.+)_(all|\d+)$", call.data)
        if not match:
            await call.answer(self.S["error"])
            return
            
        module_name, keep_param = match.groups()
        keep_count = 1 if keep_param == "all" else int(keep_param)
        
        deleted = self.loader.mod_manager.cleanup_old_backups(module_name, keep_count)
        await call.message.edit_text(
            self.S["backup"]["cleanup_complete"].format(name=module_name, count=deleted, keep=keep_count)
        )
        await sleep(2)
        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @command("mod_install")
    async def mod_install_cmd(self, _, message: Message):
        """Install a new module from a Git repository URL."""
        if len(message.text.split()) != 2:
            await message.reply(self.S["install"]["args_err"])
            return

        url = message.text.split()[1]

        parsed_path = urlparse(url).path
        if not parsed_path:
            await message.reply(self.S["install"]["invalid_url"])
            return
        name = parsed_path.split("/")[-1].removesuffix(".git")
        if not name:
            await message.reply(self.S["install"]["invalid_url_name"])
            return

        msg = await message.reply(self.S["install"]["start"].format(name=name))
        module_dir = os.path.join(os.getcwd(), "modules", name)

        os.makedirs(os.path.join(os.getcwd(), "modules"), exist_ok=True)

        # Clean up potentially leftover failed attempts
        if os.path.exists(module_dir):
            try:
                shutil.rmtree(module_dir)
            except Exception as e:
                await msg.edit_text(self.S["install"]["cleanup_err"].format(name=name, error=e))
                self.logger.error(f"Failed to clean up existing directory {module_dir}: {e}")
                return

        # Download the module
        code, stdout = self.loader.mod_manager.install_from_git(url)
        if code != 0:
            await msg.edit_text(self.S["install"]["down_err"].format(name=name, out=stdout))
            return

        config_path = os.path.join(module_dir, "config.yaml")
        info: Optional[ModuleConfig] = None
        permissions = []

        try:
            if os.path.exists(config_path):
                config_file = ModuleConfig.from_yaml_file(config_path)
                info = config_file.info
                permissions = config_file.permissions
            else:
                if os.path.exists(module_dir):
                    shutil.rmtree(module_dir)
                await msg.edit_text(self.S["install"]["no_config_yaml_err"].format(name=name))
                return

        except Exception as e:
            if os.path.exists(module_dir):
                shutil.rmtree(module_dir)
            await msg.edit_text(self.S["install"]["config_parse_err"].format(name=name, error=e))
            self.logger.error(f"Failed to parse config.yaml for {name}: {e}", exc_info=True)
            return

        # Prepare confirmation message
        text = self.S["install"]["confirm"].format(
            name=info.name, author=info.author, version=info.version
        )
        if permissions:
            perm_list = "\n".join(f"- {self.S['install']['perms'].get(p.value, p.value)}" for p in permissions)
            text += self.S["install"]["confirm_perms"].format(perms=perm_list)
            if Permissions.use_loader in permissions:
                text += self.S["install"]["confirm_warn_perms"]

        # Send confirmation with buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(self.S["yes_btn"], callback_data="install_yes"),
                InlineKeyboardButton(self.S["no_btn"], callback_data="install_no")
            ]
        ])
        await msg.edit_text(text, reply_markup=keyboard)
        self.confirmations["install"][msg.id] = (msg, name, info)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^install_(yes|no)$"))
    async def handle_install(self, _, call: CallbackQuery):
        """Handle module installation confirmation."""
        action = call.data.split("_")[1]
        confirmation_data = self.confirmations["install"].pop(call.message.id, None)

        if confirmation_data is None:
            await call.answer(self.S["install"]["confirmation_expired"])
            return

        msg, name, info_obj = confirmation_data
        module_dir = os.path.join(os.getcwd(), "modules", name)
        reqs_path = os.path.join(module_dir, "requirements.txt")

        if action == "no":
            if os.path.exists(module_dir):
                try:
                    shutil.rmtree(module_dir)
                except Exception as e:
                    self.logger.error(f"Error removing directory during install cancel {module_dir}: {e}")
            await call.answer(self.S["install"]["aborted"])
            await msg.delete()
            return

        await msg.edit_text(self.S["install"]["processing"].format(name=info_obj.name))
        try:
            if os.path.exists(reqs_path):
                await msg.edit_text(self.S["install"]["down_reqs_next"].format(name=info_obj.name))
                code, data = self.loader.mod_manager.install_deps(name, "modules")
                if code != 0:
                    await msg.edit_text(self.S["install"]["reqs_err"].format(name=info_obj.name, out=data))
                    return

                await msg.edit_text(self.S["install"]["loading"].format(name=info_obj.name))
                result = self.loader.load_module(name)
                if result is None:
                    await msg.edit_text(self.S["install"]["load_err"].format(name=info_obj.name))
                    return

                req_list_str = "\n".join(f"- {req}" for req in data) if isinstance(data, list) else str(data)
                await msg.edit_text(self.S["install"]["end_reqs"].format(name=result, reqs=req_list_str))
            else:
                await msg.edit_text(self.S["install"]["down_end_next"].format(name=info_obj.name))
                await msg.edit_text(self.S["install"]["loading"].format(name=info_obj.name))
                result = self.loader.load_module(name)
                if result is None:
                    await msg.edit_text(self.S["install"]["load_err"].format(name=info_obj.name))
                    return

                await msg.edit_text(self.S["install"]["end"].format(name=result))
        except Exception as e:
            await msg.edit_text(self.S["install"]["unexpected_err"].format(name=info_obj.name, error=e))
            self.logger.error(f"Unexpected error during final install steps for {name}: {e}", exc_info=True)

    async def mod_uninstall(self, message: Message, name: str) -> None:
        """Uninstall a module."""
        try:
            int_name = self.loader.get_int_name(name)
        except:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return

        if int_name.lower() == "core":
            await message.reply(self.S["uninstall"]["uninstall_core"])
            return

        if self.loader.get_module(int_name):
            try:
                await self.loader.unload_module(int_name)
                await sleep(0.5)
            except Exception as e:
                await message.reply(self.S["uninstall"]["unload_err_before_delete"].format(name=name))
                return

        current_deps = self.loader.get_modules_deps()
        result = self.loader.mod_manager.uninstall_module(int_name, current_deps)

        if result:
            if int_name in self.loader.get_all_modules_info():
                del self.loader.get_all_modules_info()[int_name]
            await message.reply(self.S["uninstall"]["ok"].format(name))
        else:
            await message.reply(self.S["uninstall"]["err"].format(name))

    async def mod_update(self, message: Message, name: str) -> None:
        """Update module to upstream version."""
        try:
            int_name = self.loader.get_int_name(name)
            if not int_name:
                raise ValueError("Module not found by loader")
            current_info = self.loader.get_module_info(int_name)
            if not current_info:
                raise ValueError("Module info not found by loader")
        except Exception as e:
            await message.reply(self.S["uninstall"]["not_found"].format(name=name))
            self.logger.warning(f"Attempted to update non-existent/unloaded module {name}: {e}")
            return

        msg = await message.reply(self.S["update"]["checking"].format(name=current_info.name))
        update_available = self.loader.mod_manager.check_for_updates(int_name, "modules")

        if update_available is None:
            await msg.edit_text(self.S["update"]["check_err"].format(name=current_info.name))
            return
        if not update_available:
            await msg.edit_text(self.S["update"]["no_updates_found"].format(name=current_info.name))
            return

        old_ver = current_info.version
        module_dir = os.path.join(os.getcwd(), "modules", int_name)
        reqs_path = os.path.join(module_dir, "requirements.txt")
        old_reqs = None
        if os.path.exists(reqs_path):
            try:
                with open(reqs_path, "r", encoding="utf-8") as f:
                    old_reqs = list(requirements.parse(f))
            except Exception as e:
                self.logger.warning(f"Could not parse old requirements for {int_name}: {e}")

        # Prepare for update
        try:
            if self.loader.get_module(int_name):
                await self.loader.unload_module(int_name)
                await sleep(0.5)
        except Exception as e:
            await msg.edit_text(self.S["update"]["prepare_err"].format(name=current_info.name, error=e))
            self.logger.error(f"Error unloading module {int_name} before update: {e}", exc_info=True)
            if not self.loader.get_module(int_name):
                self.loader.load_module(int_name)
            return

        # Git Pull
        await msg.edit_text(self.S["update"]["pulling"].format(name=current_info.name))
        code, stdout, backup_path = self.loader.mod_manager.update_from_git(int_name, "modules") 

        if code != 0:
            await msg.edit_text(self.S["update"]["err"].format(name=current_info.name, out=stdout))
            if backup_path:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.S["backup"]["restore_btn"], callback_data=f"confirm_restore_{int_name}_{backup_path}"),
                    InlineKeyboardButton(self.S["no_btn"], callback_data=f"cancel_update_restore_{int_name}")]
                ])
                await msg.edit_text(
                    msg.text + "\n" + self.S["backup"]["offer_restore"].format(name=int_name, backup=os.path.basename(backup_path)),
                    reply_markup=keyboard
                )
            else:
                await msg.reply(self.S["update"]["err_no_backup"].format(name=current_info.name))
            self.loader.load_module(int_name)
            return

        if not backup_path:
            self.logger.warning(f"Update for {int_name} proceeded but backup creation failed (path is None).")

        # Read Module Info
        await msg.edit_text(self.S["update"]["checking_info"].format(name=current_info.name))
        config_path = os.path.join(module_dir, "config.yaml")
        new_info_obj: Optional[ModuleConfig.info] = None # Correctly ModuleInfo
        new_permissions = []

        try:
            if os.path.exists(config_path):
                config_file = ModuleConfig.from_yaml_file(config_path)
                new_info_obj = config_file.info
                new_permissions = config_file.permissions
                self.logger.info(f"Loaded updated metadata for {int_name} from config.yaml")
            else:
                await msg.edit_text(self.S["update"]["config_yaml_missing_after_update"].format(name=current_info.name))
                if backup_path:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(self.S["backup"]["restore_btn"], callback_data=f"confirm_restore_{int_name}_{backup_path}"),
                        InlineKeyboardButton(self.S["no_btn"], callback_data=f"cancel_update_restore_{int_name}")]
                    ])
                    await msg.edit_text(
                        msg.text + "\n" + self.S["backup"]["offer_restore"].format(name=int_name, backup=os.path.basename(backup_path)),
                        reply_markup=keyboard
                    )
                else:
                    await msg.reply(self.S["update"]["err_no_backup"].format(name=current_info.name))
                return
        except Exception as e:
            await msg.edit_text(self.S["update"]["config_parse_err_after_update"].format(name=current_info.name, error=e))
            self.logger.error(f"Failed to parse updated config.yaml for {int_name}: {e}", exc_info=True)
            if backup_path:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.S["backup"]["restore_btn"], callback_data=f"confirm_restore_{int_name}_{backup_path}"),
                    InlineKeyboardButton(self.S["no_btn"], callback_data=f"cancel_update_restore_{int_name}")]
                ])
                await msg.edit_text(
                    msg.text + "\n" + self.S["backup"]["offer_restore"].format(name=int_name, backup=os.path.basename(backup_path)),
                    reply_markup=keyboard
                )
            else:
                await msg.reply(self.S["update"]["err_no_backup"].format(name=current_info.name))
            return

        # Prepare confirmation text
        text = self.S["update"]["confirm"].format(
            name=new_info_obj.name,
            author=new_info_obj.author,
            old_ver=old_ver,
            new_ver=new_info_obj.version
        ) + "\n"
        if new_permissions:
            perm_list = "\n".join(f"- {self.S['install']['perms'].get(p.value, p.value)}" for p in new_permissions)
            text += self.S["install"]["confirm_perms"].format(perms=perm_list)
            if Permissions.use_loader in new_permissions:
                text += self.S["install"]["confirm_warn_perms"]
        if backup_path:
            text += "\n" + self.S["backup"]["backup_created"].format(path=os.path.basename(backup_path))
        else:
            text += "\n" + self.S["backup"]["backup_failed_during_update"]

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(self.S["yes_btn"], callback_data="update_yes"),
             InlineKeyboardButton(self.S["no_btn"], callback_data="update_no")]
        ])
        await msg.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
        self.confirmations["update"][msg.id] = (msg, int_name, old_ver, old_reqs, backup_path, new_info_obj)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^update_(yes|no)$"))
    async def handle_update(self, _, call: CallbackQuery):
        """Handle module update confirmation."""
        action = call.data.split("_")[1]
        confirmation_data = self.confirmations["update"].pop(call.message.id, None)

        if confirmation_data is None:
            await call.answer(self.S["update"]["confirmation_expired"])
            return

        msg, int_name, old_ver, old_reqs, backup_path, new_info_obj = confirmation_data
        display_name = new_info_obj.name

        try_again_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(self.S["backup"]["restore_btn"] if backup_path else self.S["abort_btn"],
                                   callback_data=f"confirm_restore_{int_name}_{backup_path}" if backup_path else f"cancel_update_restore_{int_name}"),
                InlineKeyboardButton(self.S["abort_btn"] if backup_path else self.S["ok_btn"],
                                   callback_data=f"cancel_update_restore_{int_name}")
            ]
        ])

        if action == "no":
            await call.answer(self.S["update"]["abort"])
            if backup_path:
                await msg.edit_text(self.S["backup"]["restoring"].format(name=display_name))
                success, skipped_files = self.loader.mod_manager.restore_from_backup(int_name, "modules", backup_path)
                if success:
                    if skipped_files:
                        await msg.reply(self.S["backup"]["restore_skipped_files"].format(count=len(skipped_files)))
                        self.logger.warning(f"Skipped files during update revert restore: {skipped_files}")
                    result = self.loader.load_module(int_name)
                    if result is None:
                        await msg.edit_text(self.S["backup"]["restore_load_err"].format(name=display_name))
                    else:
                        await msg.edit_text(self.S["backup"]["restore_success"].format(name=display_name, backup=os.path.basename(backup_path)))
                else:
                    await msg.edit_text(self.S["backup"]["restore_failed"].format(name=display_name))
            else:
                await msg.edit_text(self.S["update"]["abort_no_backup"].format(name=display_name))
                self.loader.load_module(int_name)
            return

        await msg.edit_text(self.S["update"]["processing"].format(name=display_name))
        try:
            module_dir = os.path.join(os.getcwd(), "modules", int_name)
            reqs_path = os.path.join(module_dir, "requirements.txt")
            final_text = ""

            if os.path.exists(reqs_path):
                await msg.edit_text(self.S["install"]["down_reqs_next"].format(name=display_name))
                code, data = self.loader.mod_manager.install_deps(int_name, "modules")
                if code != 0:
                    await msg.edit_text(self.S["install"]["reqs_err"].format(name=display_name, out=data), reply_markup=try_again_keyboard)
                    self.confirmations["update"][call.message.id] = (msg, int_name, old_ver, old_reqs, backup_path, new_info_obj)
                    return

                await msg.edit_text(self.S["update"]["loading"].format(name=display_name))
                result = self.loader.load_module(int_name, skip_deps=False)
                if result is None:
                    await msg.edit_text(self.S["install"]["load_err"].format(name=display_name), reply_markup=try_again_keyboard)
                    self.confirmations["update"][call.message.id] = (msg, int_name, old_ver, old_reqs, backup_path, new_info_obj)
                    return

                if isinstance(data, list):
                    new_reqs_objs = []
                    if os.path.exists(reqs_path):
                         with open(reqs_path, "r", encoding="utf-8") as f_reqs:
                            new_reqs_objs = list(requirements.parse(f_reqs))

                    del_reqs = [req.name.lower() for req in (old_reqs or []) if not any(req.name.lower() == new_req.name.lower() for new_req in new_reqs_objs)]
                    if del_reqs:
                        self.logger.info(f"Attempting to uninstall old dependencies for {int_name}: {del_reqs}")
                        current_deps = self.loader.get_modules_deps()
                        temp_deps = current_deps.copy()
                        if int_name in temp_deps: del temp_deps[int_name]
                        self.loader.mod_manager.uninstall_packages(del_reqs, temp_deps)

                # Construct final message
                req_list_str = "\n".join(f"- {req}" for req in data) if isinstance(data, list) else str(data)
                final_text = self.S["update"]["ok"].format(
                    name=result,
                    old_ver=old_ver,
                    new_ver=new_info_obj.version,
                    url=new_info_obj.src_url or ""
                ) + "\n" + \
                    self.S["update"]["reqs"] + "\n" + req_list_str
            else:
                await msg.edit_text(self.S["update"]["loading"].format(name=display_name))
                result = self.loader.load_module(int_name, skip_deps=False)
                if result is None:
                    await msg.edit_text(self.S["install"]["load_err"].format(name=display_name), reply_markup=try_again_keyboard)
                    self.confirmations["update"][call.message.id] = (msg, int_name, old_ver, old_reqs, backup_path, new_info_obj)
                    return

                if old_reqs:
                    del_reqs = [req.name.lower() for req in old_reqs]
                    if del_reqs:
                        self.logger.info(f"Attempting to uninstall old dependencies for {int_name}: {del_reqs}")
                        current_deps = self.loader.get_modules_deps()
                        temp_deps = current_deps.copy()
                        if int_name in temp_deps: del temp_deps[int_name]
                        self.loader.mod_manager.uninstall_packages(del_reqs, temp_deps)

                # Construct final message
                final_text = self.S["update"]["ok"].format(
                    name=result,
                    old_ver=old_ver,
                    new_ver=new_info_obj.version,
                    url=new_info_obj.src_url or ""
                )

            self.loader.mod_manager.clear_hash_backup(int_name)
            await msg.edit_text(final_text, disable_web_page_preview=True)

        except Exception as e:
            await msg.edit_text(self.S["update"]["unexpected_err"].format(name=display_name, error=e), reply_markup=try_again_keyboard)
            self.logger.error(f"Unexpected error during final update steps for {int_name}: {e}", exc_info=True)
            self.confirmations["update"][call.message.id] = (msg, int_name, old_ver, old_reqs, backup_path, new_info_obj)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^confirm_restore_(.+)_([^_].+)$"))
    async def confirm_restore_path(self, _, call: CallbackQuery):
        """Confirm and execute specific backup restoration using path."""
        match = re.match(r"^confirm_restore_(.+)_([^_].+)$", call.data)
        if not match:
            await call.answer(self.S["error"])
            return

        module_name, backup_path = match.groups()

        if not os.path.exists(backup_path) or not backup_path.endswith(".zip"):
            await call.message.reply(self.S["backup"]["invalid_backup_path"])
            # Maybe refresh the view? Go back? Edit message?
            await call.message.edit_text(self.S["backup"]["invalid_backup_path_edit"])
            return

        await call.message.edit_text(self.S["backup"]["restoring"].format(name=module_name))
        success, skipped = self.loader.mod_manager.restore_from_backup(module_name, "modules", backup_path)

        if success:
            if skipped:
                await call.message.reply(self.S["backup"]["restore_skipped_files"].format(count=len(skipped)))
                self.logger.warning(f"Skipped files during manual restore: {skipped}")
            result = self.loader.load_module(module_name)
            status_key = "restore_success" if result else "restore_load_err"
            await call.message.edit_text(self.S["backup"][status_key].format(
                name=module_name,
                backup=os.path.basename(backup_path)
            ))
            await self._update_module_page(call, module_name)
        else:
            await call.message.edit_text(self.S["backup"]["restore_failed"].format(name=module_name))

    @allowed_for("owner")
    @callback_query(filters.regex(r"^cancel_update_restore_(.*)$"))
    async def cancel_update_restore(self, _, call: CallbackQuery):
        """Handle cancellation of restore after update failure."""
        module_name = call.data.split("_")[-1]
        await call.message.edit_text(self.S["backup"]["restore_canceled"].format(name=module_name))
        await self._update_module_page(call, module_name)

    async def mod_load(self, message: Message, name: str, silent: bool = False, edit: bool = False) -> Optional[str]:
        """Load a module."""
        reply_func = message.edit_text if edit else message.reply
        if self.loader.get_module(name):
            if not silent:
                await reply_func(self.S["load"]["already_loaded_err"].format(name))
            return None
            
        try:
            result = self.loader.load_module(name)
            if result is None:
                await reply_func(self.S["load"]["load_err"].format(name))
                return None
            if not silent:
                await reply_func(self.S["load"]["ok"].format(result))
            return result
        except FileNotFoundError:
            await reply_func(self.S["load"]["not_found"].format(name))
        except Exception:
            await reply_func(self.S["load"]["load_err"].format(name))
        return None

    async def mod_unload(self, message: Message, name: str, silent: bool = False, edit: bool = False) -> Optional[str]:
        """Unload a module."""
        reply_func = message.edit_text if edit else message.reply
        if name.lower() == "core":
            if not silent:
                await reply_func(self.S["unload"]["unload_core"])
            return None
            
        int_name = self.loader.get_int_name(name)
        if not int_name:
            if not silent:
                await reply_func(self.S["unload"]["not_loaded_err"].format(name))
            return None
            
        await self.loader.unload_module(int_name)
        if not silent:
            await reply_func(self.S["unload"]["ok"].format(name))
        return int_name

    @callback_query(filters.regex(r"^dummy$"))
    async def dummy_callback(self, _, call: CallbackQuery):
        """Handle dummy button clicks."""
        await call.answer()