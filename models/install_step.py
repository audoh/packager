from abc import ABC

from pydantic import BaseModel, Extra
from utils.operation import Operation
from utils.union import DiscriminatedUnion


class BaseInstallStep(BaseModel, ABC):
    action: str

    def execute(self, package_path: str, operation: Operation) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = DiscriminatedUnion(BaseInstallStep, "action")
install_step = InstallStep.decorator()
