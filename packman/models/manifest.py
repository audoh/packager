import json
import os
import shutil
from typing import Any, Dict, List, Set

from packman.utils.files import checksum, remove_path
from packman.utils.progress import (ProgressCallback, StepProgress,
                                    progress_noop)
from pydantic import BaseModel


class ManifestPackage(BaseModel):
    version: str
    files: List[str]
    checksums: Dict[str, str] = {}

    def update_checksums(self) -> None:
        self.checksums = {}
        for file in self.files:
            self.checksums[file] = checksum(file)


class Manifest(BaseModel):
    version = 1
    packages: Dict[str, ManifestPackage] = {}
    file_map: Dict[str, List[str]] = {}
    original_files: Dict[str, str] = {}
    orphaned_files: Set[str] = set()

    _file_checksums: Dict[str, Set[str]] = {}

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._update_checksum_map()

    @property
    def modified_files(self) -> List[str]:
        return self.file_map.keys()

    def _update_checksum_map(self) -> None:
        for package in self.packages.values():
            for file, chk in package.checksums.items():
                if file in self._file_checksums:
                    self._file_checksums[file].add(chk)
                else:
                    self._file_checksums[file] = set((chk,))

    def deepcopy(self) -> "Manifest":
        return Manifest(**self.dict())

    def cleanup_files(self, remove_orphans: bool = False) -> None:
        """
        Deletes files that have been removed from the manifest since the last cleanup, or since the Manifest was instantiated if no previous cleanups.
        """
        new_file_map: Dict[str, List[str]] = {}
        for name, package in self.packages.items():
            for file in package.files:
                if file in self.orphaned_files:
                    self.orphaned_files.remove(file)
                if file not in new_file_map:
                    new_file_map[file] = [name]
                else:
                    new_file_map[file].append(name)

        for file in self.file_map:
            if file not in new_file_map:
                curr_chk = checksum(file)
                if remove_orphans or any(chk == curr_chk for chk in self._file_checksums[file]):
                    if file in self.original_files:
                        shutil.copy2(self.original_files[file], file)
                        remove_path(self.original_files[file])
                        del self.original_files[file]
                    else:
                        remove_path(file)
                else:
                    self.orphaned_files.add(file)

        if remove_orphans:
            for file in self.orphaned_files:
                remove_path(self.original_files[file])

        self.file_map = new_file_map

    def update_checksums(self) -> None:
        for package in self.packages.values():
            package.update_checksums()
        self._update_checksum_map()

    def write_json(self, path: str) -> None:
        path_dir = os.path.normpath(os.path.dirname(path))
        if path_dir != ".":
            os.makedirs(path_dir, exist_ok=True)
        with open(path, "w") as fp:
            if path_dir != ".":
                clone = self.deepcopy()
                clone.update_path_root(path_dir)
                fp.write(clone.json(indent=2))
            else:
                fp.write(self.json(indent=2))

    def update_path_root(self, root: str) -> None:
        for package in self.packages.values():
            new_files: List[str] = []
            for file in package.files:
                new_file = os.path.relpath(file, root)
                new_files.append(new_file)
            package.files = new_files

            new_checksums: Dict[str, str] = {}
            for file, chk in package.checksums.items():
                new_file = os.path.relpath(file, root)
                new_checksums[new_file] = chk
            package.checksums = new_checksums

        new_file_map: Dict[str, List[str]] = {}
        for file, packages in self.file_map.items():
            new_file = os.path.relpath(file, root)
            new_file_map[new_file] = packages
        self.file_map = new_file_map

        new_orphaned_files: Set[str] = set()
        for file in self.orphaned_files:
            new_file = os.path.relpath(file, root)
            new_orphaned_files.add(new_file)
        self.orphaned_files = new_orphaned_files

        new_original_files: Dict[str, str] = {}
        for file, value in self.original_files.items():
            new_file = os.path.relpath(file, root)
            new_original_files[file] = value
        self.original_files = new_original_files

        self._update_checksum_map()

    def update_files(self, path: str, on_progress: ProgressCallback = progress_noop, remove_orphans: bool = False) -> None:
        """
        Updates the manifest file and cleans up any files that are no longer in the manifest.
        """

        # TODO fix a bug where when the manifest is saved, package checksums are updated, so orphaned files effectively become un-orphaned

        step_progress = StepProgress.from_step_count(
            step_count=3, on_progress=on_progress)
        self.cleanup_files(remove_orphans=remove_orphans)
        step_progress.advance()
        self.update_checksums()
        step_progress.advance()
        self.write_json(path=path)
        step_progress.advance()

    @staticmethod
    def from_path(path: str) -> "Manifest":
        """
        Creates a new instance of a Manifest, loaded from the given path. If the path does not exist, creates an empty Manifest.
        """
        if os.path.exists(path):
            with open(path, "r") as fp:
                raw = json.load(fp)
                manifest = Manifest(**raw)

                path_dir = os.path.dirname(path)
                if os.path.normpath(path_dir) != ".":
                    manifest.update_path_root(os.path.relpath(".", path_dir))

        else:
            manifest = Manifest()
        return manifest
