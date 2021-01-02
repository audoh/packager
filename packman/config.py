import os

_DEFAULT_CFG_PATH = "cfg"

_dir = os.path.dirname(__file__)
_dir_to_root = ".."
_root = os.path.normpath(os.path.join(_dir, _dir_to_root))


DEFAULT_CONFIG_PATH = os.environ.get(
    "PACKMAN_CONFIG_FILE", os.path.normpath(
        os.path.join(_root, _DEFAULT_CFG_PATH)))
DEFAULT_MANIFEST_PATH = os.environ.get("PACKMAN_MANIFEST_FILE", "packman.json")
DEFAULT_GIT_URL = os.environ.get("PACKMAN_GIT_URL",
                                 "https://github.com/audoh/packman.git")
DEFAULT_REPO_CONFIG_PATH = os.environ.get(
    "PACKMAN_GIT_CONFIG_FILE", _DEFAULT_CFG_PATH)
