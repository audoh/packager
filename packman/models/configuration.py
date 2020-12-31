from typing import Any, Dict, List

import yaml
from packman.models.install_step import BaseInstallStep, InstallStep
from packman.models.package_source import BasePackageSource, PackageSource
from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.decorator import validate_arguments
from pydantic.fields import Field
from pydantic.main import Extra

_cache: Dict[str, "Package"] = {}


class Package(BaseModel):
    name: str
    description: str = ""
    sources: List[BasePackageSource] = Field(..., min_items=1)
    steps: List[BaseInstallStep] = Field(..., min_items=1)

    @validator("sources", each_item=True, pre=True)
    @validate_arguments
    def resolve_sources(cls: Any, raw: Dict[str, Any]) -> BasePackageSource:
        return PackageSource(**raw)

    @validator("steps", each_item=True, pre=True)
    @validate_arguments
    def resolve_steps(cls: Any, raw: Dict[str, Any]) -> BasePackageSource:
        return InstallStep(**raw)

    class Config:
        extra = Extra.forbid

    @staticmethod
    def from_path(path: str) -> "Package":
        if path in _cache:
            return _cache[path]
        with open(path, "r") as fp:
            raw = yaml.load(fp, Loader=yaml.SafeLoader)
            cfg = Package(**raw)
            _cache[path] = cfg
            return cfg
