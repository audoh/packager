import json
import os
import sys
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml
from git.repo.base import Repo
from loguru import logger

import sources
import steps
from models.configuration import ModConfig
from models.manifest import Manifest, Package
from models.package_source import PackageVersion
from utils.cache import Cache
from utils.files import remove, temp_path
from utils.operation import Operation
from utils.uninterruptible import uninterruptible

CFG_PATH = os.environ.get("PACKAGER_CONFIG_FILE", "cfg")
MANIFEST_PATH = os.environ.get("PACKAGER_MANIFEST_FILE", "packager.json")
REPO_URL = os.environ.get("PACKAGER_REPOSITORY",
                          "https://github.com/audoh/packager.git")

_config_cache: Dict[str, ModConfig] = {}


def load_config(path: str) -> ModConfig:
    key = os.path.relpath(path, CFG_PATH)
    if key in _config_cache:
        return _config_cache[key]
    with open(path, "r") as fp:
        raw = yaml.load(fp, Loader=yaml.SafeLoader)
        cfg = ModConfig(**raw)
        _config_cache[key] = cfg
        return cfg


def load_configs() -> Iterable[Tuple[str, ModConfig]]:
    for root, _, files in os.walk(CFG_PATH):
        for file in files:
            path = os.path.join(root, file)
            yield os.path.relpath(path, CFG_PATH), load_config(path)


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
        for path, config in load_configs():
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
        cfg = load_config(path)
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
            "packages", help="Package name and version reference", nargs="+")

    def execute(self, packages: List[str]) -> None:
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
        cfg = load_config(path)
        op: Operation = None

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
        logger.success(f"{package} - resolved version info")

        cache_source = Cache(name=name)
        try:
            op = cache_source.fetch_version(version)
        except Exception:
            cache_miss = True
        else:
            logger.info(f"{package} - retrieved from cache")
            cache_miss = False

        if cache_miss:
            logger.info(f"{package} - downloading...")
            for source in cfg.sources:
                try:
                    op = source.fetch_version(version)
                except Exception as exc:
                    logger.error(f"failed to load from source: {source}")
                    logger.exception(exc)
                    continue
                else:
                    logger.success(f"{package} - downloaded")
                    break

        if not op:
            raise Exception(f"no available sources for {package}")

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
        try:
            for step in cfg.steps:
                step.execute(package_path, operation=op)

            if os.path.exists(MANIFEST_PATH):
                with open(MANIFEST_PATH, "r") as fp:
                    raw = json.load(fp)
                    manifest = Manifest(**raw)
            else:
                manifest = Manifest()

            manifest.packages[name] = Package(
                version=version, files=op.new_paths)

            with open(MANIFEST_PATH, "w") as fp:
                fp.write(manifest.json())

        except (Exception, KeyboardInterrupt) as exc:
            with uninterruptible():
                logger.error(
                    f"{package} - error encountered during installation")
                logger.exception(exc)
                logger.info(f"{package} - rolling back")
                errors = op.restore()
                if errors:
                    logger.warning(f"{package} - rollback encountered errors")
        else:
            logger.success(f"{package} - installed")


class UninstallCommand(Command):
    help = "Uninstalls a package previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "package", help="The package to remove")

    def execute(self, package: str) -> None:
        try:
            with open(MANIFEST_PATH, "r") as fp:
                raw = json.load(fp)
                manifest = Manifest(**raw)
        except FileNotFoundError:
            raise Exception("manifest not found")

        try:
            manifest_package = manifest.packages[package]
        except KeyError:
            raise Exception(
                "package not found; perhaps you didn't install it using this tool?")

        for file in manifest_package.files:
            if len(manifest.file_map[file]) == 1:
                remove(file)

        del manifest.packages[package]

        with open(MANIFEST_PATH, "w") as fp:
            fp.write(manifest.json())

        logger.success(f"{package} - uninstalled")


class UpdateCommand(Command):
    help = "Updates the configuration from the configured remote source"

    def execute(self) -> None:
        dir = temp_path()
        os.makedirs(dir)
        try:
            repo = Repo.clone_from(url=REPO_URL, to_path=dir, depth=1)
        finally:
            remove(dir)


commands = {
    "install": InstallCommand(),
    "uninstall": UninstallCommand(),
    "update": UpdateCommand(),
    "packages": PackageListCommand(),
    "versions": VersionListCommand(),
}


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Rudimentary file package management intended for modifications for games such as KSP and RimWorld")
    command_parsers = parser.add_subparsers(
        metavar="<command>", help="Valid commands:", dest="command", required=True)
    for name, command in commands.items():
        command_parser = command_parsers.add_parser(
            name, help=command.help)
        command.configure_parser(command_parser)
    args = parser.parse_args(sys.argv[1:])
    args_dict = vars(args)
    command_name = args_dict.pop("command")
    command = commands[command_name]
    command.execute(**args_dict)
