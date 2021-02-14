import os
from glob import iglob
from pathlib import Path, PurePath
from typing import Dict, Iterable, List, Set

from loguru import logger
from packman.models.install_step import BaseInstallStep
from packman.utils.operation import Operation
from packman.utils.progress import ProgressCallback, StepProgress, progress_noop
from pydantic import Field


class CopyFolderInstallStep(BaseInstallStep):
    """
    Copies folders matching a glob pattern into the root directory at a given relative path.

    NOTE: throws an error if more than one match is found.
    """

    glob: str = Field(
        ...,
        alias="copy-folder",
        title="Folder Glob Pattern",
        description="Glob pattern to match folder to copy.",
    )
    dest: str = Field(
        ...,
        alias="to",
        title="Destination Path",
        description="Path to copy a matched folder to.",
    )
    exclude: List[str] = Field(
        [],
        alias="without",
        title="Exclusions",
        description="A list of glob patterns matching files to exclude.",
    )

    @staticmethod
    def _is_subpath(path: str, subpath: str) -> bool:
        """ Returns True if subpath is a subpath of path. """
        resolved_subpath = os.path.abspath(subpath)
        resolved_path = os.path.abspath(path)
        return resolved_subpath.startswith(resolved_path + os.sep)

    def iter_src(self, package_path: str) -> Iterable[str]:
        found_paths: Set[str] = set()
        for path in iglob(os.path.join(package_path, self.glob), recursive=True):
            if not os.path.isdir(path):
                continue

            # Ignore children of previously matched paths
            if any(
                (
                    CopyFolderInstallStep._is_subpath(path=other_path, subpath=path)
                    for other_path in found_paths
                )
            ):
                continue

            normpath = os.path.normpath(path)
            found_paths.add(normpath)
            yield normpath

    def do_execute(
        self,
        operation: Operation,
        package_path: str,
        root_dir: str,
        on_progress: ProgressCallback = progress_noop,
    ) -> None:
        src = self.iter_src(package_path=package_path)
        dest = os.path.join(root_dir, self.dest)

        files_to_copy: Dict[str, str] = {}
        for folder in src:
            if files_to_copy:
                raise FileExistsError(
                    f"multiple folders found matching glob: {self.glob}"
                )
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

        if not files_to_copy:
            logger.warning(f"no files to copy: {self.glob}")
            return

        on_step_progress = StepProgress.from_step_count(
            step_count=len(files_to_copy), on_progress=on_progress
        )

        for file_src, file_dest in files_to_copy.items():
            operation.copy_file(file_src, file_dest)
            on_step_progress.advance()

    class Config:
        schema_extra = {
            "examples": [
                {"copy-folder": "GameData", "to": "GameData"},
                {"copy-folder": "**/project.json/..", "to": ""},
            ]
        }
        title = "Copy Folder"
