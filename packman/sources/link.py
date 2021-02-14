from packman.models.package_source import (BaseUnversionedPackageSource,
                                           PackageVersion)
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from pydantic import AnyHttpUrl, Field


class LinkPackageSource(BaseUnversionedPackageSource):
    """
    Downloads the current version from a link.
    Does not support versioning.
    """

    url: AnyHttpUrl = Field(
        ..., description="URL where this mod can be downloaded from"
    )

    def get_latest_version(self) -> PackageVersion:
        return PackageVersion(
            name=self.url, version=None, options=[self.url], description=""
        )

    def fetch_latest_version(
        self,
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        zip_path = operation.download_file(self.url, on_progress=on_progress)
        operation.extract_archive(zip_path)
        operation.remove_file(zip_path)
