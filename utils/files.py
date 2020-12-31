import os
import shutil
import tempfile
from types import TracebackType
from typing import Callable, Tuple, Type
from uuid import uuid4

import win32api
import win32con
from loguru import logger

FILE_ATTRIBUTE_HIDDEN = win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
FILE_ATTRIBUTE_UNWRITEABLE = FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_READONLY
REMOVE_FUNCS = (os.remove, os.rmdir, os.unlink)


def temp_path() -> str:
    return os.path.join(tempfile.tempdir, "packman", str(uuid4()))


def is_hidden(path: str) -> bool:
    if os.name == "nt":
        attribute = win32api.GetFileAttributes(path)
        return bool(attribute & FILE_ATTRIBUTE_HIDDEN)
    else:
        return os.path.basename(path).startswith(".")


def _nt_error_handler(source: Callable[[str], None], path: str, error: Tuple[Type[BaseException], BaseException, TracebackType]) -> None:
    attributes = win32api.GetFileAttributes(path)
    if (attributes & FILE_ATTRIBUTE_UNWRITEABLE):
        win32api.SetFileAttributes(
            path, attributes & ~FILE_ATTRIBUTE_UNWRITEABLE)
        source(path)
        if source not in REMOVE_FUNCS:
            try:
                win32api.SetFileAttributes(path, attributes)
            except FileNotFoundError:
                logger.warning(f"fn {source} also removes the file")
            except:
                return


def _noop_error_handler(source: Callable[[str], None], path: str, error: Tuple[Type[BaseException], BaseException, TracebackType]) -> None:
    return


def remove(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(
                path, onerror=_nt_error_handler if os.name == "nt" else _noop_error_handler)
        else:
            os.remove(path)
    except FileNotFoundError:
        ...
    dir = os.path.dirname(path)
    try:
        siblings = os.listdir(dir)
    except FileNotFoundError:
        ...
    else:
        if not any(siblings):
            remove(dir)
