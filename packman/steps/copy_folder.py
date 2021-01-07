import os
from pathlib import Path, PurePath
from typing import Callable, Dict, List, Optional, Set

from packman.models.install_step import BaseInstallStep, install_step
from packman.utils.operation import Operation
from packman.utils.progress import StepProgress


@install_step("copy_folder")
class CopyFolderInstallStep(BaseInstallStep):
    name: str
    to: str
    exclude: Optional[List[str]] = None

    def execute(self, operation: Operation, package_path: str, root_dir: str, on_progress: Callable[[float], None] = lambda p: None) -> None:
        src = ""
        dest = ""
        for root, subdirs, files in os.walk(package_path):
            for subdir in subdirs:
                if subdir == self.name:
                    src = os.path.join(root, subdir)
                    dest = os.path.join(root_dir, self.to)
                    break
            if src:
                break
        if not src:
            raise Exception("folder not found: {self.name}")

        files_to_copy: Dict[str, str] = {}
        for root, subdirs, files in os.walk(src):
            root_relpath = os.path.relpath(root, src)
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

        step_count = len(files_to_copy)
        on_step_progress = StepProgress(
            step_mult=1 / step_count, on_progress=on_progress)

        for file_src, file_dest in files_to_copy.items():
            operation.copy_file(file_src, file_dest)
            on_step_progress.advance()
