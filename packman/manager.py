import filecmp
import os
import shutil
from typing import Callable, Iterable, Optional, Set, Tuple

from git.repo.base import Repo
from loguru import logger

import packman.sources
import packman.steps
from packman.config import (DEFAULT_CONFIG_PATH, DEFAULT_GIT_URL,
                            DEFAULT_MANIFEST_PATH, DEFAULT_REPO_CONFIG_PATH,
                            DEFAULT_ROOT_DIR)
from packman.models.configuration import Package
from packman.models.manifest import Manifest, ManifestPackage
from packman.models.package_source import PackageVersion
from packman.utils.cache import Cache
from packman.utils.files import (backup_path, checksum, remove_path,
                                 resolve_case, temp_path)
from packman.utils.operation import Operation


class Packman:
    def __init__(self, config_dir=DEFAULT_CONFIG_PATH, manifest_path=DEFAULT_MANIFEST_PATH, git_config_dir=DEFAULT_REPO_CONFIG_PATH, git_url=DEFAULT_GIT_URL, root_dir=DEFAULT_ROOT_DIR) -> None:
        self.config_dir = config_dir
        self.manifest_path = manifest_path
        self.git_config_dir = git_config_dir
        self.git_url = git_url
        self.root_dir = root_dir

    def manifest(self) -> Manifest:
        return Manifest.from_path(self.manifest_path)

    def package_path(self, package: str) -> str:
        return os.path.join(self.config_dir, f"{package}.yml")

    def validate(self, name: str) -> Iterable[str]:
        manifest = self.manifest()
        package = manifest.packages[name]
        for file in package.checksums:
            if checksum(file) != package.checksums[file]:
                logger.warning(f"checksum mismatch: {file}")
                yield file

    def install(self, name: str, version: Optional[str] = None, force=False, on_progress: Callable[[float], None] = lambda: None) -> bool:
        cfg_path = self.package_path(name)

        # region Case sensitivity

        # Enforce case for consistency with uninstall() and across platforms
        basename = os.path.basename(resolve_case(cfg_path))
        if name != basename[:-4]:
            raise FileNotFoundError(f"no such file or directory: {cfg_path}")

        # endregion

        op: Operation
        package = self.package(name)
        context = name

        step_count = 2 + len(package.steps)
        step_mult = 1 / step_count
        step_no = 0

        def on_step_progress(p):
            return on_progress((step_no + p) * step_mult)
        on_progress(0.0)

        # region Versioning

        version_info: Optional[PackageVersion] = None
        logger.info(f"{context} - resolving version info...")
        for source in package.sources:
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

        # endregion
        # region Early-out

        manifest = self.manifest()
        if name in manifest.packages and manifest.packages[name].version == version:
            if force:
                logger.info(f"{context} - reinstalling")
            else:
                logger.info(f"{context} - already installed")
                return False

        # endregion
        # region Cache

        cache_source = Cache(name=name)
        op = Operation()
        try:
            cache_source.fetch_version(
                version, operation=op, on_progress=on_step_progress)
        except Exception:
            op.abort()
            op = None
            cache_miss = True
        else:
            on_step_progress(1.0)
            logger.info(f"{context} - retrieved from cache")
            cache_miss = False

        # endregion
        # region Download

        if cache_miss:
            logger.info(f"{context} - downloading...")
            for source in package.sources:
                op = Operation()
                try:
                    source.fetch_version(
                        version, operation=op, on_progress=on_step_progress)
                except Exception as exc:
                    logger.error(f"failed to load from source: {source}")
                    logger.exception(exc)

                    op.abort()
                    op = None
                    continue
                else:
                    on_step_progress(1.0)
                    logger.success(f"{context} - downloaded")
                    break
        # endregion

        if not op:
            raise Exception(f"no available sources for {context}")

        with op:
            package_path = op.last_path
            if not package_path:
                raise Exception("no package found")

            # region Cache update

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

            # endregion
            # region Installation
            # We don't need to uninstall first - files that are unreplaced (i.e. no longer included in package) are deleted/restored as part of manifest.write_json()

            logger.info(f"{context} - installing...")
            for step in package.steps:
                step_no += 1
                step.execute(operation=op, package_path=package_path,
                             root_dir=self.root_dir, on_progress=on_step_progress)
                on_step_progress(1.0)

            # endregion
            # region Manifest

            step_no += 1
            modified_files = manifest.modified_files
            original_files = manifest.original_files
            for original_path, temp_path in op.backups.items():
                if original_path not in modified_files and original_path not in original_files:
                    # commit temporary backup to permanence
                    logger.debug(f"committing backup for {original_path}")
                    permanent_path = backup_path(original_path)
                    os.makedirs(os.path.dirname(permanent_path), exist_ok=True)
                    shutil.copy2(temp_path, permanent_path)
                    manifest.original_files[original_path] = permanent_path

            manifest.packages[name] = ManifestPackage(
                version=version, files=op.new_paths)

            manifest.write_json(self.manifest_path)

            on_progress(1.0)

            # endregion
            logger.success(f"{context} - installed")

        return True

    def uninstall(self, name: str) -> bool:
        manifest = self.manifest()

        try:
            del manifest.packages[name]
        except KeyError:
            return False

        manifest.write_json(self.manifest_path)

        logger.success(f"{name} - uninstalled")
        return True

    def update(self) -> bool:
        dir = temp_path()
        os.makedirs(dir)
        updated = False
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
                    if not os.path.exists(dest) or not filecmp.cmp(src, dest):
                        logger.info(f"updating {dest}")
                        shutil.copy2(src, dest)
                        updated = True
        finally:
            remove_path(dir)
        if not updated:
            logger.info("no changes")
        return updated

    def versions(self, name: str) -> Iterable[str]:
        package = self.package(name)
        versions: Set[str] = set()
        for source in package.sources:
            for version in source.get_versions():
                if version not in versions:
                    versions.add(version)
                    yield version

    def package(self, name: str) -> Package:
        path = self.package_path(name)

        # Enforce case for consistency with uninstall() and across platforms
        basename = os.path.basename(resolve_case(path))
        if name != basename[:-4]:
            raise FileNotFoundError(f"no such file or directory: {path}")

        return Package.from_path(path)

    def packages(self) -> Iterable[Tuple[str, Package]]:
        for root, _, files in os.walk(self.config_dir):
            for file in files:
                path = os.path.join(root, file)
                relpath = os.path.relpath(path, self.config_dir)
                name = relpath[:relpath.rindex(os.extsep)]
                yield name, Package.from_path(path)


_default_packman: Optional[Packman] = None


def default_packman() -> Packman:
    """
    Accessor for the default Packman instance.
    """
    global _default_packman
    if not _default_packman:
        _default_packman = Packman()
    return _default_packman


def install(package: str, version: Optional[str] = None, force: bool = False, on_progress: Callable[[float], None] = lambda p: None) -> bool:
    return default_packman().install(package, version=version, force=force, on_progress=on_progress)


def uninstall(package: str) -> bool:
    return default_packman().uninstall(package)


def update() -> bool:
    return default_packman().update()


def versions(package: str) -> Iterable[str]:
    yield from default_packman().versions(package)


def packages() -> Iterable[Tuple[str, Package]]:
    yield from default_packman().packages()


def validate(package: str) -> Iterable[str]:
    yield from default_packman().validate(package)
