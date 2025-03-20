import logging
import os
import subprocess
import shutil
import time
import zipfile
from typing import Optional, Tuple, List
import json


logger = logging.getLogger(__name__)

class BackupManager:
    """
    Manages module backups and restoration for safe module updates.
    Provides both git-based and file-based backup/restore capabilities.
    """
    
    def __init__(self, root_dir: str):
        self.__root_dir = root_dir
        self.__backup_dir = os.path.join(root_dir, "backups")
        self.__ensure_backup_dir()
        
    def __ensure_backup_dir(self):
        """Ensure the backup directory exists"""
        if not os.path.exists(self.__backup_dir):
            try:
                os.makedirs(self.__backup_dir)
                logger.info(f"Created backup directory at {self.__backup_dir}")
            except Exception as e:
                logger.error(f"Failed to create backup directory: {e}")

    def safe_remove_tree(self, path: str) -> List[str]:
        skipped_files = []
        for root, dirs, files in os.walk(path, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to remove file {file_path}: {e}")
                    skipped_files.append(file_path)
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    logger.warning(f"Failed to remove directory {dir_path}: {e}")
                    skipped_files.append(dir_path)
        return skipped_files

    def safe_copy_tree(self, src: str, dst: str) -> list[str]:
        skipped_files = []
        for root, dirs, files in os.walk(src):
            rel_path = os.path.relpath(root, src)
            dest_dir = os.path.join(dst, rel_path)
            os.makedirs(dest_dir, exist_ok=True)
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as e:
                    logger.warning(f"Failed to copy file {src_file} to {dst_file}: {e}")
                    skipped_files.append(dst_file)
        return skipped_files
 
    def create_backup(self, name: str, directory: str) -> Tuple[bool, str]:
        """
        Create a backup of a module, skipping the .git folder and storing git metadata if applicable.

        :param name: Name of the module to backup
        :param directory: Directory containing the module (e.g., 'modules')
        :return: Tuple (success, backup_path or error_message)
        """
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_filename = f"{name}_{timestamp}.zip"
            backup_path = os.path.join(self.__backup_dir, backup_filename)
            source_dir = os.path.join(self.__root_dir, directory, name)

            if not os.path.exists(source_dir):
                return False, f"Module directory {source_dir} does not exist"

            # Prepare metadata
            metadata = {}
            if os.path.exists(os.path.join(source_dir, ".git")):
                # Get current commit hash
                hash_p = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=source_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
                if hash_p.returncode == 0:
                    commit_hash = hash_p.stdout.decode("utf-8").strip()
                    # Get untracked files
                    untracked_p = subprocess.run(
                        ["git", "ls-files", "--others", "--exclude-standard"],
                        cwd=source_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT
                    )
                    if untracked_p.returncode == 0:
                        untracked_files = untracked_p.stdout.decode("utf-8").splitlines()
                        metadata = {
                            "is_git_repo": True,
                            "commit_hash": commit_hash,
                            "untracked_files": untracked_files
                        }
                    else:
                        logger.warning(f"Failed to get untracked files for {name}")
                        metadata = {"is_git_repo": False}
                else:
                    logger.warning(f"Failed to get commit hash for {name}")
                    metadata = {"is_git_repo": False}
            else:
                metadata = {"is_git_repo": False}

            # Create zip backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Write metadata
                zipf.writestr("backup_meta.json", json.dumps(metadata))
                # Add files, excluding .git
                for root, dirs, files in os.walk(source_dir):
                    if '.git' in dirs:
                        dirs.remove('.git')
                    rel_dir = os.path.relpath(root, source_dir)
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join(rel_dir, file) if rel_dir != '.' else file
                        zipf.write(file_path, arcname)

            logger.info(f"Created backup of module {name} at {backup_path}")
            return True, backup_path
        except Exception as e:
            logger.error(f"Failed to create backup for module {name}: {e}")
            return False, str(e)

    def restore_from_backup(self, backup_path: str, name: str, directory: str) -> Tuple[bool, List[str]]:
        """
        Restore a module from a backup, performing a git reset and restoring untracked files for git repos.

        :param backup_path: Path to the backup zip file
        :param name: Name of the module to restore
        :param directory: Directory containing the module (e.g., 'modules')
        :return: Tuple (success, list of skipped files)
        """
        try:
            module_dir = os.path.join(self.__root_dir, directory, name)
            if not os.path.exists(backup_path):
                logger.error(f"Backup file {backup_path} not found")
                return False, []

            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Read metadata
                import json
                try:
                    with zipf.open("backup_meta.json") as meta_file:
                        metadata = json.load(meta_file)
                except KeyError:
                    # Backward compatibility: treat as non-git backup
                    metadata = {"is_git_repo": False}

                if metadata.get("is_git_repo", False) and metadata.get("commit_hash"):
                    # Handle git repository restoration
                    commit_hash = metadata["commit_hash"]
                    reset_p = subprocess.run(
                        ["git", "reset", "--hard", commit_hash],
                        cwd=module_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT
                    )
                    if reset_p.returncode != 0:
                        logger.error(f"Failed to reset repository for {name}: {reset_p.stdout.decode('utf-8')}")
                        return False, []

                    # Restore untracked files
                    untracked_files = metadata.get("untracked_files", [])
                    skipped_files = []
                    for file in untracked_files:
                        try:
                            zipf.extract(file, module_dir)
                        except Exception as e:
                            logger.warning(f"Failed to extract {file}: {e}")
                            skipped_files.append(os.path.join(module_dir, file))
                    logger.info(f"Restored git module {name} from backup {backup_path}")
                    return True, skipped_files
                else:
                    # Handle non-git restoration
                    if os.path.exists(module_dir):
                        skipped_remove = self.safe_remove_tree(module_dir)
                    else:
                        skipped_remove = []
                    os.makedirs(module_dir, exist_ok=True)
                    try:
                        zipf.extractall(module_dir)
                        skipped_copy = []
                    except Exception as e:
                        logger.error(f"Failed to extract backup for {name}: {e}")
                        skipped_copy = [module_dir]
                    logger.info(f"Restored non-git module {name} from backup {backup_path}")
                    return True, skipped_remove + skipped_copy
        except Exception as e:
            logger.error(f"Failed to restore module {name} from backup: {e}")
            return False, []
    
    def list_backups(self, name: Optional[str] = None) -> list:
        """
        List available backups, optionally filtered by module name
        
        :param name: Optional name of the module to filter backups
        :return: List of backup files (full paths)
        """
        try:
            all_backups = []
            if os.path.exists(self.__backup_dir):
                for file in os.listdir(self.__backup_dir):
                    if file.endswith('.zip'):
                        # If a module name is specified, filter for that module
                        if name is None or file.startswith(f"{name}_"):
                            all_backups.append(os.path.join(self.__backup_dir, file))
            
            # Sort by modification time (newest first)
            all_backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return all_backups
        
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def get_latest_backup(self, name: str) -> Optional[str]:
        """
        Get the most recent backup for a specific module
        
        :param name: Name of the module
        :return: Path to the most recent backup or None if no backups exist
        """
        backups = self.list_backups(name)
        return backups[0] if backups else None
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a backup file
        
        :param backup_path: Path to the backup file to delete
        :return: Success status
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f"Deleted backup {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False
    
    def cleanup_old_backups(self, name: str, keep_count: int = 5) -> int:
        """
        Remove old backups of a module, keeping only the most recent ones
        
        :param name: Name of the module
        :param keep_count: Number of recent backups to keep
        :return: Number of backups deleted
        """
        try:
            backups = self.list_backups(name)
            if len(backups) <= keep_count:
                return 0
            
            # Delete older backups
            deleted_count = 0
            for backup in backups[keep_count:]:
                if self.delete_backup(backup):
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clean up old backups for {name}: {e}")
            return 0
