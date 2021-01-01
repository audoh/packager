import os
import shutil
from typing import Iterable, Optional, Set

from git.repo.base import Repo
from loguru import logger

import packman.sources
import packman.steps
from packman.config import (DEFAULT_CONFIG_PATH, DEFAULT_GIT_URL,
                            DEFAULT_MANIFEST_PATH, DEFAULT_REPO_CONFIG_PATH)
from packman.models.configuration import Package
from packman.models.manifest import Manifest, ManifestPackage
from packman.models.package_source import PackageVersion
from packman.utils.cache import Cache
from packman.utils.files import remove_path, resolve_case, temp_path
from packman.utils.operation import Operation


class Packman:
    def __init__(self, config_dir=DEFAULT_CONFIG_PATH, manifest_path=DEFAULT_MANIFEST_PATH, git_config_dir=DEFAULT_REPO_CONFIG_PATH, git_url=DEFAULT_GIT_URL) -> None:
        self.config_dir = config_dir
        self.manifest_path = manifest_path
        self.git_config_dir = git_config_dir
        self.git_url = git_url

    def manifest(self) -> Manifest:
        return Manifest.from_path(self.manifest_path)

    def install(self, package: str, version: Optional[str] = None) -> bool:
        cfg_path = os.path.join(self.config_dir, f"{package}.yml")

        # enforce case match for consistency with uninstall and across platforms
        basename = os.path.basename(resolve_case(cfg_path))
        if package != basename[:-4]:
            raise FileNotFoundError(f"no such file or directory: {cfg_path}")

        op: Operation
        cfg = Package.from_path(cfg_path)
        context = package

        version_info: Optional[PackageVersion] = None
        logger.info(f"{context} - resolving version info...",)
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
            raise Exception(f"failed to resolve info for version: {version}")
        version = version_info.version
        logger.success(f"{context} - resolved info for version {version}")

        manifest = self.manifest()
        if package in manifest.packages and manifest.packages[package].version == version:
            logger.info(f"{context} - already installed")
            return False

        cache_source = Cache(name=package)
        op = Operation()
        try:
            cache_source.fetch_version(version, operation=op)
        except Exception:
            op.abort()
            op = None
            cache_miss = True
        else:
            logger.info(f"{context} - retrieved from cache")
            cache_miss = False

        if cache_miss:
            logger.info(f"{context} - downloading...")
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
                    logger.success(f"{context} - downloaded")
                    break

        if not op:
            raise Exception(f"no available sources for {context}")

        with op:
            package_path = op.last_path
            if not package_path:
                raise Exception("no package found")

            if cache_miss:
                logger.info(f"{context} - updating cache...")
                try:
                    cache_source.add_package(
                        version_info=version_info, package_path=package_path)
                except Exception as exc:
                    logger.error(f"{context} - failed to update cache")
                    logger.exception(exc)
                else:
                    logger.success(f"{context} - cache updated")

            logger.info(f"{context} - installing...")
            for step in cfg.steps:
                step.execute(package_path, operation=op)

            manifest.packages[package] = ManifestPackage(
                version=version, files=op.new_paths)

            manifest.write_json(self.manifest_path)

            logger.success(f"{context} - installed")

        return True

    def uninstall(self, package: str) -> bool:
        manifest = self.manifest()

        try:
            del manifest.packages[package]
        except KeyError:
            return False

        manifest.write_json(self.manifest_path)

        logger.success(f"{package} - uninstalled")
        return True

    def update(self) -> None:
        dir = temp_path()
        os.makedirs(dir)
        try:
            logger.debug(
                f"retrieving config files from {self.git_url}/{self.git_config_dir}")
            Repo.clone_from(url=self.git_url, to_path=dir, depth=1)
            cfg_path = os.path.join(dir, self.git_config_dir)
            for root, _, files in os.walk(cfg_path):
                for file in files:
                    src = os.path.join(root, file)
                    src_relpath = os.path.relpath(src, cfg_path)
                    dest = os.path.join(self.config_dir, src_relpath)
                    logger.debug(f"copying {src} to {dest}")
                    shutil.copy2(src, dest)
        finally:
            remove_path(dir)

    def versions(self, package: str) -> Iterable[str]:
        path = os.path.join(self.config_dir, f"{package}.yml")
        cfg = Package.from_path(path)
        versions: Set[str] = set()
        for source in cfg.sources:
            for version in source.get_versions():
                if version not in versions:
                    versions.add(version)
                    yield version

    def packages(self) -> Iterable[Package]:
        for root, _, files in os.walk(self.config_dir):
            for file in files:
                path = os.path.join(root, file)
                yield os.path.relpath(path, self.config_dir), Package.from_path(path)


_default_packman: Optional[Packman] = None


def default_packman() -> Packman:
    """
    Accessor for the default Packman instance.
    """
    global _default_packman
    if not _default_packman:
        _default_packman = Packman()
    return _default_packman


def install(package: str, version: str) -> bool:
    return default_packman().install(package, version)


def uninstall(package: str) -> bool:
    return default_packman().uninstall(package)


def update() -> None:
    default_packman().update()


def versions(package: str) -> Iterable[str]:
    yield from default_packman().versions(package)


def packages() -> Iterable[Package]:
    yield from default_packman().packages()
