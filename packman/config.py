import os

_DEFAULT_CFG_PATH = "cfg"

CFG_PATH = os.environ.get("PACKMAN_CONFIG_FILE", _DEFAULT_CFG_PATH)
MANIFEST_PATH = os.environ.get("PACKMAN_MANIFEST_FILE", "packman.json")
REPO_URL = os.environ.get("PACKMAN_GIT_URL",
                          "https://github.com/audoh/packman.git")
REPO_CFG_PATH = os.environ.get("PACKMAN_GIT_CONFIG_FILE", _DEFAULT_CFG_PATH)
