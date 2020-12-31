import json
import os
from typing import Any, Dict, List

from packman.utils.files import remove_path
from pydantic import BaseModel


class ManifestPackage(BaseModel):
    version: str
    files: List[str]


class Manifest(BaseModel):
    version = 1
    packages: Dict[str, ManifestPackage] = {}
    file_map: Dict[str, List[str]] = {}

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
                remove_path(file)
        self.file_map = file_map

    def write_json(self, path: str) -> None:
        self.update_file_map()
        with open(path, "w") as fp:
            fp.write(self.json())

    @staticmethod
    def from_path(path: str) -> "Manifest":
        if os.path.exists(path):
            with open(path, "r") as fp:
                raw = json.load(fp)
                manifest = Manifest(**raw)
        else:
            manifest = Manifest()
        return manifest
