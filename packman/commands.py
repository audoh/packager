import json
import os
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any, List, Optional
from zipfile import ZipFile

from loguru import logger

from packman.manager import Packman
from packman.models.manifest import Manifest
from packman.utils.operation import Operation
from packman.utils.output import ConsoleOutput
from packman.utils.progress import StepProgress


class Command(ABC):
    output = ConsoleOutput()

    def __init__(self, packman: Packman) -> None:
        super().__init__()
        self.packman = packman

    @property
    @abstractmethod
    def help(self) -> str:
        ...

    def configure_parser(self, parser: ArgumentParser) -> None:
        return

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> None:
        ...

    def execute_safe(self, *args: Any, **kwargs: Any) -> bool:
        try:
            self.execute(*args, **kwargs)
        except Exception as exc:
            self.output.write_line(str(exc))
            return False
        except KeyboardInterrupt as exc:
            self.output.write_line("Aborted due to keyboard interrupt.")
            return False
        else:
            return True
        finally:
            self.output.end()


class PackageListCommand(Command):
    help = "Lists available packages"

    def execute(self) -> None:
        self.output.write_table([[name, config.name, config.description]
                                 for name, config in self.packman.packages()])


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
            "-o", "--output", help="The file to export", dest="output_path")
        parser.add_argument(
            "--format", help="The format to use", dest="format")

    def execute(self, output_path: Optional[str] = None, format: Optional[str] = None) -> None:
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
                versions = {package_name: package.version for package_name,
                            package in manifest.packages.items()}

                with open(output_path, "w") as fp:
                    json.dump(versions, fp)

            elif format == "zip":
                root = self.packman.root_dir
                with ZipFile(output_path, "w") as zipfile:
                    on_step_progress = StepProgress.from_step_count(step_count=sum(len(
                        package.files) for package in manifest.packages.values()) + 1, on_progress=on_progress)
                    for package in manifest.packages.values():
                        for file in package.files:
                            relfile = os.path.relpath(file, root)
                            zipfile.write(file, relfile)
                            on_step_progress.advance()
                    zip_manifest = manifest.deepcopy()
                    zip_manifest.original_files = {}
                    zip_manifest.orphaned_files = set()
                    zip_manifest.update_path_root(root)
                    zipfile.writestr(
                        "manifest.json", zip_manifest.json(indent=2))
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
            "-i", "--input", help="The file to import", dest="input_path", default=f"{_DEFAULT_EXPORT_FILE}.json")

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
                    step_name = f"+ {name}@{version}"
                    try:
                        if not self.packman.install(name=name, version=version, on_progress=on_progress):
                            # not_installed += 1
                            self.output.write_step_error(
                                step_name, "already installed")
                        else:
                            self.output.write_step_complete(step_name)
                    except Exception as exc:
                        logger.exception(exc)
                        self.output.write_step_error(step_name, str(exc))
                    except KeyboardInterrupt as exc:
                        self.output.write_step_error(step_name, "cancelled")

        elif format == "zip":
            with Operation() as op:
                zip_root = op.extract_archive(input_path)
                zip_manifest = Manifest.from_path(os.path.join(
                    zip_root, "manifest.json"), update_root=False)

                for name, package in zip_manifest.packages.items():
                    step_name = f"+ {name}@{package.version}"

                    if name in manifest.packages and manifest.packages[name].version == package.version:
                        self.output.write_step_error(
                            step_name, "already installed")
                        continue

                    self.output.write_step_progress(step_name, 0.0)
                    try:
                        on_step_progress = StepProgress.from_step_count(
                            step_count=len(package.files), on_progress=on_progress)
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


class VersionListCommand(Command):
    help = "Lists available versions for a package"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "package", help="The package to list versions for")

    def execute(self, package: str) -> None:
        for version in self.packman.versions(package):
            self.output.write(version)


class InstalledPackageListCommand(Command):
    help = "Lists installed packages"

    def execute(self) -> None:
        manifest = self.packman.manifest
        packages = {key: value for key, value in self.packman.packages()}
        self.output.write_table(rows=[[name, info.version, packages[name].name, packages[name].description]
                                      for name, info in manifest.packages.items()])


class InstallCommand(Command):
    help = "Installs or updates one or more packages using the current local configuration"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="The package or packages to install, by name or in package@version format; if none specified, all packages will be updated to their latest versions", nargs="*")
        parser.add_argument(
            "-f", "--force", help="Forces re-installation when the package version is already installed", action="store_true"
        )
        parser.add_argument(
            "--no-cache", help="Forces re-download when the package version is already downloaded", action="store_true", dest="no_cache"
        )

    def execute(self, packages: Optional[List[str]] = None, force: bool = False, no_cache: bool = False) -> None:
        if not packages:
            manifest = self.packman.manifest
            if not manifest.packages:
                self.output.write("No installed packages to update.")
                return
            packages = list(manifest.packages.keys())

        output = self.output
        not_installed = 0
        for package in packages:
            at_idx = package.find("@")
            if at_idx != -1:
                name, version = package.split("@")
            else:
                name = package
                version_info = self.packman.get_latest_version_info(name)
                version = version_info.version

            step_name = f"+ {name}@{version}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)

            try:
                if not self.packman.install(name=name, version=version, force=force, no_cache=no_cache, on_progress=on_progress):
                    not_installed += 1
                    output.write_step_error(step_name, "already installed")
                else:
                    output.write_step_complete(step_name)
            except Exception as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))
            except KeyboardInterrupt as exc:
                self.output.write_step_error(step_name, "cancelled")
                raise exc from None

        if not_installed == 1:
            self.output.write(
                f"{not_installed} package was not installed. Use -f to force installation.")
        elif not_installed > 1:
            self.output.write(
                f"{not_installed} packages were not installed. Use -f to force installation.")

        if self.packman.manifest.orphaned_files:
            count = len(self.packman.manifest.orphaned_files)
            print(
                f"You have {count} orphaned file{'s' if count != 1 else ''}; use 'clean' to resolve them")





class UninstallCommand(Command):
    help = "Uninstalls one or more packages previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to remove; if none specified, all packages will be removed", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = self.packman.manifest
            if not manifest.packages:
                self.output.write("No installed packages to uninstall.")
                return
            packages = list(manifest.packages.keys())

        output = self.output
        for name in packages:
            step_name = f"- {name}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)
            try:
                if not self.packman.uninstall(name=name, on_progress=on_progress):
                    output.write_step_error(
                        step_name, "not uninstalled; perhaps you didn't install it using this tool?")
                else:
                    output.write_step_complete(step_name)
            except Exception as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))
            except KeyboardInterrupt as exc:
                self.output.write_step_error(step_name, "cancelled")
                raise exc from None

        if self.packman.manifest.orphaned_files:
            count = len(self.packman.manifest.orphaned_files)
            print(
                f"You have {count} orphaned file{'s' if count != 1 else ''}; use 'clean' to resolve them")


class UpdateCommand(Command):
    help = "Updates the configuration from the configured remote source"

    def execute(self) -> None:

        output = self.output

        step_name = "updating..."

        def on_progress(p: float) -> None:
            output.write_step_progress(step_name, p)

        try:
            if self.packman.update(on_progress=on_progress):
                output.write_step_complete(step_name)
            else:
                output.write_step_error(step_name, "nothing to update")
        except Exception as exc:
            logger.exception(exc)
            output.write_step_error(step_name, str(exc))
        except KeyboardInterrupt as exc:
            self.output.write_step_error(step_name, "cancelled")
            raise exc from None


class ValidateCommand(Command):
    help = "Validates the files of one or more packages"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to validate; if none specified, all packages will be validated", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = self.packman.manifest
            if not manifest.packages:
                self.output.write("0 invalid files")
                return
            packages = list(manifest.packages.keys())
        invalid_files: List[str] = []
        for name in packages:
            invalid_files += list(self.packman.validate(name=name))
        invalid_count = len(invalid_files)
        if invalid_count == 1:
            self.output.write("1 invalid file")
        else:
            self.output.write(f"{invalid_count} invalid files")
        for file in invalid_files:
            self.output.write(file)


class CleanCommand(Command):
    help = "Cleans up orphaned files"

    def execute(self) -> None:
        raise NotImplementedError("TODO")

# TODO interactive orphan resolution:
# - Delete all
# - Delete orphan
# - Keep orphan (remove from manifest)
# - Restore from backup (if applicable)
