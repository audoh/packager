import math
import os
import shutil
import tempfile
from io import FileIO
from typing import List, Optional, Set, Tuple
from urllib import parse as urlparse
from uuid import uuid4

import patoolib
import requests
from loguru import logger

from utils.files import remove

_CHUNK_SIZE = 1024
_TEMP_DIR = os.path.join(tempfile.gettempdir(), "packman")


class Operation:
    new_paths: Set[str] = set()
    temp_paths: Set[str] = set()
    last_path: Optional[str] = None
    backups: List[Tuple[str, str]] = []

    def __init__(self):
        os.makedirs(_TEMP_DIR, exist_ok=True)

    def __del__(self):
        for path in self.temp_paths:
            try:
                remove(path)
            except Exception as exc:
                logger.warning(
                    f"failed to discard temporary path {path}: {exc}")
                continue

    def get_temp_path(self, ext: str = "") -> None:
        name = uuid4()
        path = os.path.join(_TEMP_DIR, f"{name}{ext}")
        self.temp_paths.add(path)
        self.last_path = path
        return path

    def copy_file(self, src: str, dest: str) -> None:
        if dest not in self.temp_paths and os.path.exists(dest):
            backup = self.get_temp_path()
            logger.debug(f"backing up {dest} to {backup}")
            shutil.copy2(dest, backup)
            self.backups.append((backup, dest))

        logger.debug(f"copying {src} to {dest}")
        shutil.copy2(src, dest)
        self.new_paths.add(dest)

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

    def discard(self, path: str) -> None:
        logger.debug(f"discarding {path}")
        if path not in self.temp_paths:
            return
        remove(path)
        self.temp_paths.remove(path)

    def restore(self) -> bool:
        errors = False

        for path in self.new_paths:
            logger.debug(f"cleaning up {path}")
            try:
                remove(path)
            except Exception as exc:
                logger.error(f"failed to clean up file: {path}")
                logger.exception(exc)
                errors = True

        for src, dest in self.backups:
            logger.debug(f"restoring {src} to {dest}")
            try:
                shutil.copy2(src, dest)
            except Exception as exc:
                logger.error(f"failed to restore file: {dest}")
                logger.exception(exc)
                errors = True
                continue

        return errors
