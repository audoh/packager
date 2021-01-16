
import base64
import json
import os
from typing import Any, Dict, Iterable, List, Optional
from urllib import parse as urlparse

import requests
from loguru import logger
from packman.models.package_source import (BasePackageSource, PackageVersion,
                                           package_source)
from packman.utils.operation import Operation
from packman.utils.progress import (ProgressCallback, StepProgress,
                                    progress_noop)

_API_URL = "https://api.github.com"

_HEADERS = {"accept": "application/vnd.github.v3+json"}
if "GITHUB_TOKEN" in os.environ:
    token_bytes = bytes(os.environ["GITHUB_TOKEN"], "utf-8")
    token_base64_bytes = base64.b64encode(token_bytes)
    token_base64 = token_base64_bytes.decode("utf-8")
    _HEADERS["authorization"] = f"Basic {token_base64}"


class RepositoryAPI:
    headers = _HEADERS
    url = _API_URL

    def __init__(self, repository: str) -> None:
        self.repository = repository

    def uri(self, endpoint: str) -> str:
        return urlparse.urljoin(self.url, f"/repos/{self.repository}/{endpoint}")

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        res = requests.get(url=self.uri(endpoint),
                           headers=self.headers, params=kwargs)
        res.raise_for_status()
        return res.json()

    def list_releases(self, per_page: Optional[int] = None, page: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.get("releases", per_page=per_page, page=page)

    def list_release_assets(self, release_id: int, per_page: Optional[int] = None, page: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.get(f"releases/{release_id}/assets", per_page=per_page, page=page)

    def get_release_by_tag_name(self, tag: str) -> Dict[str, Any]:
        return self.get(f"releases/tags/{tag}")

    def get_latest_release(self) -> Dict[str, Any]:
        return self.get(f"releases/latest")


def _to_version_info(release: Dict[str, Any]) -> PackageVersion:
    return PackageVersion(name=release["name"], version=release["tag_name"], description=release["body"])


def _is_usable_archive(asset: Dict[str, Any]) -> bool:
    supported_content_types = ("application/zip")
    supported_extensions = ("zip")

    if "content_type" in asset:
        if asset["content_type"] in supported_content_types:
            return True
    else:
        logger.warning("no content_type field for asset")

    if "name" in asset:
        name = asset["name"]
        extidx = name.rfind(".")
        if extidx != -1:
            if name[extidx:] in supported_extensions:
                return True
        else:
            logger.warning("no extension for asset")
    else:
        logger.warning("no name field for asset")

    if "browser_download_url" in asset:
        name = os.path.basename(asset["browser_download_url"])
        extidx = name.rfind(".")
        if extidx != -1:
            if name[extidx:] in supported_extensions:
                return False
    else:
        logger.warning("no browser_download_url field for asset")

    return True


@package_source(type="github")
class GitHubPackageSource(BasePackageSource):
    repository: str

    def get_api(self) -> RepositoryAPI:
        return RepositoryAPI(self.repository)

    def get_version(self, version: str) -> PackageVersion:
        api = self.get_api()
        release = api.get_release_by_tag_name(tag=version)
        return _to_version_info(release)

    def fetch_version(self, version: str, operation: Operation, on_progress: ProgressCallback = progress_noop) -> None:
        on_step_progress = StepProgress.from_step_count(
            step_count=1, on_progress=on_progress)

        api = self.get_api()
        release = api.get_release_by_tag_name(tag=version)
        release_id = release["id"]
        assets = [asset for asset in api.list_release_assets(
            release_id=release_id) if _is_usable_archive(asset)]

        asset_count = len(assets)
        if asset_count == 1:
            asset = assets[0]
        elif asset_count > 1:
            # TODO
            raise NotImplementedError("multiple asset support")
        else:
            raise Exception("no assets")

        url = asset["browser_download_url"]

        zip_path = operation.download_file(url, on_progress=on_step_progress)
        operation.extract_archive(zip_path)
        operation.remove_file(zip_path)

    def get_latest_version(self) -> PackageVersion:
        api = self.get_api()
        release = api.get_latest_release()
        return _to_version_info(release)

    def get_versions(self) -> Iterable[str]:
        api = self.get_api()
        return (release["tag_name"] for release in api.list_releases())


if __name__ == "__main__":
    api = RepositoryAPI("KSP-KOS/KOS")
    release = api.list_releases(per_page=1)[0]
    assets = api.list_release_assets(release["id"])
    print(json.dumps(assets, indent=2))
