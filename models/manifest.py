from typing import Any, Dict, List

from pydantic import BaseModel


class Package(BaseModel):
    version: str
    files: List[str]


class Manifest(BaseModel):
    version = 1
    packages: Dict[str, Package] = []
    file_map: Dict[str, List[str]] = {}

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        self.update_file_map()
        return super().dict(*args, **kwargs)

    def update_file_map(self) -> None:
        file_map: Dict[str, List[str]] = {}
        for name, package in self.packages.items():
            for file in package.files:
                if file not in file_map:
                    file_map[file] = [name]
                else:
                    file_map[file].append(name)
        self.file_map = file_map
