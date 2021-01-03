import json
import os
import shutil
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any, List, Optional

from loguru import logger

import packman.manager as packman


class Command(ABC):
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
        width = 30
        for name, config in packman.packages():
            print(
                f"{name.ljust(width)} {config.name.ljust(width)} {config.description}")


_DEFAULT_EXPORT_FILE = "packman-export"
_DEFAULT_EXPORT_FORMAT = "json"


def _default_export_path(format: Optional[str] = None) -> str:
    if format is None:
        format = _DEFAULT_EXPORT_FORMAT

    if format == "json":
        return f"{_DEFAULT_EXPORT_FILE}.json"

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
            raise NotImplementedError("TODO")  # TODO
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
            print(version)


class InstalledPackageListCommand(Command):
    help = "Lists installed packages"

    def execute(self) -> None:
        width = 30
        manifest = packman.default_packman().manifest()
        for name, info in manifest.packages.items():
            print(f"{name.ljust(width)} {info.version}")


class InstallCommand(Command):
    help = "Installs or updates one or more packages using the current local configuration"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="The package or packages to install, by name or in package@version format; if none specified, all packages will be updated to their latest versions", nargs="*")
        parser.add_argument(
            "-f", "--force", help="Forces re-installation when the package version is already installed", action="store_true"
        )

    def execute(self, packages: Optional[List[str]] = None, force=False) -> None:
        if not packages:
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                logger.info("no packages installed to update")
                return
            packages = manifest.packages.keys()

        changed = True
        for package in packages:
            at_idx = package.find("@")
            if at_idx != -1:
                name, version = package.split("@")
            else:
                name = package
                version = None
            if not packman.install(package=name, version=version, force=force):
                changed = False
        if not changed:
            logger.info("use -f to force installation")


class UninstallCommand(Command):
    help = "Uninstalls one or more packages previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to remove; if none specified, all packages will be removed", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                logger.info("no packages installed to remove")
                return
            packages = manifest.packages.keys()
        for package in packages:
            uninstalled = packman.uninstall(package=package)
            if not uninstalled:
                logger.warning(
                    f"package {package} not uninstalled; perhaps you didn't install it using this tool?")


class UpdateCommand(Command):
    help = "Updates the configuration from the configured remote source"

    def execute(self) -> None:
        packman.update()


class VerifyCommand(Command):
    help = "Verifies that the files of one or more packages have not changed since installation"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Names of the package or packages to verify; if none specified, all packages will be verified", nargs="*")
        parser.add_argument(
            "-l", "--list", help="List the specific files which are invalid", action="store_true", dest="list_files"
        )

    def execute(self, packages: Optional[List[str]] = None, list_files=False) -> None:
        if not packages:
            manifest = packman.default_packman().manifest()
            if not manifest.packages:
                logger.info("no packages installed to verify")
                return
            packages = manifest.packages.keys()
        invalid_files: List[str] = []
        for package in packages:
            invalid_files += list(packman.verify(package=package))
        invalid_count = len(invalid_files)
        if invalid_count == 0:
            logger.success("all files are valid")
        else:
            if list_files:
                for file in invalid_files:
                    print(file)
            elif invalid_count == 1:
                logger.warning("1 file is invalid")
            else:
                logger.warning(f"{invalid_count} files are invalid")
