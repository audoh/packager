import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import TracebackType
from typing import Callable, Optional, Tuple, Type
from uuid import uuid4

import appdirs
import win32api
import win32con
from loguru import logger

FILE_ATTRIBUTE_HIDDEN = win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
FILE_ATTRIBUTE_UNWRITEABLE = FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_READONLY
REMOVE_FUNCS = (os.remove, os.rmdir, os.unlink)

_TEMP_DIR: Optional[str] = None
_BACKUP_DIR: Optional[str] = None


def temp_dir() -> str:
    global _TEMP_DIR
    if _TEMP_DIR is None:
        _TEMP_DIR = os.path.join(tempfile.gettempdir(), "packman")
    return _TEMP_DIR


def temp_path(ext: str = "") -> str:
    return os.path.join(temp_dir(), f"{uuid4()}{ext}")


def backup_dir() -> str:
    global _BACKUP_DIR
    if _BACKUP_DIR is None:
        _BACKUP_DIR = os.path.join(appdirs.user_state_dir(appname="packman"), "backups")
    return _BACKUP_DIR


def backup_path(src: str) -> str:
    key_bytes = bytes(src, "utf-8")
    key_md5 = hashlib.md5(key_bytes)
    key_md5_str = key_md5.hexdigest()
    return os.path.join(backup_dir(), key_md5_str)


def checksum(path: str) -> str:
    hash = hashlib.sha256()
    with open(path, "rb") as fp:
        for b in fp:
            hash.update(b)
    return f"{hash.name}:{hash.hexdigest()}"


def is_hidden(path: str) -> bool:
    if os.name == "nt":
        attribute = win32api.GetFileAttributes(path)
        return bool(attribute & FILE_ATTRIBUTE_HIDDEN)
    else:
        return os.path.basename(path).startswith(".")


def _nt_error_handler(
    source: Callable[[str], None],
    path: str,
    error: Tuple[Type[BaseException], BaseException, TracebackType],
) -> None:
    type, _, _ = error
    if issubclass(type, FileNotFoundError):
        return

    attributes = win32api.GetFileAttributes(path)
    if attributes & FILE_ATTRIBUTE_UNWRITEABLE:
        win32api.SetFileAttributes(path, attributes & ~FILE_ATTRIBUTE_UNWRITEABLE)
        source(path)
        if source not in REMOVE_FUNCS:
            try:
                win32api.SetFileAttributes(path, attributes)
            except FileNotFoundError:
                logger.warning(f"fn {source} also removes the file")
            except Exception:
                return


def _noop_error_handler(
    source: Callable[[str], None],
    path: str,
    error: Tuple[Type[BaseException], BaseException, TracebackType],
) -> None:
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
    logger.trace(f"removing file {path}", backtrace=True)
    try:
        os.remove(path)
    except OSError:
        type, err, trace = sys.exc_info()
        assert type is not None
        assert err is not None
        assert trace is not None
        _error_handler(os.remove, path, (type, err, trace))


def remove_path(path: str) -> None:
    try:
        if os.path.isdir(path):
            logger.trace(f"removing tree {path}")
            shutil.rmtree(path, onerror=_error_handler)
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
