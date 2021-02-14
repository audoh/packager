import os
from sys import stderr

from loguru import logger

_DEFAULT_CFG_PATH = "configs/ksp"

_dir = os.path.dirname(__file__)
_dir_to_root = ".."
_root = os.path.normpath(os.path.join(_dir, _dir_to_root))

DEFAULT_CONFIG_PATH = os.environ.get(
    "PACKMAN_CONFIG_FILE", os.path.normpath(os.path.join(_root, _DEFAULT_CFG_PATH))
)
DEFAULT_MANIFEST_PATH = os.environ.get("PACKMAN_MANIFEST_FILE", "packman.json")
DEFAULT_GIT_URL = os.environ.get(
    "PACKMAN_GIT_URL", "https://github.com/audoh/packman.git"
)
DEFAULT_REPO_CONFIG_PATH = os.environ.get("PACKMAN_GIT_CONFIG_FILE", _DEFAULT_CFG_PATH)
DEFAULT_ROOT_DIR = os.environ.get("PACKMAN_ROOT_DIR", "")

REQUEST_TIMEOUT = float(os.environ.get("PACKMAN_REQUEST_TIMEOUT", "30"))
REQUEST_CHUNK_SIZE = int(os.environ.get("PACKMAN_REQUEST_CHUNKSZ", 500 * 1000))

# Set up logger
logger.remove()
logger.add(stderr, level=os.environ.get("PACKMAN_LOGGING", "CRITICAL"))
