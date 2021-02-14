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
        ..., description="Name of this version e.g. v1.3.37."
    )
    options: List[str] = Field(
        ...,
        description="Names of the different packages available for this version"
        " e.g. software often has separate builds for amd64, arm, x86.",
    )
    description: str = Field(
        "", description="A description of changes or notices for this version."
    )


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
        version: str,
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


PackageSource = create_union(BasePackageSource)
package_source = PackageSource.decorator()
