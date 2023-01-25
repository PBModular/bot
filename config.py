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
    enable_db: bool
    db_url: str


# Load from YAML
if CONF_FILE not in os.listdir('./'):
    shutil.copy('config.example.yaml', CONF_FILE)

config = Config.from_yaml_file(CONF_FILE)
