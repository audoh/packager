import os
import re
import shutil
import tempfile
from sys import stderr
from typing import Any, Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
from loguru import logger
from packman import Packman
from pytest import Item

# Set up logger with all logs because pytest itself suppresses output
logger.remove()
logger.add(stderr, level="TRACE")


def _copytree(src: str, dest: str) -> None:
    logger.debug(f"copying {src=} to {dest=}")
    try:
        shutil.copytree(src, dest)
    except FileNotFoundError:
        pass


def _rmtree(path: str) -> None:
    logger.debug(f"cleaning up {path=}")
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


@pytest.fixture(scope="function", autouse=True)
def mock_path() -> Generator[str, None, None]:
    """ Copies and returns mock folder structure from fixtures. """
    mock_path = os.path.join("tests_tmp", str(uuid4()))
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    _copytree(fixture_path, mock_path)
    logger.debug(f"generated {mock_path=}")
    yield mock_path
    _rmtree(mock_path)


@pytest.fixture(scope="function", autouse=True)
def temp_path() -> Generator[str, None, None]:
    """ Patch apparent system temp dir to a unique one to avoid cross-test interactions. """
    mock_temp_path = os.path.join("tmp", str(uuid4()))
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "temp_files")
    _copytree(fixture_path, mock_temp_path)
    logger.debug(f"patching {mock_temp_path=}")
    with patch("tempfile.tempdir", mock_temp_path):
        assert tempfile.tempdir == mock_temp_path
        yield mock_temp_path
    _rmtree(mock_temp_path)


def _file_path_generator(root_path: str) -> Generator[str, None, None]:
    while True:
        path = os.path.join(root_path, str(uuid4()))
        logger.debug(f"generated {path=}")
        yield path


@pytest.fixture(scope="function")
def file_paths(mock_path: str) -> Generator[Generator[str, None, None], None, None]:
    """ Returns a generator which can be used to get file paths for creating test files. """
    yield _file_path_generator(mock_path)


@pytest.fixture(scope="function")
def packman(mock_path: str) -> Generator[Packman, None, None]:
    """Generates packman using the mock folder structure. """
    logger.debug(f"generating packman instance at {mock_path}")
    yield Packman(
        root_dir=os.path.join(mock_path, "mockgame"),
        config_dir=os.path.join(mock_path, "mockconfigs"),
        manifest_path=os.path.join(mock_path, "mockgame", "manifest.json"),
    )


def _str(val: Any) -> str:
    if isinstance(val, bytes):
        return str(val, encoding="utf-8")
    return str(val)


def pytest_make_parametrize_id(config, val, argname):
    val_str = repr(val).replace("-", "--")
    return f"{argname}: {val_str}"


def pytest_itemcollected(item: Item) -> None:
    nodeid: str = item._nodeid

    # Check if item is parameterised
    args_idx = nodeid.rfind("[")
    if args_idx == -1:
        return

    # Split up "function[val1-val2]"" into "function" and "val1-val2"
    args_idx_end = nodeid.find("]", args_idx)
    name = nodeid[:args_idx] + nodeid[args_idx_end + 1 :]
    args_str = nodeid[args_idx + 1 : args_idx_end]

    args_str = re.sub(r"([^-])-([^-])", r"\1, \2", args_str)
    item._nodeid = f"{name} ({args_str})"
