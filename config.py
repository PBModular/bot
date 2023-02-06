from dataclasses import dataclass
from dataclass_wizard import YAMLWizard
import os
import shutil

CONF_FILE = 'config.yaml'


@dataclass
class Config(YAMLWizard):
    token: str
    language: str
    fallback_language: str
    update_deps_at_load: bool
    enable_db: bool
    db_url: str
    db_file_name: str


# Load from YAML
if CONF_FILE not in os.listdir('./'):
    shutil.copy('config.example.yaml', CONF_FILE)

config = Config.from_yaml_file(CONF_FILE)
