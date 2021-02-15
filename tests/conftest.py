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


@pytest.fixture(scope="session", autouse=True)
def mock_files() -> Generator[None, None, None]:
    root_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    shutil.copytree(root_path, "/test")
    yield
