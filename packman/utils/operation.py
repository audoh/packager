import math
import os
import shutil
from io import FileIO
from types import TracebackType
from typing import Dict, Optional, Set, Type
from urllib import parse as urlparse

import patoolib
import requests
from loguru import logger
from packman.utils.files import remove_file, remove_path, temp_dir, temp_path
from packman.utils.uninterruptible import uninterruptible

_CHUNK_SIZE = 1024


class Operation:
    new_paths: Set[str] = set()
    temp_paths: Set[str] = set()
    last_path: Optional[str] = None
    backups: Dict[str, str] = {}

    def __init__(self):
        os.makedirs(temp_dir(), exist_ok=True)

    def close(self) -> None:
        for path in self.temp_paths:
            try:
                remove_path(path)
            except Exception as exc:
                logger.warning(
                    f"failed to discard temporary path {path}: {exc}")
                continue

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "Operation":
        return self

    def __exit__(self, exception_type: Type, exception_value: BaseException, traceback: TracebackType) -> None:
        if exception_type is None:
            self.close()
        else:
            with uninterruptible():
                self.abort()

    def get_temp_path(self, ext: str = "") -> None:
        path = temp_path(ext=ext)
        self.temp_paths.add(path)
        self.last_path = path
        return path

    def backup_file(self, path: str) -> None:
        backup = self.get_temp_path()
        logger.debug(f"backing up {path} to {backup}")
        shutil.copy2(path, backup)
        self.backups[path] = backup

    def should_backup_file(self, path: str) -> bool:
        return path not in self.temp_paths and path not in self.backups and path not in self.new_paths and os.path.exists(path)

    def copy_file(self, src: str, dest: str) -> None:
        if self.should_backup_file(dest):
            self.backup_file(dest)

        logger.debug(f"copying {src} to {dest}")
        shutil.copy2(src, dest)
        self.new_paths.add(dest)

    def remove_file(self, path: str) -> None:
        if self.should_backup_file(path):
            self.backup_file(path)
        logger.debug(f"deleting {path}")
        remove_file(path)
        if path in self.temp_paths:
            self.temp_paths.remove(path)

    def download_file(self, url: str, ext: Optional[str] = "") -> str:
        if ext is None:
            parsed_url = urlparse.urlparse(url)
            url_path = parsed_url.path
            extsep_idx = url_path.rfind(".")
            if extsep_idx != -1:
                ext = url_path[extsep_idx:]
            else:
                ext = ""
        res = requests.get(url)
        path = self.get_temp_path(ext=ext)
        logger.debug(f"downloading {url} to {path}")
        with open(path, "bw") as file:
            size = int(res.headers["content-length"])
            chunks = math.ceil(size / _CHUNK_SIZE)

            file: FileIO
            for chunk, i in zip(res.iter_content(chunk_size=_CHUNK_SIZE), range(chunks)):
                # logger.info(f"{i / chunks}")
                file.write(chunk)
        return path

    def extract_archive(self, path: str) -> str:
        dir = self.get_temp_path()
        logger.debug(f"extracting {path} to {dir}")
        patoolib.extract_archive(path, outdir=dir, verbosity=-1)
        return dir

    def restore(self) -> bool:
        errors = False

        for path in self.new_paths:
            logger.debug(f"cleaning up {path}")
            try:
                remove_path(path)
            except Exception as exc:
                logger.error(f"failed to clean up file: {path}")
                logger.exception(exc)
                errors = True

        for dest, src in self.backups.items():
            logger.debug(f"restoring {src} to {dest}")
            try:
                dest_dir = os.path.dirname(dest)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src, dest)
            except Exception as exc:
                logger.error(f"failed to restore file: {dest}")
                logger.exception(exc)
                errors = True
                continue

        return errors

    def abort(self) -> bool:
        """
        Shorthand for restore and close.
        """
        logger.debug("aborting operation")
        errors = self.restore()
        self.close()
        return errors
