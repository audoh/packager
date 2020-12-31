from typing import Any, Dict, List

from pydantic import BaseModel
from pydantic.class_validators import validator
from pydantic.decorator import validate_arguments
from pydantic.fields import Field
from pydantic.main import Extra

from models.install_step import BaseInstallStep, InstallStep
from models.package_source import BasePackageSource, PackageSource


class ModConfig(BaseModel):
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
