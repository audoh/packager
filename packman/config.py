import os
from enum import Enum
from sys import stderr

import yaml
from loguru import logger
from pydantic.main import BaseModel

_dir = os.path.dirname(__file__)
_dir_to_root = ".."
_root = os.path.abspath(os.path.join(_dir, _dir_to_root))

_DEFAULT_DEFINITION_PATH = "definitions/ksp"


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class GitConfig(BaseModel):
    url: str = "https://github.com/audoh/packman.git"
    definition_path: str = _DEFAULT_DEFINITION_PATH


class Config(BaseModel):
    root_path: str = ""
    manifest_path: str = "packman.json"
    definition_path: str = os.path.abspath(
        os.path.join(_root, _DEFAULT_DEFINITION_PATH)
    )
    git: GitConfig = GitConfig()
    log_level: LogLevel = LogLevel(os.environ.get("PACKMAN_LOGGING", "CRITICAL"))

    def configure_logger(self) -> None:
        # Set up logger
        logger.remove()
        logger.add(stderr, level=self.log_level)


def get_config_path() -> str:
    return os.environ.get("PACKMAN_CONFIG_FILE", "packman.yml")


def read_config(path: str = get_config_path()) -> Config:
    try:
        with open(path) as fp:
            raw = yaml.load(fp, Loader=yaml.SafeLoader)
            if raw is None:
                return Config()
            cfg = Config(**raw)
            return cfg
    except FileNotFoundError:
        return Config()
