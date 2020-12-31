import os
import shutil
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any, Iterable, List, Optional, Set, Tuple

from git.repo.base import Repo
from loguru import logger

import sources
import steps
from config import CFG_PATH, MANIFEST_PATH, REPO_CFG_PATH, REPO_URL
from models.configuration import ModConfig
from models.manifest import Manifest, Package
from models.package_source import PackageVersion
from utils.cache import Cache
from utils.files import remove_path, temp_path
from utils.operation import Operation


def _load_configs() -> Iterable[Tuple[str, ModConfig]]:
    for root, _, files in os.walk(CFG_PATH):
        for file in files:
            path = os.path.join(root, file)
            yield os.path.relpath(path, CFG_PATH), ModConfig.from_path(path)


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
        for path, config in _load_configs():
            name = path[:path.rindex(os.extsep)]
            print(
                f"{name.ljust(width)} {config.name.ljust(width)} {config.description}")


class VersionListCommand(Command):
    help = "Lists available versions for a package"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "package", help="The package to list versions for")

    def execute(self, package: str) -> None:
        path = os.path.join(CFG_PATH, f"{package.lower()}.yml")
        cfg = ModConfig.from_path(path)
        versions: Set[str] = set()
        for source in cfg.sources:
            for version in source.get_versions():
                if version not in versions:
                    versions.add(version)
                    print(version)


class InstallCommand(Command):
    help = "Installs one or more packages using the current local configuration"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="Package name and version reference", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = Manifest.from_path(MANIFEST_PATH)
            packages = manifest.packages.keys()
        for package in packages:
            self.execute_package(package)

    def execute_package(self, package: str) -> None:
        at_idx = package.find("@")
        if at_idx != -1:
            name, version = package.split("@")
        else:
            name = package
            version = None

        path = os.path.join(CFG_PATH, f"{name.lower()}.yml")
        cfg = ModConfig.from_path(path)
        op: Operation

        version_info: Optional[PackageVersion] = None
        logger.info(f"{package} - resolving version info...",)
        for source in cfg.sources:
            try:
                if version:
                    version_info = source.get_version(version)
                else:
                    version_info = source.get_latest_version()
            except Exception as exc:
                logger.error(f"failed to load from source: {source}")
                logger.exception(exc)
                continue
            else:
                break
        if not version_info:
            raise Exception(f"failed to resolve version info")
        version = version_info.version
        logger.success(f"{package} - resolved info for version {version}")

        manifest = Manifest.from_path(MANIFEST_PATH)
        if name in manifest.packages and manifest.packages[name].version == version:
            logger.info(f"{package} - already installed")
            return

        cache_source = Cache(name=name)
        op = Operation()
        try:
            cache_source.fetch_version(version, operation=op)
        except Exception:
            op.abort()
            op = None
            cache_miss = True
        else:
            logger.info(f"{package} - retrieved from cache")
            cache_miss = False

        if cache_miss:
            logger.info(f"{package} - downloading...")
            for source in cfg.sources:
                op = Operation()
                try:
                    source.fetch_version(version, operation=op)
                except Exception as exc:
                    logger.error(f"failed to load from source: {source}")
                    logger.exception(exc)

                    op.abort()
                    op = None
                    continue
                else:
                    logger.success(f"{package} - downloaded")
                    break

        if not op:
            raise Exception(f"no available sources for {package}")

        with op:
            package_path = op.last_path
            if not package_path:
                raise Exception("no package found")

            if cache_miss:
                logger.info(f"{package} - updating cache...")
                try:
                    cache_source.add_package(
                        version_info=version_info, package_path=package_path)
                except Exception as exc:
                    logger.error(f"{package} - failed to update cache")
                    logger.exception(exc)
                else:
                    logger.success(f"{package} - cache updated")

            logger.info(f"{package} - installing...")
            for step in cfg.steps:
                step.execute(package_path, operation=op)

            manifest.packages[name] = Package(
                version=version, files=op.new_paths)

            manifest.write_json(MANIFEST_PATH)

            logger.success(f"{package} - installed")


class UninstallCommand(Command):
    help = "Uninstalls a package previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages", help="The packages to remove", nargs="*")

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = Manifest.from_path(MANIFEST_PATH)
            packages = manifest.packages.keys()
        for package in packages:
            self.execute_package(package)

    def execute_package(self, package: str) -> None:
        manifest = Manifest.from_path(MANIFEST_PATH)

        try:
            del manifest.packages[package]
        except KeyError:
            raise Exception(
                "package not found; perhaps you didn't install it using this tool?")

        manifest.write_json(MANIFEST_PATH)

        logger.success(f"{package} - uninstalled")


class UpdateCommand(Command):
    help = "Updates the configuration from the configured remote source"

    def execute(self) -> None:
        dir = temp_path()
        os.makedirs(dir)
        try:
            logger.debug(
                f"retrieving config files from {REPO_URL}/{REPO_CFG_PATH}")
            Repo.clone_from(url=REPO_URL, to_path=dir, depth=1)
            cfg_path = os.path.join(dir, REPO_CFG_PATH)
            for root, _, files in os.walk(cfg_path):
                for file in files:
                    src = os.path.join(root, file)
                    src_relpath = os.path.relpath(src, cfg_path)
                    dest = os.path.join(CFG_PATH, src_relpath)
                    logger.debug(f"copying {src} to {dest}")
                    shutil.copy2(src, dest)
        finally:
            remove_path(dir)
