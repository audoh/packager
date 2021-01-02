import os
from pathlib import Path, PurePath
from typing import List, Optional

from packman.models.install_step import BaseInstallStep, install_step
from packman.utils.operation import Operation


@install_step("copy_folder")
class CopyFolderInstallStep(BaseInstallStep):
    name: str
    to: str
    exclude: Optional[List[str]] = None

    def copy_folder(self, operation: Operation, src: str, dest: str) -> None:
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
                operation.copy_file(file_src, file_dest)

    def execute(self, operation: Operation, package_path: str, root_dir: str) -> None:
        for root, subdirs, files in os.walk(package_path):
            for subdir in subdirs:
                if subdir == self.name:
                    src = os.path.join(root, subdir)
                    dest = os.path.join(root_dir, self.to)
                    self.copy_folder(operation, src, dest)
                    return
        raise Exception(f"folder not found: {self.name}")
