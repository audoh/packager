import os
from glob import glob
from pathlib import Path, PurePath
from typing import Dict, List, Optional

from loguru import logger
from packman.models.install_step import BaseInstallStep, install_step
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, StepProgress, progress_noop
from pydantic import Field


@install_step()
class CopyFolderInstallStep(BaseInstallStep):
    glob: str = Field(..., alias="copy-folder")
    to: str
    exclude: Optional[List[str]] = None

    def do_execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        src = glob(os.path.join(package_path, self.glob), recursive=True)
        dest = os.path.join(root_dir, self.to)
        if not src:
            logger.warning(f"folder not found: {self.glob}")
            on_progress(1.0)
            return
        if len(src) > 1:
            raise FileExistsError(f"multiple folders found: {self.glob}")

        files_to_copy: Dict[str, str] = {}
        for folder in src:
            for root, _, files in os.walk(folder):
                root_relpath = os.path.relpath(root, folder)
                dest_root = os.path.join(dest, root_relpath)
                Path(dest_root).mkdir(parents=True, exist_ok=True)
                for file in files:
                    file_src = os.path.join(root, file)
                    if self.exclude:
                        file_relsrc = os.path.join(root_relpath, file)
                        pure_path = PurePath(file_relsrc)
                        if any(pure_path.match(pattern) for pattern in self.exclude):
                            continue
                    file_dest = os.path.join(dest_root, file)
                    files_to_copy[file_src] = file_dest

            on_step_progress = StepProgress.from_step_count(
                step_count=len(files_to_copy), on_progress=on_progress
            )

            for file_src, file_dest in files_to_copy.items():
                operation.copy_file(file_src, file_dest)
                on_step_progress.advance()
