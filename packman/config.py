import os

_DEFAULT_CFG_PATH = "cfg"

DEFAULT_CONFIG_PATH = os.environ.get("PACKMAN_CONFIG_FILE", _DEFAULT_CFG_PATH)
DEFAULT_MANIFEST_PATH = os.environ.get("PACKMAN_MANIFEST_FILE", "packman.json")
DEFAULT_GIT_URL = os.environ.get("PACKMAN_GIT_URL",
                                 "https://github.com/audoh/packman.git")
DEFAULT_REPO_CONFIG_PATH = os.environ.get(
    "PACKMAN_GIT_CONFIG_FILE", _DEFAULT_CFG_PATH)
