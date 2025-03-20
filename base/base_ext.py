from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtensionInfo:
    name: str
    author: str
    version: str
    src_url: Optional[str] = None


class BaseExtension(ABC):
    """
    Class to extend ModuleLoader functionality.
    Can modify module object before stage2 initialization
    Useful for implementing features for every module
    """

    @property
    @abstractmethod
    def extension_info(self) -> ExtensionInfo:
        """
        Extension info. Must be set
        
        :return: ExtensionInfo dataclass object
        """

    @abstractmethod
    def on_module(self, obj):
        """
        Main method where extension must edit module object

        :param obj: BaseModule object
        """
