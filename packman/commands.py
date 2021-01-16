import json
import os
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any, List, Optional

from loguru import logger

import packman.manager as packman
from packman.utils.output import ConsoleOutput


class Command(ABC):
    output = ConsoleOutput()

    @property
    @abstractmethod
    def help(self) -> str:
        ...

    def configure_parser(self, parser: ArgumentParser) -> None:
        return

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> None:
        ...


class PackageListCommand(Command):
    help = "Lists available packages"

    def execute(self) -> None:
        self.output.write_table([[name, config.name, config.description]
                                 for name, config in packman.packages()])


_DEFAULT_EXPORT_FILE = "packman-export"
_DEFAULT_EXPORT_FORMAT = "json"


def _default_export_path(format: Optional[str] = None) -> str:
    if format is None:
        format = _DEFAULT_EXPORT_FORMAT

    if format == "json":
        return f"{_DEFAULT_EXPORT_FILE}.json"
    if format == "zip":
        return f"{_DEFAULT_EXPORT_FILE}.zip"

    raise Exception(f"unknown format: {format}")


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


class ExportCommand(Command):
    help = "Exports installed packages"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-o", "--output", help="The file to export", dest="output_path")
        parser.add_argument(
            "--format", help="The format to use", dest="output_path")

    def execute(self, output_path: Optional[str] = None, format: Optional[str] = None) -> None:
        if not output_path:
            output_path = _default_export_path(format=format)
        if not format:
            format = _infer_export_format(output_path)

        manifest = packman.default_packman().manifest()
        if format == "json":
            versions = {package_name: package.version for package_name,
                        package in manifest.packages.items()}
            with open(output_path, "w") as fp:
                json.dump(versions, fp)
        elif format == "zip":
            raise NotImplementedError("zip TODO")  # TODO

        else:
            raise Exception(f"unknown format: {format}")


class ImportCommand(Command):
    help = "Imports a package export"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-i", "--input", help="The file to import", dest="input_path", default=f"{_DEFAULT_EXPORT_FILE}.json")

    def execute(self, input_path: str) -> None:
        format = _infer_export_format(input_path)

        if format == "json":
            with open(input_path, "r") as fp:
                versions = json.load(fp)
                for package, version in versions.items():
                    packman.install(package=package, version=version)
        elif format == "zip":
            raise NotImplementedError("TODO")  # TODO
        else:
            raise Exception(f"unknown format: {format}")


class VersionListCommand(Command):
    help = "Lists available versions for a package"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "package", help="The package to list versions for")

    def execute(self, package: str) -> None:
        for version in packman.versions(package):
            self.output.write(version)


class InstalledPackageListCommand(Command):
    help = "Lists installed packages"

    def execute(self) -> None:
        manifest = packman.default_packman().manifest()
        packages = {key: value for key, value in packman.packages()}
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
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                self.output.write("No installed packages to update.")
                return
            packages = manifest.packages.keys()

        output = self.output
        not_installed = 0
        for package in packages:
            at_idx = package.find("@")
            if at_idx != -1:
                name, version = package.split("@")
            else:
                name = package
                version_info = packman.default_packman().get_latest_version_info(name)
                version = version_info.version

            step_name = f"+ {name}@{version}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)

            try:
                if not packman.install(package=name, version=version, force=force, no_cache=no_cache, on_progress=on_progress):
                    not_installed += 1
                    output.write_step_error(step_name, "already installed")
                else:
                    output.write_step_complete(step_name)
            except Exception as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))

        output.end()

        if not_installed == 1:
            self.output.write(
                f"{not_installed} package was not installed. Use -f to force installation.")
        elif not_installed > 1:
            self.output.write(
                f"{not_installed} packages were not installed. Use -f to force installation.")


# TODO interactive orphan resolution:
# - Delete all
# - Delete orphan
# - Keep orphan (remove from manifest)
# - Restore from backup (if applicable)


class UninstallCommand(Command):
    help = "Uninstalls one or more packages previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to remove; if none specified, all packages will be removed", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                self.output.write("No installed packages to uninstall.")
                return
            packages = manifest.packages.keys()

        output = self.output
        for name in packages:
            step_name = f"- {name}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)
            try:
                if not packman.uninstall(package=name, on_progress=on_progress):
                    output.write_step_error(
                        step_name, "not uninstalled; perhaps you didn't install it using this tool?")
                else:
                    output.write_step_complete(step_name)
            except Exception as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))

        output.end()


class UpdateCommand(Command):
    help = "Updates the configuration from the configured remote source"

    def execute(self) -> None:

        output = self.output

        step_name = "updating..."

        def on_progress(p: float) -> None:
            output.write_step_progress(step_name, p)

        try:
            if packman.update(on_progress=on_progress):
                output.write_step_complete(step_name)
            else:
                output.write_step_error(step_name, "nothing to update")
        except Exception as exc:
            logger.exception(exc)
            output.write_step_error(step_name, str(exc))

        output.end()


class ValidateCommand(Command):
    help = "Validates the files of one or more packages"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to validate; if none specified, all packages will be validated", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                self.output.write("0 invalid files")
                return
            packages = manifest.packages.keys()
        invalid_files: List[str] = []
        for package in packages:
            invalid_files += list(packman.validate(package=package))
        invalid_count = len(invalid_files)
        if invalid_count == 1:
            self.output.write("1 invalid file")
        else:
            self.output.write(f"{invalid_count} invalid files")
        for file in invalid_files:
            self.output.write(file)
