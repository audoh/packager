from abc import ABC
from typing import Callable

from packman.utils.operation import Operation
from packman.utils.union import DiscriminatedUnion
from pydantic import BaseModel, Extra


class BaseInstallStep(BaseModel, ABC):
    action: str

    def execute(self, operation: Operation, package_path: str, root_dir: str, on_progress: Callable[[float], None] = lambda: None) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = DiscriminatedUnion(BaseInstallStep, "action")
install_step = InstallStep.decorator()
