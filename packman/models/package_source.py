from abc import ABC, abstractmethod
from typing import Iterable, List, Union

from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from packman.utils.union import create_union
from pydantic import BaseModel, Extra, Field


class PackageVersion(BaseModel):
    """
    Contains information about an installable version of a package.
    """

    name: str = Field(..., description="Human readable version name.")
    version: Union[str, None] = Field(
        ...,
        description="Unique identifier for this version e.g. v1.3.37."
        "If None, represents info about an unversioned 'latest' package.",
    )
    options: List[str] = Field(
        ...,
        description="Names of the different packages available for this version"
        " e.g. software often has separate builds for amd64, arm, x86.",
        min_items=1,
    )
    description: str = Field(
        "", description="A description of changes or notices for this version."
    )

    class Config:
        arbitrary_types_allowed = True


class BasePackageSource(BaseModel, ABC):
    """
    An abstract class representing a means of retrieving a package so that it can be installed.
    """

    @abstractmethod
    def get_version(self, version: Union[str, None]) -> PackageVersion:
        """
        Returns information about the requested package version.
        """
        ...

    @abstractmethod
    def fetch_version(
        self,
        version: Union[str, None],
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        """
        Retrieves a package matching the given version and option so that it can be installed.

        This method is passed an Operation instance, which should be used for all actions involving the file-system.

        If any Exception is raised during the execution of this method, the Operation will be rolled back and a
        different source will be tried if defined for the package.

        Finer grained progress updates can be provided to the caller via on_progress, but it is not required to do so.
        The caller should regardless consider the progress to be 0 before and 1 after this call.
        """
        ...

    @abstractmethod
    def get_latest_version(self) -> PackageVersion:
        """
        Returns information about the latest version available from this source.
        """
        ...

    @abstractmethod
    def get_versions(self) -> Iterable[str]:
        """
        Returns a list of all versions available from this source, by name only.
        """
        ...

    class Config:
        extra = Extra.forbid
        arbitrary_types_allowed = True


class BaseUnversionedPackageSource(BasePackageSource):
    """
    An abstract class representing a means of retrieving a package so that it can be installed.

    Does not support versioning.
    """

    def _version_error(self) -> ValueError:
        return ValueError("This source does not support versioning")

    def get_version(self, version: Union[str, None]) -> PackageVersion:
        if version is not None:
            raise self._version_error()
        return self.get_latest_version()

    def get_versions(self) -> Iterable[str]:
        return []

    def fetch_version(
        self,
        version: Union[str, None],
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        if version is not None:
            raise self._version_error()
        return self.fetch_latest_version(
            option=option, operation=operation, on_progress=on_progress
        )

    @abstractmethod
    def fetch_latest_version(
        self,
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        ...


PackageSource = create_union(BasePackageSource)
package_source = PackageSource.decorator()
