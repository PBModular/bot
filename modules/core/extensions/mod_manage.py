from base.mod_ext import ModuleExtension
from base.module import command, callback_query, allowed_for, Permissions, InfoFile
from base.loader import ModuleLoader

from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from pyrogram import filters, errors
from urllib.parse import urlparse
import os
import shutil
import requirements
from asyncio import sleep
from typing import Optional


class ModManageExtension(ModuleExtension):
    def on_init(self):
        self.install_confirmations = {}
        self.update_confirmations = {}
        self.last_page = {}

    def generate_module_buttons(self, page: int = 0, items_per_page: int = 5):
        """Creates a keyboard with a list of all modules, sorted alphabetically, with pagination."""
        self.loader: ModuleLoader
        modules_info = self.loader.get_modules_info()
        
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

        await self.update_module_page(call, module_name)

    async def update_module_page(self, call, module_name):
        """Update the module page with the latest information, and check for updates."""
        self.loader: ModuleLoader

        info = self.loader.get_module_info(module_name)
        text = f"{self.S['module_page']['name'].format(name=info.name)}\n" if info.name else ""
        text += f"{self.S['module_page']['author'].format(author=info.author)}\n" if info.author else ""
        text += f"{self.S['module_page']['version'].format(version=info.version)}\n" if info.version else ""
        text += f"{self.S['module_page']['src_url'].format(url=info.src_url)}\n" if info.src_url else ""
        text += f"\n{self.S['module_page']['description'].format(description=info.description)}" if info.description else ""
        
        git_repo_path = os.path.join(os.getcwd(), "modules", module_name, ".git")
        if os.path.exists(git_repo_path):
            update_message = self.loader.check_for_updates(module_name, "modules")

        if update_message == True:
            text += f"\n\n{self.S['module_page']['updates_found']}"
        elif update_message == False:
            text += f"\n\n{self.S['module_page']['no_updates_found']}"

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
                    ) if os.path.exists(git_repo_path) and update_message else None,
                InlineKeyboardButton(self.S["module_page"]["delete_btn"], callback_data=f"delete_module_{module_name}")
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
        try:
            await self.update_module_page(call, module_name)

        except errors.MessageNotModified:
            await call.answer(self.S["module_page"]["no_changes"])
        except Exception as e:
            await call.edit_message_text(self.S["module_page"]["refresh_page_err"].format(module_name=module_name))
            self.logger.error(f"Failed to refresh {module_name} page! \n{e}")

    @allowed_for("owner")
    @callback_query(filters.regex(r"^update_module_(.*)$"))
    async def call_update_module(self, _, call: CallbackQuery):
        """Handle the module update process."""
        module_name = call.data.split("_")[2]

        if not await self.mod_update(_, call.message, module_name):
            return

    @allowed_for("owner")
    @callback_query(filters.regex(r"^delete_module_(.*)$"))
    async def call_delete_module(self, _, call: CallbackQuery):
        """Handle the module deletion process."""
        module_name = call.data.split("_")[2]

        if not await self.mod_uninstall(_, call.message, module_name):
            return

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

    @allowed_for("owner")
    @callback_query(filters.regex(r"^unload_module_(.*)$"))
    async def call_unload_module(self, _, call: CallbackQuery):
        """Handle the module unload process."""
        module_name = call.data.split("_")[2]
        
        if not await self.mod_unload(call.message, module_name):
            return

    @allowed_for("owner")
    @callback_query(filters.regex(r"^load_module_(.*)$"))
    async def call_load_module(self, _, call: CallbackQuery):
        """Handle the module load process."""
        module_name = call.data.split("_")[2]
        
        if not await self.mod_load(call.message, module_name):
            return

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
    @callback_query(filters.regex("install_yes"))
    async def install_yes(self, _, call: CallbackQuery):
        msg, name = self.install_confirmations[call.message.id]
        self.install_confirmations.pop(call.message.id)

        await call.answer()

        if os.path.exists(f"{os.getcwd()}/modules/{name}/requirements.txt"):
            # Install deps
            await msg.edit_text(self.S["install"]["down_reqs_next"].format(name))
            code, data = self.loader.install_deps(name, "modules")
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

    @allowed_for("owner")
    @command("mod_uninstall")
    async def mod_uninstall_cmd(self, _, message: Message):
        if len(message.text.split()) == 1:
            await message.reply(self.S["uninstall"]["args_err"])
            return

        name = " ".join(message.text.split()[1:])
        await self.mod_uninstall(_, message, name)

    async def mod_uninstall(self, _, message, name):
        """Uninstall module"""
        self.loader: ModuleLoader

        # Uninstall module
        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return

        result = self.loader.uninstall_module(int_name)
        await message.reply(
            (
                self.S["uninstall"]["ok"] if result else self.S["uninstall"]["err"]
            ).format(name)
        )

    @allowed_for("owner")
    @command("mod_update")
    async def mod_update_cmd(self, _, message: Message):
        if len(message.text.split()) == 1:
            await message.reply(self.S["update"]["args_err"])
            return

        name = " ".join(message.text.split()[1:])
        await self.mod_update(_, message, name)

    async def mod_update(self, _, message, name):
        """Update module to the upstream version"""
        self.loader: ModuleLoader

        int_name = self.loader.get_int_name(name)
        if int_name is None:
            await message.reply(self.S["uninstall"]["not_found"].format(name))
            return

        msg = await message.reply(self.S["install"]["start"].format(name))

        old_ver = self.loader.get_module_info(int_name).version
        old_reqs = None

        reqs_path = f"{os.getcwd()}/modules/{int_name}/requirements.txt"
        if os.path.exists(reqs_path):
            old_reqs = requirements.parse(open(reqs_path, encoding="utf-8"))

        code, stdout = self.loader.update_from_git(int_name, "modules")
        if code != 0:
            await msg.edit_text(self.S["update"]["err"].format(name=name, out=stdout))
            self.loader.revert_update(int_name, "modules")
            return

        # Parse info file
        try:
            info_file = InfoFile.from_yaml_file(
                f"{os.getcwd()}/modules/{int_name}/info.yaml"
            )
        except FileNotFoundError:
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
        self.update_confirmations[msg.id] = [msg, name, int_name, old_ver, old_reqs]

    @allowed_for("owner")
    @callback_query(filters.regex("update_yes"))
    async def update_yes(self, _, call: CallbackQuery):
        self.loader: ModuleLoader
        msg, name, int_name, old_ver, old_reqs = self.update_confirmations[
            call.message.id
        ]
        await call.answer()

        try_again_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self.S["try_again_btn"], callback_data=f"update_yes"
                    ),
                    InlineKeyboardButton(
                        self.S["abort_btn"], callback_data=f"update_no"
                    ),
                ]
            ]
        )

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
            code, data = self.loader.install_deps(int_name, "modules")
            if code != 0:
                await msg.edit_text(
                    self.S["install"]["reqs_err"].format(name, data),
                    reply_markup=try_again_keyboard,
                )
                return

            # Load module
            result = self.loader.load_module(int_name)
            if result is None:
                await msg.edit_text(
                    self.S["install"]["load_err"].format(name),
                    reply_markup=try_again_keyboard,
                )
                return

            # Cleanup
            self.loader.uninstall_packages(del_reqs)

            info = self.loader.get_module_info(int_name)
            text = (
                self.S["update"]["ok"].format(
                    name=result, old_ver=old_ver, new_ver=info.version, url=info.src_url
                )
                + "\n"
                + self.S["update"]["reqs"]
                + "\n"
            )

            for req in data:
                text += f"- {req}\n"

            await msg.edit_text(text)
        else:
            await msg.edit_text(self.S["install"]["down_end_next"].format(name))

            # Load module
            result = self.loader.load_module(int_name)
            if result is None:
                await msg.edit_text(
                    self.S["install"]["load_err"].format(name),
                    reply_markup=try_again_keyboard,
                )
                return

            info = self.loader.get_module_info(int_name)
            await msg.edit_text(
                self.S["update"]["ok"].format(
                    name=result, old_ver=old_ver, new_ver=info.version, url=info.src_url
                )
            )

        self.update_confirmations.pop(call.message.id)

    @allowed_for("owner")
    @callback_query(filters.regex("update_no"))
    async def update_no(self, _, call: CallbackQuery):
        msg, name, int_name, _, _ = self.update_confirmations[call.message.id]
        self.update_confirmations.pop(call.message.id)

        self.loader.revert_update(int_name, "modules")
        self.loader.load_module(int_name)

        await call.answer(self.S["update"]["abort"])
        await msg.delete()

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

    @callback_query(filters.regex(r"^dummy"))
    async def dummy_callback(self, _, call: CallbackQuery):
        await call.answer()