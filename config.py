from dataclasses import dataclass
from dataclass_wizard.mixins.yaml import YAMLWizard
import os
import shutil
from typing import Union

from dataclass_wizard import LoadMeta

CONF_FILE = "config.yaml"


@dataclass
class Config(YAMLWizard):
    token: str
    api_id: int
    api_hash: str
    language: str
    fallback_language: str
    update_deps_at_load: bool
    enable_db: bool
    db_url: str
    db_file_name: str
    owner: Union[int, str]

LoadMeta(case='AUTO').bind_to(Config)

# Load from YAML
if CONF_FILE not in os.listdir("./"):
    shutil.copy("config.example.yaml", CONF_FILE)

config = Config.from_yaml_file(CONF_FILE)
