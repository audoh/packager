from typing import Dict, List

import yaml
from packman.models.install_step import InstallStep
from packman.models.package_source import PackageSource
from pydantic import BaseModel
from pydantic.fields import Field
from pydantic.main import Extra

_cache: Dict[str, "PackageDefinition"] = {}


class PackageDefinition(BaseModel):
    """
    Describes a package and how to fetch and install it.
    """

    name: str = Field(
        ..., description="Human readable package name e.g. 'Ferram Aerospace Research'."
    )
    description: str = Field(
        "",
        description="A brief (100 character) summary of what this package does "
        "e.g. 'Provides realistic aerodynamics.'.",
        max_length=100,
    )
    sources: List[PackageSource] = Field(
        ...,
        min_items=1,
        description="Where this package can be downloaded from e.g. a GitHub repository. "
        "Sources will be tried in order when attempting to retrieve package.",
    )
    steps: List[InstallStep] = Field(
        ...,
        min_items=1,
        description="Steps required to install a version of this package. "
        "All steps must succeed for a successful package installation; "
        "if any one step fails, package installation will be aborted.",
    )

    class Config:
        extra = Extra.forbid
        title = "Package Definition"

    @staticmethod
    def from_yaml(path: str) -> "PackageDefinition":
        """
        Attempts to load a package definition file from the given YAML file.
        """
        if path in _cache:
            return _cache[path]
        with open(path, "r") as fp:
            raw = yaml.load(fp, Loader=yaml.SafeLoader)
            cfg = PackageDefinition(**raw)
            _cache[path] = cfg
            return cfg
