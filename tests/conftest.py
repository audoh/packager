import os
import shutil
from itertools import count
from sys import stderr
from typing import Any, Dict, Generator, List
from unittest.mock import patch
from uuid import uuid4

import pytest
from loguru import logger
from packman import Packman
from pytest import Item

# Set up logger with all logs because pytest itself suppresses output
logger.remove()
logger.add(stderr, level="TRACE")


@pytest.fixture(scope="function", autouse=True)
def mock_path() -> Generator[str, None, None]:
    """ Copies and returns mock folder structure from fixtures. """
    mock_path = os.path.join("tests_tmp", str(uuid4()))
    root_path = os.path.join(os.path.dirname(__file__), "fixtures", "files")
    shutil.copytree(root_path, mock_path)
    logger.debug(f"generated {mock_path=}")
    yield mock_path
    logger.debug(f"cleaning up {mock_path=}")
    shutil.rmtree(mock_path)


@pytest.fixture(scope="function", autouse=True)
def temp_path() -> Generator[str, None, None]:
    """ Patch apparent system temp dir to a unique one to avoid cross-test interactions. """
    mock_temp_path = os.path.join("tmp", str(uuid4()))
    logger.debug(f"patching {mock_temp_path=}")
    with patch("tempfile.tempdir", mock_temp_path):
        yield mock_temp_path
    try:
        logger.debug(f"cleaning up {mock_temp_path=}")
        shutil.rmtree(mock_temp_path)
    except FileNotFoundError:
        pass


def _file_path_generator(mock_path: str) -> Generator[str, None, None]:
    while True:
        path = os.path.join(mock_path, str(uuid4()))
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

    args_dict: Dict[str, str] = {}
    for mark in item.iter_markers("parametrize"):
        names_raw = mark.args[0]
        names: List[str] = (
            [name.strip() for name in names_raw.split(",")]
            if isinstance(names_raw, str)
            else list(names_raw)
        )

        param_sets = list(mark.args[1])
        for param_name, param_index in zip(names, count(start=0)):
            # Find node's value for this param
            found_any = False
            longest_match: str = ""
            value: str = ""
            for param_set in param_sets:
                # Get param string val
                param = (
                    param_set[param_index]
                    if isinstance(param_set, (tuple, list))
                    else param_set
                )
                param_str = _str(param)

                # Find longest value that args_str starts with
                if len(longest_match) < len(param_str) and args_str.startswith(
                    param_str
                ):
                    found_any = True
                    longest_match = param_str
                    value = repr(param)

            if not found_any:
                raise ValueError(
                    f"failed to resolve {param_name=} to param value from {param_sets=}"
                )

            args_str = args_str[len(longest_match) + 1 :]
            args_dict[param_name] = value

    args_str = ", ".join((f"{key}: {value}" for key, value in args_dict.items()))
    item._nodeid = f"{name} ({args_str})"
