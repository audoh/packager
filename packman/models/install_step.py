from abc import ABC

from packman.utils.operation import Operation
from packman.utils.union import DiscriminatedUnion
from pydantic import BaseModel, Extra


class BaseInstallStep(BaseModel, ABC):
    action: str

    def execute(self, operation: Operation, package_path: str, root_dir: str) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = DiscriminatedUnion(BaseInstallStep, "action")
install_step = InstallStep.decorator()
