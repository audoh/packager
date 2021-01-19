import os.path
from functools import cached_property
from typing import Any, Iterable, List, Optional
from urllib import parse as urlparse

from packman.api.http import HTTPAPI
from packman.models.package_source import (
    BasePackageSource,
    PackageVersion,
    package_source,
)
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, StepProgress, progress_noop
from pydantic import BaseModel

_API_URL = "https://spacedock.info/api/"


class Version(BaseModel):
    id: int

    game_version: str
    friendly_version: str
    download_path: str

    changelog: str


class Mod(BaseModel):
    id: int

    name: str
    author: str

    description: str
    short_description: str
    description_html: str

    versions: List[Version]
    default_version_id: int

    def get_version(
        self,
        *args: Any,
        id: Optional[int] = None,
        friendly_version: Optional[str] = None,
    ) -> Version:
        return next(
            (
                version
                for version in self.versions
                if version.id == id or version.friendly_version == friendly_version
            )
        )


class SpaceDockAPI(HTTPAPI):
    def __init__(self, mod_id: int) -> None:
        super().__init__(url=_API_URL)
        self.mod_id = mod_id

    def uri(self, endpoint: str) -> str:
        return urlparse.urljoin(self.url, endpoint)

    @cached_property
    def mod(self) -> Mod:
        mod = Mod(**self.get(f"mod/{self.mod_id}"))
        for version in mod.versions:
            version.download_path = urlparse.urljoin(self.url, version.download_path)
        return mod


@package_source(type="spacedock")
class SpaceDockPackageSource(BasePackageSource):
    id: int

    @cached_property
    def _api(self) -> SpaceDockAPI:
        return SpaceDockAPI(mod_id=self.id)

    def _get_option_name(self, download_path: str) -> str:
        option = os.path.basename(download_path)
        ext_idx = option.rfind(".")
        if ext_idx > 0:
            option = option[:ext_idx]
        return option

    def _to_version_info(self, mod_version: Version) -> PackageVersion:
        return PackageVersion(
            name=mod_version.friendly_version,
            version=mod_version.friendly_version,
            description=mod_version.changelog,
            options=[self._get_option_name(mod_version.download_path)],
        )

    def get_version(self, version: str) -> PackageVersion:
        mod_version = self._api.mod.get_version(friendly_version=version)
        return self._to_version_info(mod_version)

    def fetch_version(
        self,
        version: str,
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        on_step_progress = StepProgress.from_step_count(
            step_count=3, on_progress=on_progress
        )

        mod_version = self._api.mod.get_version(friendly_version=version)
        if self._get_option_name(mod_version.download_path) != option:
            raise ValueError(f"unknown option: {option}")

        path = operation.download_file(
            mod_version.download_path, on_progress=on_step_progress
        )
        on_step_progress.advance()

        operation.extract_archive(path)
        on_step_progress.advance()

        operation.remove_file(path)
        on_step_progress.advance()

    def get_latest_version(self) -> PackageVersion:
        mod_version = self._api.mod.get_version(id=self._api.mod.default_version_id)
        return self._to_version_info(mod_version)

    def get_versions(self) -> Iterable[str]:
        return (mod_version.friendly_version for mod_version in self._api.mod.versions)
