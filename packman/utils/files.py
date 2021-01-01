import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Callable, Optional, Tuple, Type
from uuid import uuid4

import win32api
import win32con
from loguru import logger

FILE_ATTRIBUTE_HIDDEN = win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
FILE_ATTRIBUTE_UNWRITEABLE = FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_READONLY
REMOVE_FUNCS = (os.remove, os.rmdir, os.unlink)

_TEMP_DIR: Optional[str] = None


def temp_dir() -> str:
    global _TEMP_DIR
    if _TEMP_DIR is None:
        _TEMP_DIR = os.path.join(tempfile.gettempdir(), "packman")
    return _TEMP_DIR


def temp_path(ext: str = "") -> str:
    return os.path.join(temp_dir(), f"{uuid4()}{ext}")


def is_hidden(path: str) -> bool:
    if os.name == "nt":
        attribute = win32api.GetFileAttributes(path)
        return bool(attribute & FILE_ATTRIBUTE_HIDDEN)
    else:
        return os.path.basename(path).startswith(".")


def _nt_error_handler(source: Callable[[str], None], path: str, error: Tuple[Type[OSError], OSError, TracebackType]) -> None:
    type, _, _ = error
    if type == FileNotFoundError:
        return

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


def _noop_error_handler(source: Callable[[str], None], path: str, error: Tuple[Type[OSError], OSError, TracebackType]) -> None:
    return


_error_handler = _nt_error_handler if os.name == "nt" else _noop_error_handler


def resolve_case(pathlike: str) -> str:
    """
    On case-insensitive file-systems, resolves the given path's casing to match the real file or folder it points to.
    """
    path = Path(pathlike)

    if not path.exists():
        raise FileNotFoundError(f"no such file or directory: {path}")

    parts = []
    while str(path) not in (path.anchor, "", "."):
        parent = path.parent
        child = path.name
        match: str = ""
        for file in os.scandir(parent):
            name = file.name
            if name == child:
                match = name
                break
            elif name.lower() == child.lower():
                match = name
        parts.append(match)
        path = parent

    anchor = str(path)
    if os.path.isabs(pathlike) or pathlike.startswith(anchor):
        parts.append(anchor)

    result = os.path.join(*parts[::-1])
    return result


def remove_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        _error_handler(os.remove, path, sys.exc_info())


def remove_path(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(
                path, onerror=_error_handler)
        else:
            remove_file(path)

    except FileNotFoundError:
        ...
    dir = os.path.dirname(path)
    try:
        siblings = os.listdir(dir)
    except FileNotFoundError:
        ...
    else:
        if not any(siblings):
            remove_path(dir)
