import json
import os
from argparse import ArgumentParser
from typing import Optional
from zipfile import ZipFile

from loguru import logger
from packman.models.manifest import Manifest
from packman.utils.operation import Operation
from packman.utils.progress import StepProgress

from .command import Command
from .util import get_version_name

_DEFAULT_EXPORT_FILE = "packman-export"
_DEFAULT_EXPORT_FORMAT = "json"


def _default_export_path(format: Optional[str] = None) -> str:
    if format is None:
        format = _DEFAULT_EXPORT_FORMAT

    if format == "json":
        return f"{_DEFAULT_EXPORT_FILE}.json"
    if format == "zip":
        return f"{_DEFAULT_EXPORT_FILE}.zip"

    raise ValueError(f"unknown format: {format}")


def _infer_export_format(path: str) -> str:
    name = os.path.basename(path)
    ext_idx = name.rfind(os.path.extsep)
    if ext_idx <= 0:
        return _DEFAULT_EXPORT_FORMAT
    ext = name[ext_idx:]
    if ext == ".json":
        return "json"
    if ext == ".zip":
        return "zip"

    raise ValueError(f"unrecognised extension: {path}")


class ExportCommand(Command):
    help = "Exports installed packages"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-o", "--output", help="The file to export", dest="output_path"
        )
        parser.add_argument("--format", help="The format to use", dest="format")

    def execute(
        self, output_path: Optional[str] = None, format: Optional[str] = None
    ) -> None:
        if not output_path:
            output_path = _default_export_path(format=format)
        step_name = output_path
        self.output.write_step_progress(step_name, 0.0)

        def on_progress(p: float) -> None:
            self.output.write_step_progress(step_name, p)

        try:
            if not format:
                format = _infer_export_format(output_path)

            manifest = self.packman.manifest

            if format == "json":
                versions = {
                    package_name: package.version
                    for package_name, package in manifest.packages.items()
                }

                with open(output_path, "w") as fp:
                    json.dump(versions, fp)

            elif format == "zip":
                root = self.packman.root_dir
                with ZipFile(output_path, "w") as zipfile:
                    on_step_progress = StepProgress.from_step_count(
                        step_count=sum(
                            len(package.files) for package in manifest.packages.values()
                        )
                        + 1,
                        on_progress=on_progress,
                    )
                    for package in manifest.packages.values():
                        for file in package.files:
                            relfile = os.path.relpath(file, root)
                            zipfile.write(file, relfile)
                            on_step_progress.advance()
                    zip_manifest = manifest.deepcopy()
                    zip_manifest.original_files = {}
                    zip_manifest.orphaned_files = set()
                    zip_manifest.update_path_root(root)
                    zipfile.writestr("manifest.json", zip_manifest.json(indent=2))
                    on_step_progress.advance()

            else:
                raise ValueError(f"unknown format: {format}")

        except Exception as exc:
            logger.exception(exc)
            self.output.write_step_error(step_name, str(exc))
        except KeyboardInterrupt as exc:
            self.output.write_step_error(step_name, "cancelled")
            raise exc from None
        else:
            self.output.write_step_complete(step_name)


class ImportCommand(Command):
    help = "Imports a package export"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-i",
            "--input",
            help="The file to import",
            dest="input_path",
            default=f"{_DEFAULT_EXPORT_FILE}.json",
        )

    def execute(self, input_path: str) -> None:
        format = _infer_export_format(input_path)

        manifest = self.packman.manifest

        step_name = ""

        def on_progress(p: float) -> None:
            self.output.write_step_progress(step_name, p)

        if format == "json":
            with open(input_path, "r") as fp:
                versions = json.load(fp)
                for name, version in versions.items():
                    version_name = get_version_name(version)
                    step_name = f"+ {name}@{version_name}"
                    try:
                        if not self.packman.install(
                            name=name, version=version, on_progress=on_progress
                        ):
                            # not_installed += 1
                            self.output.write_step_error(step_name, "already installed")
                        else:
                            self.output.write_step_complete(step_name)
                    except Exception as exc:
                        logger.exception(exc)
                        self.output.write_step_error(step_name, str(exc))
                    except KeyboardInterrupt:
                        self.output.write_step_error(step_name, "cancelled")

        elif format == "zip":
            with Operation() as op:
                zip_root = op.extract_archive(input_path)
                zip_manifest = Manifest.from_json(
                    os.path.join(zip_root, "manifest.json"), update_root=False
                )

                for name, package in zip_manifest.packages.items():
                    version_name = get_version_name(package.version)
                    step_name = f"+ {name}@{version_name}"

                    if (
                        package.version is not None
                        and name in manifest.packages
                        and manifest.packages[name].version == package.version
                    ):
                        self.output.write_step_error(step_name, "already installed")
                        continue

                    self.output.write_step_progress(step_name, 0.0)
                    try:
                        on_step_progress = StepProgress.from_step_count(
                            step_count=len(package.files), on_progress=on_progress
                        )
                        on_step_progress(0.0)

                        for relfile in package.files:
                            tmpfile = os.path.join(zip_root, relfile)
                            file = os.path.join(self.packman.root_dir, relfile)
                            dest = os.path.normpath(os.path.dirname(file))
                            if dest != ".":
                                os.makedirs(dest, exist_ok=True)
                            op.copy_file(tmpfile, file)
                            on_step_progress.advance()

                        package.prepend_path(self.packman.root_dir)
                        manifest.packages[name] = package
                    except Exception as exc:
                        logger.exception(exc)
                        self.output.write_step_error(step_name, str(exc))
                    except KeyboardInterrupt as exc:
                        self.output.write_step_error(step_name, "cancelled")
                        raise exc from None
                    else:
                        self.output.write_step_complete(step_name)

                self.packman.commit_backups(op)
                manifest.update_files(self.packman.manifest_path)

        else:
            raise ValueError(f"unknown format: {format}")
