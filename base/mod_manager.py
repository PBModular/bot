import logging
import os
import subprocess
import sys
import shutil
from urllib.parse import urlparse
from typing import Optional, Union, Tuple
from packaging import version
import importlib
import inspect

from base.db_migration import DBMigration

logger = logging.getLogger(__name__)


class ModuleManager:
    """
    Handles module installation, updates, dependency management, and configuration.
    """

    def __init__(self, root_dir: str):
        self.__root_dir = root_dir
        self.__hash_backups: dict[str, str] = {}
        
    def install_from_git(self, url: str) -> Tuple[int, str]:
        """
        Module installation method. Clones git repository from the given URL
        
        :param url: Git repository URL
        :return: Tuple with exit code and read STDOUT
        """
        logger.info(f"Downloading module from git URL {url}!")
        name = urlparse(url).path.split("/")[-1].removesuffix(".git")
        modules_dir = os.path.join(self.__root_dir, "modules")
        p = subprocess.run(
            ["git", "clone", url, name],
            cwd=modules_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        if p.returncode != 0:
            logger.error(f"Error while cloning module {name}!")
            logger.error(f"Printing STDOUT and STDERR:")
            logger.error(p.stdout.decode("utf-8"))
            subprocess.run(["rm", f"{self.__root_dir}/modules/{name}"])

        return p.returncode, p.stdout.decode("utf-8")

    def check_for_updates(self, name: str, directory: str) -> Optional[bool]:
        """
        Check if there are new commits available for the module or extension.
        
        :param name: Name of the module or extension
        :param directory: Directory of modules or extensions
        :return: True if there are new commits, False if up-to-date, or None on error
        """
        try:
            repo_dir = os.path.join(self.__root_dir, directory, name)
            p = subprocess.run(
                ["git", "fetch"], cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            
            if p.returncode != 0:
                logger.error(f"Error while fetching updates for {name}!")
                logger.error(p.stdout.decode("utf-8"))
                return None

            cmd_check = (
                f"cd {self.__root_dir}/{directory}/{name} && git rev-list --count HEAD..origin"
            )
            p_check = subprocess.run(
                cmd_check, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )

            if p_check.returncode != 0:
                logger.error(f"Error while checking for new commits for {name}!")
                logger.error(p_check.stdout.decode("utf-8"))
                return None

            output = p_check.stdout.decode("utf-8").strip()

            # Handle empty or invalid output
            if not output.isdigit():
                logger.warning(f"Unexpected output when checking for commits: {output}")
                return False  # Assume no new commits if output is invalid

            new_commits_count = int(output)
            return new_commits_count > 0

        except Exception as e:
            logger.error(f"Failed to check for new commits for {name}. Details: {e}")
            return None

    def update_from_git(self, name: str, directory: str, module=None) -> Tuple[int, str]:
        """
        Method to update git repository (module or extensions)
        Remembers commit hash for reverting and executes git pull
        
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :param module: Module object if updating a loaded module (provides access to version, db, etc.)
        :return: Exit code and output of git pull
        """
        # Store module data before unloading if provided
        prev_version = None
        prev_db = None
        prev_db_meta = None
        
        if module:
            prev_version = module.module_info.version
            prev_db = module.db
            prev_db_meta = module.db_meta

        logger.info(f"Updating {name}!")

        # Backup current hash
        repo_dir = os.path.join(self.__root_dir, directory, name)
        hash_p = subprocess.run(
            ["git", "rev-parse", "HEAD"], 
            cwd=repo_dir, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        
        if hash_p.returncode != 0:
            logger.error(f"Failed to retrieve HEAD hash for {name}. STDOUT below")
            logger.error(hash_p.stdout.decode("utf-8"))
            return hash_p.returncode, hash_p.stdout.decode("utf-8")

        self.__hash_backups[name] = hash_p.stdout.decode("utf-8")

        # Pull updates
        p = subprocess.run(
            ["git", "pull"], 
            cwd=repo_dir, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        if p.returncode != 0:
            logger.error(f"Error while updating module {name}!")
            logger.error(f"Printing STDOUT and STDERR:")
            logger.error(p.stdout.decode("utf-8"))
            return p.returncode, p.stdout.decode("utf-8")

        # Start database migration if module provided and db_migrations directory exists
        if prev_db is not None and os.path.exists(
            f"{self.__root_dir}/{directory}/{name}/db_migrations"
        ):
            for file in os.listdir(
                f"{self.__root_dir}/{directory}/{name}/db_migrations"
            ):
                mig_ver = file.removesuffix(".py")
                if version.parse(prev_version) < version.parse(mig_ver):
                    logger.info(
                        f"Migrating database for module {name} to version {mig_ver}..."
                    )
                    imported = importlib.import_module(
                        f"modules.{name}.db_migrations.{mig_ver}"
                    )
                    classes = inspect.getmembers(imported, inspect.isclass)
                    if len(classes) == 0:
                        logger.error("Invalid migration! No DBMigration classes found!")
                        continue

                    obj = classes[0][1]  # Use first detected class
                    instance: DBMigration = obj()
                    instance.apply(prev_db.session, prev_db.engine, prev_db_meta)

        return p.returncode, p.stdout.decode("utf-8")

    def revert_update(self, name: str, directory: str) -> bool:
        """
        Reverts update caused by update_from_git(). Resets to previously stored hash.
        
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :return: Boolean (success or not)
        """
        try:
            if name not in self.__hash_backups:
                logger.error(f"Tried to revert module {name} with no pending update!")
                return False
                
            repo_dir = os.path.join(self.__root_dir, directory, name)
            p = subprocess.run(
                ["git", "reset", "--hard", self.__hash_backups[name]], 
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )

            if p.returncode != 0:
                logger.error(
                    f"Failed to revert update of module {name}! Printing STDOUT"
                )
                logger.error(p.stdout.decode("utf-8"))
                return False

            logger.info(f"Update of module {name} reverted!")
            return True
        except Exception as e:
            logger.error(f"Error reverting update for {name}: {e}")
            return False

    def install_deps(self, name: str, directory: str) -> Tuple[int, Union[str, list[str]]]:
        """
        Method to install Python dependencies from requirements.txt file
        
        :param name: Name of module or extension
        :param directory: Directory of modules or extensions
        :return: Tuple with exit code and read STDOUT or list of requirements
        """
        logger.info(f"Upgrading dependencies for {name}!")
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                "-r",
                f"{self.__root_dir}/{directory}/{name}/requirements.txt",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if r.returncode != 0:
            logger.error(
                f"Error at upgrading deps for {name}!\nPip output:\n"
                f"{r.stdout.decode('utf-8')}"
            )
            return r.returncode, r.stdout.decode("utf-8")
        else:
            logger.info(f"Dependencies upgraded successfully!")
            with open(f"{self.__root_dir}/{directory}/{name}/requirements.txt") as f:
                reqs = [dep.removesuffix("\n") for dep in f]
                if not reqs:
                    logger.warning(f"{name} requirements.txt is empty")
                elif reqs[-1] == "":
                    reqs.pop(-1)

                return r.returncode, reqs

    def uninstall_mod_deps(self, name: str, modules_deps: dict[str, list[str]]):
        """
        Method to uninstall module dependencies. Removes package only if it isn't required by other module
        
        :param name: Name of module
        :param modules_deps: Dictionary mapping module names to their dependencies
        """
        if name not in modules_deps:
            logger.warning(f"No dependencies found for module {name}")
            return
            
        for mod_dep in modules_deps[name]:
            found = False
            for other_name, deps in modules_deps.items():
                if other_name == name:
                    continue
                if mod_dep in deps:
                    found = True
                    break
            if found:
                continue

            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", mod_dep],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

    def uninstall_packages(self, pkgs: list[str], modules_deps: dict[str, list[str]]):
        """
        Uninstall specified packages if they are not required by any module
        
        :param pkgs: List of package names to uninstall
        :param modules_deps: Dictionary mapping module names to their dependencies
        """
        for dep in pkgs:
            found = False
            for other_name, deps in modules_deps.items():
                if dep in deps:
                    found = True
                    break
            if found:
                continue

            subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", dep],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

    def uninstall_module(self, name: str, modules_deps: dict[str, list[str]]) -> bool:
        """
        Module uninstallation method. Removes module directory and its dependencies
        
        :param name: Name of Python module inside modules dir
        :param modules_deps: Dictionary mapping module names to their dependencies
        :return: Bool, representing success or not
        """
        try:
            # Remove deps if they exist in the dependency dictionary
            if name in modules_deps:
                self.uninstall_mod_deps(name, modules_deps)
                modules_deps.pop(name)
                
            # Remove module directory
            if os.path.exists(f"./modules/{name}"):
                shutil.rmtree(f"./modules/{name}")
                logger.info(f"Successfully removed module {name}!")
                return True
            else:
                logger.warning(f"Module directory for {name} not found.")
                return False
        except Exception as e:
            logger.error(f"Error while removing module {name}! Printing traceback...")
            logger.exception(e)
            return False

    def set_module_auto_load(self, name: str, auto_load: bool) -> bool:
        """
        Set auto_load preference for a module
        
        :param name: Name of Python module inside modules dir
        :param auto_load: Whether to auto-load the module on startup
        :return: Success status
        """
        try:
            info_path = f"./modules/{name}/info.yaml"
            
            # Ensure directory exists
            if not os.path.exists(f"./modules/{name}"):
                logger.error(f"Module directory for {name} not found.")
                return False
            
            import yaml
            info = {}
            if os.path.exists(info_path):
                with open(info_path, "r") as f:
                    info = yaml.safe_load(f) or {}
            
            # Update auto_load setting
            info["auto_load"] = auto_load
            
            with open(info_path, "w") as f:
                yaml.dump(info, f)
                
            return True
        except Exception as e:
            logger.error(f"Error updating auto_load for {name}: {e}")
            return False

    def get_hash_backups(self) -> dict[str, str]:
        """
        Get the current hash backups dictionary
        
        :return: Dictionary of module name to hash backup mappings
        """
        return self.__hash_backups

    def clear_hash_backup(self, name: str) -> bool:
        """
        Clear a specific hash backup
        
        :param name: Name of the module
        :return: Whether the hash was cleared
        """
        if name in self.__hash_backups:
            self.__hash_backups.pop(name)
            return True
        return False
