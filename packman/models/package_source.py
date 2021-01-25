from abc import ABC, abstractmethod
from typing import Iterable, List

from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from packman.utils.union import create_union
from pydantic import BaseModel, Extra


class PackageVersion(BaseModel):
    name: str
    version: str
    options: List[str]
    description: str = ""


class BasePackageSource(BaseModel, ABC):
    @abstractmethod
    def get_version(self, version: str) -> PackageVersion:
        ...

    @abstractmethod
    def fetch_version(
        self,
        version: str,
        option: str,
        operation: Operation,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        ...

    @abstractmethod
    def get_latest_version(self) -> PackageVersion:
        ...

    @abstractmethod
    def get_versions(self) -> Iterable[str]:
        ...

    class Config:
        extra = Extra.forbid


PackageSource = create_union(BasePackageSource)
package_source = PackageSource.decorator()
