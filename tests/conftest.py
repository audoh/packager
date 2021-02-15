import os
import shutil
from typing import Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
from packman import Packman


@pytest.fixture(scope="function")
def packman(mock_path: str) -> Generator[Packman, None, None]:
    yield Packman(
        root_dir=os.path.join(mock_path, "mockgame"),
        config_dir=os.path.join(mock_path, "mockconfigs"),
        manifest_path=os.path.join(mock_path, "mockgame", "manifest.json"),
    )


@pytest.fixture(scope="function", autouse=True)
def mock_path() -> Generator[str, None, None]:
    mock_path = os.path.join("tests_tmp", str(uuid4()))
    root_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    shutil.copytree(root_path, mock_path)
    yield mock_path
    shutil.rmtree(mock_path)


@pytest.fixture(scope="function", autouse=True)
def temp_path() -> Generator[str, None, None]:
    mock_path = os.path.join("tmp", str(uuid4()))
    with patch("tempfile.tempdir", mock_path):
        yield mock_path
    try:
        shutil.rmtree(mock_path)
    except FileNotFoundError:
        pass


def file_path_generator(mock_path: str) -> Generator[str, None, None]:
    while True:
        yield os.path.join(mock_path, str(uuid4()))


@pytest.fixture(scope="function")
def file_paths(mock_path: str) -> Generator[Generator[str, None, None], None, None]:
    yield file_path_generator(mock_path)
