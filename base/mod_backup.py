import logging
import os
import subprocess
import sys
import shutil
import tempfile
import time
from pathlib import Path
import zipfile
from typing import Optional, Union, Tuple, Dict, Any

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
                
    def create_backup(self, name: str, directory: str) -> Tuple[bool, str]:
        """
        Create a backup of a module before updating
        
        :param name: Name of the module to backup
        :param directory: Directory containing the module (e.g. 'modules')
        :return: Tuple (success, backup_path or error_message)
        """
        try:
            # Create timestamped backup filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            backup_filename = f"{name}_{timestamp}.zip"
            backup_path = os.path.join(self.__backup_dir, backup_filename)
            
            # Source directory for the module
            source_dir = os.path.join(self.__root_dir, directory, name)
            
            # Check if source directory exists
            if not os.path.exists(source_dir):
                return False, f"Module directory {source_dir} does not exist"
                
            # Create zip backup
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(source_dir):
                    # Get the relative path from the module directory
                    rel_dir = os.path.relpath(root, os.path.join(self.__root_dir, directory))
                    
                    # Skip git directory to save space
                    if '.git' in rel_dir.split(os.sep):
                        continue
                        
                    # Add all files to the zip
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Store with relative path in the zip
                        arcname = os.path.join(rel_dir, file)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Created backup of module {name} at {backup_path}")
            return True, backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for module {name}: {e}")
            return False, str(e)
    
    def restore_from_backup(self, backup_path: str, name: str, directory: str) -> bool:
        """
        Restore a module from a backup file
        
        :param backup_path: Path to the backup zip file
        :param name: Name of the module to restore
        :param directory: Directory containing the module (e.g. 'modules')
        :return: Success status
        """
        try:
            # Target directory for restoration
            target_dir = os.path.join(self.__root_dir, directory)
            module_dir = os.path.join(target_dir, name)
            
            # Check if the backup file exists
            if not os.path.exists(backup_path):
                logger.error(f"Backup file {backup_path} not found")
                return False
                
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the backup to the temp directory
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Remove existing module directory if it exists
                if os.path.exists(module_dir):
                    shutil.rmtree(module_dir)
                
                # Copy the extracted files to the target directory
                extracted_module_dir = os.path.join(temp_dir, name)
                if not os.path.exists(extracted_module_dir):
                    # The module might be at the root of the zip
                    shutil.copytree(temp_dir, module_dir)
                else:
                    shutil.copytree(extracted_module_dir, module_dir)
            
            logger.info(f"Restored module {name} from backup {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore module {name} from backup: {e}")
            return False
    
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
                return a0
            
            # Delete older backups
            deleted_count = 0
            for backup in backups[keep_count:]:
                if self.delete_backup(backup):
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clean up old backups for {name}: {e}")
            return 0
