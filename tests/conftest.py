import os
import shutil
from typing import Generator

import pytest
from packman import Packman


@pytest.fixture(scope="function")
def packman(mock_files: str) -> Generator[Packman, None, None]:
    yield Packman(
        root_dir=os.path.join(mock_files, "mockgame"),
        config_dir=os.path.join(mock_files, "mockconfigs"),
        manifest_path=os.path.join(mock_files, "mockgame", "manifest.json"),
    )


@pytest.fixture(scope="function", autouse=True)
def mock_files() -> Generator[str, None, None]:
    root_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    try:
        shutil.rmtree("/test")
    except FileNotFoundError:
        pass
    shutil.copytree(root_path, "/test")
    yield "/test"
