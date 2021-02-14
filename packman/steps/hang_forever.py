from time import sleep

from packman.models.install_step import BaseInstallStep
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, progress_noop
from pydantic import Field


class HangForeverInstallStep(BaseInstallStep):
    """
    Hangs forever, for testing/debugging purposes.
    """

    enabled: bool = Field(
        ...,
        alias="hang-forever",
        title="Hang Forever",
        description="Whether or not to hang forever, for testing and debugging purposes.",
    )

    def do_execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        while self.enabled:
            sleep(5)
