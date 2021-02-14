from abc import ABC
from typing import List

from packman.models.condition import Condition
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from packman.utils.union import create_union
from pydantic import BaseModel, Extra, Field


class BaseInstallStep(BaseModel, ABC):
    """
    An abstract class representing a step to be executed in the course of installing a particular package.
    """

    conditions: List[Condition] = Field(
        [],
        alias="if",
        title="Conditions",
        min_items=1,
        description="Defines a list of conditions which must all be met in order for this install step to execute.",
    )

    def execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        if any(
            (
                not cond.evaluate(package_path=package_path, root_dir=root_dir)
                for cond in self.conditions
            )
        ):
            return
        self.do_execute(
            operation=operation,
            package_path=package_path,
            root_dir=root_dir,
            on_progress=on_progress,
        )

    def do_execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        ...

    class Config:
        extra = Extra.forbid


InstallStep = create_union(BaseInstallStep)
install_step = InstallStep.decorator()
