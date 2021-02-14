import json
import os
import shutil
from datetime import datetime, timedelta
from types import TracebackType
from typing import Dict, Optional, Set, Type, Union
from urllib import parse as urlparse

import patoolib
import requests
from loguru import logger
from packman.config import REQUEST_CHUNK_SIZE, REQUEST_TIMEOUT
from packman.utils.files import remove_file, remove_path, temp_dir, temp_path
from packman.utils.progress import (ProgressCallback, StepProgress,
                                    progress_noop)
from packman.utils.uninterruptible import uninterruptible
from pydantic import BaseModel


class OperationState(BaseModel):
    temp_paths: Set[str]
    new_paths: Set[str]
    backups: Dict[str, str]
    last_path: Union[str, None]

    @staticmethod
    def from_json(path: str) -> "OperationState":
        with open(path, "r") as fp:
            state = json.load(fp)
            return OperationState(**state)


class Operation:
    def __init__(self, on_restore_progress: ProgressCallback = progress_noop):
        self.new_paths: Set[str] = set()
        self.temp_paths: Set[str] = set()
        self.last_path: Optional[str] = None
        self.backups: Dict[str, str] = {}
        self.on_restore_progress = on_restore_progress
        os.makedirs(temp_dir(), exist_ok=True)

    @staticmethod
    def recover(
        state: OperationState, on_restore_progress: ProgressCallback = progress_noop
    ) -> "Operation":
        op = Operation(on_restore_progress=on_restore_progress)
        op.new_paths = state.new_paths
        op.temp_paths = state.temp_paths
        op.last_path = state.last_path
        op.backups = state.backups
        return op

    def close(self) -> None:
        for path in self.temp_paths:
            try:
                remove_path(path)
            except Exception as exc:
                logger.warning(f"failed to discard temporary path {path}: {exc}")
                continue

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> "Operation":
        return self

    def __exit__(
        self,
        exception_type: Type,
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        if exception_type is None:
            self.close()
        else:
            with uninterruptible():
                logger.exception(exception_value)
                self.abort()

    def get_temp_path(self, ext: str = "") -> str:
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
        return (
            # Don't back up our own files
            path not in self.temp_paths
            and path not in self.new_paths
            and
            # Don't back up files already backed up
            path not in self.backups
            and os.path.exists(path)
        )

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

    def download_file(
        self,
        url: str,
        ext: Optional[str] = "",
        on_progress: ProgressCallback = progress_noop,
    ) -> str:
        update_interval = timedelta(milliseconds=400)

        if ext is None:
            parsed_url = urlparse.urlparse(url)
            url_path = parsed_url.path
            extsep_idx = url_path.rfind(".")
            if extsep_idx != -1:
                ext = url_path[extsep_idx:]
            else:
                ext = ""
        res = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        res.raise_for_status()
        path = self.get_temp_path(ext=ext)
        logger.debug(f"downloading {url} to {path}")
        with open(path, "bw") as file:
            pending_size = int(res.headers["content-length"])
            downloaded_size = 0
            time = datetime.now()

            for chunk in res.iter_content(REQUEST_CHUNK_SIZE):
                file.write(chunk)
                downloaded_size += len(chunk)

                now = datetime.now()
                if now - time >= update_interval:
                    on_progress(downloaded_size / pending_size)
                    time = now
        return path

    def extract_archive(self, path: str) -> str:
        dir = self.get_temp_path()
        logger.debug(f"extracting {path} to {dir}")
        patoolib.extract_archive(path, outdir=dir, verbosity=-1)
        return dir

    def restore(self, on_progress: Optional[ProgressCallback] = None) -> bool:
        # TODO handle power outage in the middle of installation or rollback
        if not on_progress:
            on_progress = self.on_restore_progress

        errors = False

        progress = StepProgress.from_step_count(
            step_count=len(self.new_paths) + len(self.backups), on_progress=on_progress
        )
        on_progress(0.0)

        for path in self.new_paths:
            logger.debug(f"cleaning up {path}")
            try:
                remove_path(path)
                progress.advance()
            except Exception as exc:
                logger.error(f"failed to clean up file: {path}")
                logger.exception(exc)
                errors = True

        for dest, src in self.backups.items():
            logger.debug(f"restoring {src} to {dest}")
            try:
                dest_dir = os.path.normpath(os.path.dirname(dest))
                if dest_dir != ".":
                    os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(src, dest)
                progress.advance()
            except Exception as exc:
                logger.error(f"failed to restore file: {dest}")
                logger.exception(exc)
                errors = True
                continue

        on_progress(1.0)

        return errors

    def abort(self, on_progress: Optional[ProgressCallback] = None) -> bool:
        """
        Shorthand for restore and close.
        """
        logger.debug("aborting operation")
        errors = self.restore(on_progress=on_progress)
        self.close()
        return errors
