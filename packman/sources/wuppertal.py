from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import parse as urlparse

from packman.api.http import HTTPAPI
from packman.models.package_source import (BaseUnversionedPackageSource,
                                           PackageVersion)
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from pydantic import BaseModel, Field

_API_URL = "https://launcher.emergency-wuppertal.de/api/public/v1/"
_CDN_URL = "https://download.emergency-wuppertal.de/"


class Hash(BaseModel):
    id: str
    version_id: str = Field(..., alias="versionId")
    version: Optional[Any] = None
    relative_path: str = Field(..., alias="relativePath")
    checksum: str


class Version(BaseModel):
    id: str
    display_name: str = Field(..., alias="displayName")
    creation: datetime
    hashes: List[Hash] = Field([])
    branch_relations: Optional[Any] = Field(None, alias="branchRelations")
    deleted: Optional[Any] = None

    def to_version_info(self) -> PackageVersion:
        return PackageVersion(name=self.display_name, version=self.id, options=[self.id])


# `https://download.emergency-wuppertal.de/versions/${i.id}/Full.zip`
class WuppertalAPI(HTTPAPI):
    def __init__(self) -> None:
        super().__init__(url=_API_URL)

    def get_version(self, id: str) -> Version:
        res: Dict[str, Any] = self.get(f"versions/{id}", includeHashes=True)
        return Version(**res)

    def get_latest_version(self) -> Version:
        return self.get_version(id="latest")

    def get_download_url(self, version_id: str) -> str:
        return urlparse.urljoin(_CDN_URL, f"versions/{version_id}/Full.zip")

    def get_download_urls(self, version: Version) -> Iterable[Tuple[str, str]]:
        for hash in version.hashes:
            path = hash.relative_path
            yield urlparse.urljoin(
                _CDN_URL, f"versions/{version.id}/Packaged/{path}.zip"
            ), path


class WuppertalPackageSource(BaseUnversionedPackageSource):
    wuppertal: bool

    def get_api(self) -> WuppertalAPI:
        return WuppertalAPI()

    def get_version(self, version: str) -> PackageVersion:
        raise NotImplementedError

    def get_latest_version(self) -> PackageVersion:
        latest_ver = api.get_latest_version()
        return latest_ver.to_version_info()

    def fetch_latest_version(
        self,
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        latest_ver = api.get_latest_version()
        download_url = api.get_download_url(latest_ver.id)
        zip_path = operation.download_file(download_url, on_progress=on_progress)
        operation.extract_archive(zip_path)
        operation.remove_file(zip_path)


if __name__ == "__main__":
    api = WuppertalAPI()
    ver = api.get_latest_version()
    print(api.get_download_url(version_id=ver.id))
    print(list(api.get_download_urls(ver)))
