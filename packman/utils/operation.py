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
from packman.utils.files import remove_file, remove_path, temp_dir, temp_path
from packman.utils.progress import ProgressCallback, StepProgress, progress_noop
from packman.utils.uninterruptible import uninterruptible
from pydantic import BaseModel


def _ensure_dir_exists(path: str) -> None:
    dirname = os.path.normpath(path)
    if dirname != ".":
        os.makedirs(dirname, exist_ok=True)


def _ensure_dir_exists_for_file(path: str) -> None:
    _ensure_dir_exists(os.path.dirname(path))


def _copy(src: str, dest: str) -> None:
    _ensure_dir_exists_for_file(dest)
    try:
        shutil.copy2(src, dest)
    except Exception:
        # TODO clean up
        ...


class OperationState(BaseModel):
    new_paths: Set[str] = set()
    temp_paths: Set[str] = set()
    last_path: Union[str, None] = None
    backups: Dict[str, str] = {}

    @staticmethod
    def _get_tmp_path(path: str) -> str:
        return f"{path}.tmp"

    @staticmethod
    def load(path: str) -> "OperationState":

        try:
            with open(path, "r") as fp:
                state = json.load(fp)
                return OperationState(**state)
        except Exception as exc:
            logger.exception(exc)
            tmp_path = OperationState._get_tmp_path(path)
            with open(tmp_path, "r") as fp:
                state = json.load(fp)
                return OperationState(**state)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            tmp_path = OperationState._get_tmp_path(path)
            shutil.copyfile(path, tmp_path)
        except FileNotFoundError:
            tmp_path = None
            pass
        with open(path, "w") as fp:
            text = self.json()
            fp.write(text)
        if tmp_path is not None:
            remove_path(tmp_path)

    @staticmethod
    def exists(path: str) -> bool:
        return os.path.exists(path) or os.path.exists(
            OperationState._get_tmp_path(path)
        )

    @staticmethod
    def remove(path: str) -> None:
        try:
            remove_path(path)
        except FileNotFoundError:
            return
        try:
            remove_path(OperationState._get_tmp_path(path))
        except FileNotFoundError:
            return


class StateFileExistsError(FileExistsError):
    pass


class Operation:
    _DEFAULT_KEY = "default"

    def __init__(
        self,
        key: str = _DEFAULT_KEY,
        on_restore_progress: ProgressCallback = progress_noop,
        state: Optional[OperationState] = None,
        *,
        request_timeout: float = 30,
        request_chunk_size: int = 500 * 1000,
    ):
        self.request_timeout = request_timeout
        self.request_chunk_size = request_chunk_size

        if state is None:
            self.new_paths: Set[str] = set()
            self.temp_paths: Set[str] = set()
            self.last_path: Optional[str] = None
            self.backups: Dict[str, str] = {}
        else:
            self.new_paths = state.new_paths
            self.temp_paths = state.temp_paths
            self.last_path = state.last_path
            self.backups = state.backups

        self.on_restore_progress = on_restore_progress

        os.makedirs(temp_dir(), exist_ok=True)

        self.state_path = None
        state_path = Operation._get_state_path(key=key)
        if state is None and OperationState.exists(state_path):
            raise StateFileExistsError(f"unable to create '{state_path}': file exists")
        self.state_path = state_path

    @staticmethod
    def _get_state_path(key: str) -> str:
        return os.path.join(temp_dir(), f"state_{key}.json")

    def _capture_state(self) -> OperationState:
        return OperationState(
            new_paths={os.path.abspath(path) for path in self.new_paths},
            temp_paths={os.path.abspath(path) for path in self.temp_paths},
            last_path=os.path.abspath(self.last_path)
            if self.last_path is not None
            else None,
            backups={
                os.path.abspath(key): os.path.abspath(value)
                for key, value in self.backups.items()
            },
        )

    def _update_state(self) -> None:
        state = self._capture_state()
        assert self.state_path is not None, "state_path must exist by now"
        state.save(self.state_path)

    @staticmethod
    def recover(
        key: str = _DEFAULT_KEY, on_restore_progress: ProgressCallback = progress_noop
    ) -> "Operation":
        path = Operation._get_state_path(key=key)
        state = OperationState.load(path)
        return Operation(key=key, on_restore_progress=on_restore_progress, state=state)

    def close(self) -> None:
        """
        Removes temporary files and cleans up any other temporary state.
        """

        for path in self.temp_paths:
            try:
                remove_path(path)
            except Exception as exc:
                logger.warning(f"failed to discard temporary path {path}: {exc}")
                continue
        if self.state_path is not None:
            try:
                OperationState.remove(self.state_path)
            except Exception as exc:
                logger.warning(
                    f"failed to discard state recovery file {self.state_path}: {exc}"
                )

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
        self._update_state()
        return path

    def backup_file(self, path: str) -> str:
        backup_path = self.get_temp_path()
        logger.debug(f"backing up {path} to {backup_path}")
        _copy(path, backup_path)
        self.backups[path] = backup_path
        self._update_state()
        return backup_path

    def should_backup_file(self, path: str) -> bool:
        return (
            # Don't back up our own files
            path not in self.temp_paths
            and path not in self.new_paths
            # Don't back up files already backed up
            and path not in self.backups
            and os.path.exists(path)
        )

    def write_file(self, path: str, content: Union[bytes, str]) -> None:
        if self.should_backup_file(path):
            self.backup_file(path)

        logger.debug(f"writing to {path}")
        _ensure_dir_exists_for_file(path)
        if isinstance(content, str):
            with open(path, "w") as fp:
                fp.write(content)
        else:
            with open(path, "wb") as fp:
                fp.write(content)
        self.new_paths.add(path)
        self._update_state()

    def copy_file(self, src: str, dest: str) -> None:
        if self.should_backup_file(dest):
            self.backup_file(dest)

        logger.debug(f"copying {src} to {dest}")
        _copy(src, dest)
        self.new_paths.add(dest)
        self._update_state()

    def remove_file(self, path: str) -> None:
        if self.should_backup_file(path):
            self.backup_file(path)
        logger.debug(f"deleting {path}")
        remove_file(path)
        if path in self.temp_paths:
            self.temp_paths.remove(path)
            self._update_state()

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
        res = requests.get(url, stream=True, timeout=self.request_timeout)
        res.raise_for_status()
        path = self.get_temp_path(ext=ext)
        logger.debug(f"downloading {url} to {path}")
        with open(path, "bw") as file:
            pending_size = int(res.headers["content-length"])
            downloaded_size = 0
            time = datetime.now()

            for chunk in res.iter_content(self.request_chunk_size):
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
        """
        Deletes all new files and restores all backups made since instantiation or the last restore.

        Returns True if errors were encountered during restore.
        """
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
                _copy(src, dest)
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
