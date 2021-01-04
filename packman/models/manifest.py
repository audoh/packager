import json
import os
import shutil
from typing import Dict, List

from packman.utils.files import checksum, remove_path
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

    @property
    def modified_files(self) -> List[str]:
        return self.file_map.keys()

    def update_file_map(self) -> None:
        file_map: Dict[str, List[str]] = {}
        for name, package in self.packages.items():
            for file in package.files:
                if file not in file_map:
                    file_map[file] = [name]
                else:
                    file_map[file].append(name)
        for file in self.file_map:
            if file not in file_map:
                if file in self.original_files:
                    shutil.copy2(self.original_files[file], file)
                    remove_path(self.original_files[file])
                    del self.original_files[file]
                else:
                    remove_path(file)
        self.file_map = file_map

    def update_checksums(self) -> None:
        for package in self.packages.values():
            package.update_checksums()

    def write_json(self, path: str) -> None:
        self.update_file_map()
        self.update_checksums()
        with open(path, "w") as fp:
            fp.write(self.json(indent=2))

    @staticmethod
    def from_path(path: str) -> "Manifest":
        if os.path.exists(path):
            with open(path, "r") as fp:
                raw = json.load(fp)
                manifest = Manifest(**raw)
        else:
            manifest = Manifest()
        return manifest
