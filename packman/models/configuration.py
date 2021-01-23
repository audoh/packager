from typing import Dict, List

import yaml
from packman.models.install_step import InstallStep
from packman.models.package_source import PackageSource
from pydantic import BaseModel
from pydantic.fields import Field
from pydantic.main import Extra

_cache: Dict[str, "Package"] = {}


class Package(BaseModel):
    name: str
    description: str = ""
    sources: List[PackageSource] = Field(..., min_items=1)
    steps: List[InstallStep] = Field(..., min_items=1)

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
