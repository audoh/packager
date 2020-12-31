from abc import ABC

from packman.utils.operation import Operation
from packman.utils.union import DiscriminatedUnion
from pydantic import BaseModel, Extra


class BaseInstallStep(BaseModel, ABC):
    action: str

    def execute(self, package_path: str, operation: Operation) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = DiscriminatedUnion(BaseInstallStep, "action")
install_step = InstallStep.decorator()
