import hashlib
import os
import shutil
from typing import Iterable

from packman.models.package_source import PackageVersion
from packman.utils.files import temp_dir
from packman.utils.operation import Operation


class Cache:
    def __init__(self, name: str) -> None:
        self.name = name

    def fetch_version(self, version: str, operation: Operation) -> None:
        cache_path = self.get_path(version, ".zip")
        if not os.path.exists(cache_path):
            raise Exception("not found")
        operation.extract_archive(cache_path)

    def get_versions(self) -> Iterable[str]:
        self._raise_unsupported_error()

    def add_package(self, version_info: PackageVersion, package_path: str) -> None:
        version = version_info.version
        cache_path = self.get_path(version)
        try:
            os.remove(cache_path)
        except FileNotFoundError:
            ...
        shutil.make_archive(cache_path, "zip", package_path)

    def get_path(self, version: str, ext: str = "") -> str:
        key_bytes = bytes(f"{self.name}{version}", "utf-8")
        key_md5 = hashlib.md5(key_bytes)
        key_md5_str = key_md5.hexdigest()
        file = f"cache_{key_md5_str}{ext}"
        return os.path.join(temp_dir(), file)
