from abc import ABC

from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from packman.utils.union import create_discriminated_union
from pydantic import BaseModel, Extra


class BaseInstallStep(BaseModel, ABC):
    action: str
    # condition: Optional[List[Condition]] = Field(alias="if", min_items=1)

    def execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = create_discriminated_union(BaseInstallStep, discriminator="action")
install_step = InstallStep.decorator()
