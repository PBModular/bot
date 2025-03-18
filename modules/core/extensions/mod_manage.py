from base.mod_ext import ModuleExtension
from base.module import command, callback_query, allowed_for, Permissions, InfoFile
from base.loader import ModuleLoader
from base.mod_manager import ModuleManager

from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram import filters, errors
import os
import shutil
import requirements
from asyncio import sleep
from typing import Optional
import re

class ModManageExtension(ModuleExtension):
    def on_init(self):
        self.install_confirmations = {}
        self.update_confirmations = {}
        self.last_page = {}

    def generate_module_buttons(self, page: int = 0, items_per_page: int = 5):
        """Creates a keyboard with a list of all modules, sorted alphabetically, with pagination."""
        self.loader: ModuleLoader
        modules_info = self.loader.get_all_modules_info()
        
        sorted_modules = sorted(modules_info.items(), key=lambda x: x[1].name.lower())
        start, end = page * items_per_page, (page + 1) * items_per_page
        paginated_modules = sorted_modules[start:end]
        total_pages = (len(modules_info) + items_per_page - 1) // items_per_page

        buttons = [
            [InlineKeyboardButton(info.name, callback_data=f"module_{module_name}_{page}")]
            for module_name, info in paginated_modules
        ]

        navigation_buttons = [
            InlineKeyboardButton(self.S["modules"]["prev_btn"], callback_data=f"modules_page_{page-1}") if page > 0 else None,
            InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="dummy") if total_pages > 1 else None,
            InlineKeyboardButton(self.S["modules"]["next_btn"], callback_data=f"modules_page_{page+1}") if end < len(modules_info) else None
        ]

        navigation_buttons = list(filter(None, navigation_buttons))

        if navigation_buttons:
            buttons.append(navigation_buttons)
        
        keyboard = InlineKeyboardMarkup(buttons)
        return keyboard

    @allowed_for("owner")
    @command("modules")
    async def modules_cmd(self, _, message: Message):
        """Display a list of all modules with options to view and manage them."""
        keyboard = self.generate_module_buttons()
        await message.reply(self.S["modules"]["list"], reply_markup=keyboard)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^modules_page_(\d+)$"))
    async def call_modules_page(self, _, call: CallbackQuery):
        """Handles a transition to another page of the module list."""
        page = int(call.data.split("_")[2])
        keyboard = self.generate_module_buttons(page=page)
        await call.message.edit_text(self.S["modules"]["list"], reply_markup=keyboard)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^module_(.*)_(\d+)$"))
    async def call_module_page(self, _, call: CallbackQuery):
        """Display the help page and management options for a specific module."""
        try:
            module_name, page = call.data.split("_")[1], int(call.data.split("_")[2])
        except ValueError:
            await call.answer(self.S["module_page"]["invalid_module"])
            return
        
        self.last_page[call.message.id] = page

        await self._update_module_page(call, module_name)

    async def _update_module_page(self, call, module_name):
        """Helper function to update module page with error handling"""
        try:
            await self.update_module_page(call, module_name)

        except errors.MessageNotModified:
            await call.answer(self.S["module_page"]["no_changes"])
        except Exception as e:
            await call.message.edit_text(self.S["module_page"]["refresh_page_err"].format(module_name=module_name))
            self.logger.error(f"Failed to refresh {module_name} page! \n{e}")

    async def update_module_page(self, call, module_name):
        """Update the module page with the latest information, and check for updates."""
        self.loader: ModuleLoader

        info = self.loader.get_module_info(module_name)
        auto_load = getattr(info, "auto_load", True)
        text = f"{self.S['module_page']['name'].format(name=info.name)}\n" if info.name else ""
        text += f"{self.S['module_page']['author'].format(author=info.author)}\n" if info.author else ""
        text += f"{self.S['module_page']['version'].format(version=info.version)}\n" if info.version else ""
        text += f"{self.S['module_page']['src_url'].format(url=info.src_url)}\n" if info.src_url else ""
        
        if module_name != "core":
            text += f"{self.S['module_page']['auto_load'].format(status=self.S['module_page']['enabled'] if auto_load else self.S['module_page']['disabled'])}"

        text += f"\n{self.S['module_page']['description'].format(description=info.description)}" if info.description else ""

        git_repo = os.path.join(os.getcwd(), "modules", module_name, ".git") if module_name != "core" else None
        update_message = self.loader.mod_manager.check_for_updates(module_name, "modules") if git_repo and os.path.exists(git_repo) else None

        if update_message:
            text += f"\n\n{self.S['module_page']['updates_found']}"
        else:
            text += f"\n\n{self.S['module_page']['no_updates_found']}"

        has_backups = len(self.loader.mod_manager.list_backups(module_name)) > 0

        buttons = [
            [
                InlineKeyboardButton(
                    self.S["module_page"][f"{'un' if self.loader.get_module(module_name) else ''}load_btn"], 
                    callback_data=f"{'unload' if self.loader.get_module(module_name) else 'load'}_module_{module_name}"
                ),
                InlineKeyboardButton(self.S["module_page"]["reload_btn"], callback_data=f"reload_module_{module_name}")
            ],
            [
                InlineKeyboardButton(
                    self.S["module_page"]["update_btn"], callback_data=f"update_module_{module_name}"
                ) if git_repo and update_message else None,
                InlineKeyboardButton(self.S["module_page"]["delete_btn"], callback_data=f"delete_module_{module_name}")
            ],
            [
                InlineKeyboardButton(
                    self.S["module_page"][f"{'disable' if auto_load else 'enable'}_auto_load_btn"], 
                    callback_data=f"toggle_auto_load_{module_name}"
                ) if module_name != "core" else None
            ],
            [
                InlineKeyboardButton(
                    self.S["backup"]["view_backups_btn"], callback_data=f"view_backups_{module_name}"
                ) if has_backups else None
            ],
            [InlineKeyboardButton(self.S["module_page"]["refresh_page_btn"], callback_data=f"refresh_module_page_{module_name}")],
            [InlineKeyboardButton(self.S["module_page"]["back_btn"], callback_data="back_to_modules")]
        ]

        buttons = [list(filter(None, group)) for group in buttons]

        keyboard = InlineKeyboardMarkup(buttons)
        await call.message.edit_text(text.strip(), reply_markup=keyboard)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^back_to_modules$"))
    async def call_back_to_modules(self, _, call: CallbackQuery):
        """Returns the user to the list of modules on the page they were last on."""
        page = self.last_page.get(call.message.id, 0)
        keyboard = self.generate_module_buttons(page=page)
        await call.message.edit_text(self.S["modules"]["list"], reply_markup=keyboard)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^refresh_module_page_(.*)$"))
    async def call_refresh_module_page(self, _, call: CallbackQuery):
        """Handle the refresh page process."""
        module_name = call.data.split("_")[3]
        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^update_module_(.*)$"))
    async def call_update_module(self, _, call: CallbackQuery):
        """Handle the module update process."""
        module_name = call.data.split("_")[2]
        await self.mod_update(_, call.message, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^delete_module_(.*)$"))
    async def call_delete_module(self, _, call: CallbackQuery):
        """Handle the module deletion process."""
        module_name = call.data.split("_")[2]
        await self.mod_uninstall(_, call.message, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^reload_module_(.*)$"))
    async def call_reload_module(self, _, call: CallbackQuery):
        """Handle the module restart process."""
        module_name = call.data.split("_")[2]
        
        if not await self.mod_unload(call.message, module_name, silent=True, edit=False):
            return

        if not await self.mod_load(call.message, module_name, silent=True, edit=False):
            return

        await call.answer(self.S["module_page"]["reload_ok"].format(module_name=module_name), show_alert=True)
        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^unload_module_(.*)$"))
    async def call_unload_module(self, _, call: CallbackQuery):
        """Handle the module unload process."""
        module_name = call.data.split("_")[2]
        
        if not await self.mod_unload(call.message, module_name):
            return

        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^load_module_(.*)$"))
    async def call_load_module(self, _, call: CallbackQuery):
        """Handle the module load process."""
        module_name = call.data.split("_")[2]
        
        if not await self.mod_load(call.message, module_name):
            return

        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^toggle_auto_load_(.*)$"))
    async def call_toggle_auto_load(self, _, call: CallbackQuery):
        """Handle toggling the auto_load setting for a module."""
        module_name = call.data.split("_")[3]
        self.loader: ModuleLoader

        info = self.loader.get_module_info(module_name)
        current_status = getattr(info, "auto_load", True)

        new_status = not current_status

        success = self.loader.mod_manager.set_module_auto_load(module_name, new_status)

        if success:
            status_text = self.S["module_page"]["enabled"] if new_status else self.S["module_page"]["disabled"]
            await call.answer(self.S["module_page"]["auto_load_toggled"].format(status=status_text), show_alert=True)

            await self._update_module_page(call, module_name)
        else:
            await call.answer(self.S["module_page"]["auto_load_toggle_error"], show_alert=True)

    @allowed_for("owner")
    @callback_query(filters.regex(r"^view_backups_(.+)$"))
    async def call_view_backups(self, _, call: CallbackQuery):
        """Show backups for a specific module in a dialog"""
        module_name = call.data.split("_")[2]
        self.mod_manager: ModuleManager
        await call.answer()

        backups = self.loader.mod_manager.list_backups(module_name)
        if not backups:
            await call.message.reply(self.S["backup"]["no_backups_module"].format(name=module_name))
            return

        text = self.S["backup"]["list_module"].format(name=module_name) + "\n\n"
        for backup in backups:
            text += f"- {os.path.basename(backup)}\n"

        restore_buttons = []
        # Show restore buttons for up to 5 most recent backups
        for i, backup in enumerate(backups[:5]):
            backup_name = os.path.basename(backup)
            restore_buttons.append([
                InlineKeyboardButton(
                    f"{self.S['backup']['restore_btn']} {backup_name}", 
                    callback_data=f"restore_specific_{module_name}_{i}"
                )
            ])

        restore_buttons.append([
            InlineKeyboardButton(
                self.S["backup"]["cleanup_btn"], callback_data=f"module_backup_cleanup_{module_name}"
            ),
            InlineKeyboardButton(
                self.S["backup"]["restore_latest_btn"], callback_data=f"restore_{module_name}"
            )
        ])

        restore_buttons.append([
            InlineKeyboardButton(
                self.S["backup"]["back_btn"], 
                callback_data=f"module_{module_name}_{self.last_page.get(call.message.id, 0)}"
            )
        ])

        await call.message.edit_text(
            text, 
            reply_markup=InlineKeyboardMarkup(restore_buttons)
        )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^restore_specific_(.+)_(\d+)$"))
    async def call_restore_specific(self, _, call: CallbackQuery):
        """Restore a specific backup by index"""
        match = re.match(r"restore_specific_(.+)_(\d+)", call.data)
        if not match:
            await call.answer(self.S["error"])
            return

        module_name = match.group(1)
        backup_index = int(match.group(2))

        await call.answer()

        # Get the specified backup
        backups = self.loader.mod_manager.list_backups(module_name)
        if not backups or backup_index >= len(backups):
            await call.message.reply(self.S["backup"]["invalid_backup"])
            return

        backup_path = backups[backup_index]

        # Show confirmation dialog
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    self.S["yes_btn"], 
                    callback_data=f"confirm_restore_{module_name}_{backup_index}"
                ),
                InlineKeyboardButton(
                    self.S["no_btn"], 
                    callback_data=f"module_{module_name}_{self.last_page.get(call.message.id, 0)}"
                )
            ]
        ])

        await call.message.edit_text(
            self.S["backup"]["confirm_restore"].format(
                name=module_name,
                backup=os.path.basename(backup_path)
            ),
            reply_markup=confirm_keyboard
        )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^confirm_restore_(.+)_(\d+)$"))
    async def call_confirm_restore(self, _, call: CallbackQuery):
        """Confirm restoration of a specific backup"""
        match = re.match(r"confirm_restore_(.+)_(\d+)", call.data)
        if not match:
            await call.answer(self.S["error"])
            return

        module_name = match.group(1)
        backup_index = int(match.group(2))
        
        await call.answer()

        # Get the specified backup
        backups = self.loader.mod_manager.list_backups(module_name)
        if not backups or backup_index >= len(backups):
            await call.message.reply(self.S["backup"]["invalid_backup"])
            return

        backup_path = backups[backup_index]

        # Perform restoration
        msg = await call.message.edit_text(self.S["backup"]["restoring"].format(name=module_name))
        success = self.loader.mod_manager.restore_from_backup(backup_path, module_name, "modules")
        
        if success:
            # Unload module if loaded
            if self.loader.get_module(module_name):
                self.loader.unload_module(module_name)

            # Reload the module
            result = self.loader.load_module(module_name)
            if result is not None:
                await msg.edit_text(
                    self.S["backup"]["restore_success"].format(
                        name=module_name, 
                        backup=os.path.basename(backup_path)
                    )
                )
                # After delay, go back to module page
                await sleep(2)
                await self._update_module_page(call, module_name)
            else:
                await msg.edit_text(
                    self.S["backup"]["restore_load_err"].format(
                        name=module_name, 
                        backup=os.path.basename(backup_path)
                    )
                )
        else:
            await msg.edit_text(
                self.S["backup"]["restore_failed"].format(
                    name=module_name, 
                    backup=os.path.basename(backup_path)
                )
            )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^restore_(.+)$"))
    async def restore_backup(self, _, call: CallbackQuery):
        """Restore the latest backup of a module"""
        # Original restore_backup implementation with modifications to return to module page
        int_name = call.data.split("_")[1]
        await call.answer()

        msg = await call.message.reply(self.S["backup"]["restoring"].format(name=int_name))

        # Get the latest backup
        backups = self.loader.mod_manager.list_backups(int_name)
        if not backups:
            await msg.edit_text(self.S["backup"]["no_backups_module"].format(name=int_name))
            return

        latest_backup = backups[0]

        # Perform restoration
        success = self.loader.mod_manager.restore_from_backup(latest_backup, int_name, "modules")

        if success:
            # Reload the module
            result = self.loader.load_module(int_name)
            if result is not None:
                await msg.edit_text(
                    self.S["backup"]["restore_success"].format(
                        name=int_name, 
                        backup=os.path.basename(latest_backup)
                    )
                )
                # After delay, refresh module page
                await sleep(2)
                await self._update_module_page(call, int_name)
            else:
                await msg.edit_text(
                    self.S["backup"]["restore_load_err"].format(
                        name=int_name, 
                        backup=os.path.basename(latest_backup)
                    )
                )
        else:
            await msg.edit_text(
                self.S["backup"]["restore_failed"].format(
                    name=int_name, 
                    backup=os.path.basename(latest_backup)
                )
            )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^module_backup_cleanup_(.+)$"))
    async def call_module_backup_cleanup(self, _, call: CallbackQuery):
        """Show cleanup options for module backups"""
        module_name = call.data.split("_")[3]
        await call.answer()

        # Display cleanup options
        cleanup_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    self.S["backup"]["all_except_latest"], 
                    callback_data=f"do_cleanup_{module_name}_all"
                ),
                InlineKeyboardButton(
                    self.S["backup"]["back_btn"], 
                    callback_data=f"module_{module_name}_{self.last_page.get(call.message.id, 0)}"
                )
            ]
        ])

        await call.message.edit_text(
            self.S["backup"]["cleanup_select_count"].format(name=module_name),
            reply_markup=cleanup_keyboard
        )

    @allowed_for("owner")
    @callback_query(filters.regex(r"^do_cleanup_(.+)_(all|\d+)$"))
    async def call_do_cleanup(self, _, call: CallbackQuery):
        """Perform backup cleanup with specified keep count"""
        match = re.match(r"do_cleanup_(.+)_(all|\d+)", call.data)
        if not match:
            await call.answer(self.S["error"])
            return
            
        module_name = match.group(1)
        keep_param = match.group(2)
        
        keep_count = 1 if keep_param == 'all' else int(keep_param)
        
        await call.answer()
        deleted = self.loader.mod_manager.cleanup_old_backups(module_name, keep_count)
        
        msg = await call.message.edit_text(
            self.S["backup"]["cleanup_complete"].format(
                name=module_name, 
                count=deleted, 
                keep=keep_count
            )
        )
        
        # After delay, return to module page
        await sleep(2)
        await self._update_module_page(call, module_name)

    @allowed_for("owner")
    @callback_query(filters.regex("install_yes"))
    async def install_yes(self, _, call: CallbackQuery):
        msg, name = self.install_confirmations[call.message.id]
        self.install_confirmations.pop(call.message.id)

        await call.answer()

        if os.path.exists(f"{os.getcwd()}/modules/{name}/requirements.txt"):
            # Install deps
            await msg.edit_text(self.S["install"]["down_reqs_next"].format(name))
            code, data = self.loader.mod_manager.install_deps(name, "modules")
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
                reqs_list += f"- {req}"

            await msg.edit_text(self.S["install"]["end_reqs"].format(result, reqs_list))

        else:
            await msg.edit_text(self.S["install"]["down_end_next"].format(name))

            # Load module
            result = self.loader.load_module(name)
            if result is None:
                await msg.edit_text(self.S["install"]["load_err"].format(name))
                return

            await msg.edit_text(self.S["install"]["end"].format(result))

    @allowed_for("owner")
    @callback_query(filters.regex("install_no"))
    async def install_no(self, _, call: CallbackQuery):
        msg, name = self.install_confirmations[call.message.id]
        self.install_confirmations.pop(call.message.id)

        shutil.rmtree(f"./modules/{name}")
        await call.answer(self.S["install"]["aborted"])
        await msg.delete()

    async def mod_uninstall(self, _, message, name):
        """Uninstall module"""
        self.loader: ModuleLoader

        # Uninstall module
        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return
        if int_name.lower() == "core":
            await message.reply(self.S["uninstall"]["core_uninstall_error"])
            return

        result = self.loader.mod_manager.uninstall_module(int_name)
        await message.reply(
            (
                self.S["uninstall"]["ok"] if result else self.S["uninstall"]["err"]
            ).format(name)
        )

    async def mod_update(self, _, message, name):
        """Update module to the upstream version"""
        self.loader: ModuleLoader

        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return

        msg = await message.reply(self.S["install"]["start"].format(name))

        # Check for updates
        update_available = self.loader.mod_manager.check_for_updates(int_name, "modules")
        if update_available is None:
            await msg.edit_text(self.S["update"]["check_err"].format(name=name))
            return
        elif not update_available:
            await msg.edit_text(self.S["update"]["no_updates_found"].format(name=name))
            return

        old_ver = self.loader.get_module_info(int_name).version
        old_reqs = None

        reqs_path = f"{os.getcwd()}/modules/{int_name}/requirements.txt"
        if os.path.exists(reqs_path):
            old_reqs = requirements.parse(open(reqs_path, encoding="utf-8"))

        # Create backup before updating
        await msg.edit_text(self.S["update"]["creating_backup"].format(name=name))
        if not self.loader.prepare_for_module_update(int_name):
            return

        code, stdout, backup_path = self.loader.mod_manager.update_from_git(int_name, "modules")
        
        if code != 0:
            await msg.edit_text(self.S["update"]["err"].format(name=name, out=stdout))
            await msg.edit_text(self.S["update"]["reverting"].format(name=name))
            self.loader.mod_manager.revert_update(int_name, "modules")
            await msg.edit_text(self.S["update"]["revert_complete"].format(name=name))
            return

        # Parse info file
        try:
            info_file = InfoFile.from_yaml_file(
                f"{os.getcwd()}/modules/{int_name}/info.yaml"
            )
        except FileNotFoundError:
            await msg.edit_text(self.S["update"]["info_file_missing"].format(name=name))
            await msg.edit_text(self.S["update"]["reverting"].format(name=name))
            self.loader.mod_manager.revert_update(int_name, "modules")
            return

        info = info_file.info
        permissions = info_file.permissions

        text = (
            self.S["update"]["confirm"].format(
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

        # Add backup info to the confirmation message
        if backup_path:
            text += self.S["update"]["backup_created"].format(path=os.path.basename(backup_path))

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self.S["yes_btn"], callback_data=f"update_yes"
                    ),
                    InlineKeyboardButton(self.S["no_btn"], callback_data=f"update_no"),
                ]
            ]
        )
        await msg.edit_text(text, reply_markup=keyboard)
        self.update_confirmations[msg.id] = [msg, name, int_name, old_ver, old_reqs, backup_path]

    @allowed_for("owner")
    @callback_query(filters.regex("update_yes"))
    async def update_yes(self, _, call: CallbackQuery):
        self.loader: ModuleLoader
        msg, name, int_name, old_ver, old_reqs, backup_path = self.update_confirmations[call.message.id]
        await call.answer()

        try_again_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(self.S["try_again_btn"], callback_data=f"update_yes"),
            InlineKeyboardButton(self.S["abort_btn"], callback_data=f"update_no")]
        ])

        reqs_path = f"{os.getcwd()}/modules/{int_name}/requirements.txt"
        if os.path.exists(reqs_path):
            reqs = requirements.parse(open(reqs_path, encoding="utf-8"))
            del_reqs = []
            for req in old_reqs:
                found = False
                for new_req in reqs:
                    if req.name.lower() == new_req.name.lower():
                        found = True
                        break
                if not found:
                    del_reqs.append(req.name.lower())

            # Install deps
            await msg.edit_text(self.S["install"]["down_reqs_next"].format(name))
            code, data = self.loader.mod_manager.install_deps(int_name, "modules")
            if code != 0:
                await msg.edit_text(
                    self.S["install"]["reqs_err"].format(name, data),
                    reply_markup=try_again_keyboard,
                )
                return

            # Unload module if loaded
            if self.loader.get_module(int_name):
                self.loader.unload_module(int_name)

            # Load module
            result = self.loader.load_module(int_name)
            if result is None:
                await msg.edit_text(self.S["install"]["load_err"].format(name), reply_markup=try_again_keyboard)
                return

            modules_deps = self.loader.get_modules_deps()
            self.loader.mod_manager.uninstall_packages(del_reqs, modules_deps)

            info = self.loader.get_module_info(int_name)
            text = (self.S["update"]["ok"].format(name=result, old_ver=old_ver, new_ver=info.version, url=info.src_url) + "\n" + self.S["update"]["reqs"] + "\n")
            for req in data:
                text += f"- {req}\n"

            # Clear the hash backup since the update was successful
            self.loader.mod_manager.clear_hash_backup(int_name)
            await msg.edit_text(text)
        else:
            await msg.edit_text(self.S["install"]["down_end_next"].format(name))

            # Unload module if loaded
            if self.loader.get_module(int_name):
                self.loader.unload_module(int_name)

            # Load module
            result = self.loader.load_module(int_name)
            if result is None:
                await msg.edit_text(self.S["install"]["load_err"].format(name), reply_markup=try_again_keyboard)
                return

            # Clear the hash backup since the update was successful
            self.loader.mod_manager.clear_hash_backup(int_name)
            info = self.loader.get_module_info(int_name)
            await msg.edit_text(self.S["update"]["ok"].format(name=result, old_ver=old_ver, new_ver=info.version, url=info.src_url))

        self.update_confirmations.pop(call.message.id)

    @allowed_for("owner")
    @callback_query(filters.regex("update_no"))
    async def update_no(self, _, call: CallbackQuery):
        msg, name, int_name, _, _, _ = self.update_confirmations[call.message.id]
        self.update_confirmations.pop(call.message.id)

        await call.answer(self.S["update"]["abort"])
        await msg.edit_text(self.S["update"]["reverting"].format(name=name))

        if self.loader.mod_manager.revert_update(int_name, "modules"):
            self.loader.load_module(int_name)
            await msg.edit_text(self.S["update"]["revert_complete"].format(name=name))
        else:
            await msg.edit_text(self.S["update"]["revert_failed"].format(name=name))

    async def mod_load(self, message: Message, name: str, silent = False, edit = False) -> Optional[str]:
        if edit:
            reply_func = message.edit_text
        else:
            reply_func = message.reply
        
        if self.loader.get_module(name):
            await reply_func(self.S["load"]["already_loaded_err"].format(name))
            return
        
        try:
            res = self.loader.load_module(name)
            if res is None:
                await reply_func(self.S["load"]["load_err"].format(name))
                return
        except FileNotFoundError:
            await reply_func(self.S["load"]["not_found"].format(name))
            return
        except:
            await reply_func(self.S["load"]["load_err"].format(name))
            return
        
        if not silent:
            await reply_func(self.S["load"]["ok"].format(res))
        
        return res

    async def mod_unload(self, message: Message, name: str, silent = False, edit = False) -> Optional[str]:
        if edit:
            reply_func = message.edit_text
        else:
            reply_func = message.reply

        if name.lower() == "core":
            await reply_func(self.S["unload"]["unload_core"])
            return
        
        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await reply_func(self.S["unload"]["not_loaded_err"].format(name))
            return
        
        self.loader.unload_module(int_name)
        if not silent:
            await reply_func(self.S["unload"]["ok"].format(name))
        
        return int_name

    @callback_query(filters.regex(r"^dummy"))
    async def dummy_callback(self, _, call: CallbackQuery):
        await call.answer()