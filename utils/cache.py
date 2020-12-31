import hashlib
import os
import shutil
import tempfile
from typing import Iterable

from models.package_source import PackageVersion

from utils.operation import Operation

_TEMP_DIR = os.path.join(tempfile.gettempdir(), "packman")

# cache_path = os.path.join(_TEMP_DIR, f"download_{hashlib.md5(bytes(url, 'utf-8')).hexdigest()}")


class Cache:
    def __init__(self, name: str) -> None:
        self.name = name

    def fetch_version(self, version: str, operation: Operation) -> None:
        cache_path = self.get_path(version, ".zip")
        if not os.path.exists(cache_path):
            raise Exception("not found")
        operation = Operation()
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
        return os.path.join(_TEMP_DIR, file)
