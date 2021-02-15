import os
import shutil
from typing import Generator

import pytest
from packman import Packman


@pytest.fixture(scope="function")
def packman() -> Generator[Packman, None, None]:
    yield Packman(
        root_dir="/test/mockgame",
        config_dir="/test/mockconfigs",
        manifest_path="/test/mockgame/manifest.json",
    )


@pytest.fixture(scope="function", autouse=True)
def mock_files() -> Generator[None, None, None]:
    root_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    try:
        shutil.rmtree("/test")
    except FileNotFoundError:
        pass
    shutil.copytree(root_path, "/test")
    yield
