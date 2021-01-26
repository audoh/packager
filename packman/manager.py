import filecmp
import os
import shutil
from functools import cached_property
from typing import Iterable, List, Optional, Set, Tuple

from git.repo.base import Repo
from loguru import logger

import packman.sources
import packman.steps
from packman.config import (DEFAULT_CONFIG_PATH, DEFAULT_GIT_URL,
                            DEFAULT_MANIFEST_PATH, DEFAULT_REPO_CONFIG_PATH,
                            DEFAULT_ROOT_DIR)
from packman.models.manifest import Manifest, ManifestPackage
from packman.models.package_definition import PackageDefinition
from packman.models.package_source import PackageVersion
from packman.utils.cache import Cache
from packman.utils.files import (backup_path, checksum, remove_path,
                                 resolve_case, temp_path)
from packman.utils.operation import Operation
from packman.utils.progress import (ProgressCallback, RestoreProgress,
                                    StepProgress, progress_noop)


class VersionNotFoundError(Exception):
    def __init__(self, message: str, package: str, version: str) -> None:
        super().__init__(message)
        self.package = package
        self.version = version


class NoSourcesError(Exception):
    def __init__(
        self, message: str, package: str, version: str, causes: List[Exception]
    ) -> None:
        super().__init__(message)
        self.package = package
        self.version = version
        self.causes = causes


class NoFilesError(Exception):
    ...


class Packman:
    def __init__(
        self,
        config_dir: str = DEFAULT_CONFIG_PATH,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
        git_config_dir: str = DEFAULT_REPO_CONFIG_PATH,
        git_url: str = DEFAULT_GIT_URL,
        root_dir: str = DEFAULT_ROOT_DIR,
    ) -> None:
        self.config_dir = config_dir
        self.manifest_path = manifest_path
        self.git_config_dir = git_config_dir
        self.git_url = git_url
        self.root_dir = root_dir

    def get_version_info(self, name: str, version: str) -> PackageVersion:
        """
        Returns information about the specified version for the given package.

        :raises FileNotFoundError: If the package cannot be found.
        :raises VersionNotFoundError: If the version cannot be found from the sources defined for the package.
        """
        package = self.package(name)
        for source in package.sources:
            try:
                return source.get_version(version)
            except Exception as exc:
                logger.error(f"failed to load from source: {source}")
                logger.exception(exc)
                continue
        raise VersionNotFoundError(
            f"no version info for {name}@{version}", package=name, version=version
        )

    def get_latest_version_info(self, name: str) -> PackageVersion:
        """
        Returns information about the latest version available for the given package.

        :raises FileNotFoundError: If the package cannot be found.
        :raises VersionNotFoundError: If the latest version cannot be found from the sources defined for the package.
        """
        package = self.package(name)
        for source in package.sources:
            try:
                return source.get_latest_version()
            except Exception as exc:
                logger.error(f"failed to load from source: {source}")
                logger.exception(exc)
                continue
        raise VersionNotFoundError(
            f"no version info for {name}@latest", package=name, version="latest"
        )

    @cached_property
    def manifest(self) -> Manifest:
        """
        Returns the path to this manager's manifest file.
        """
        return Manifest.from_json(self.manifest_path)

    def package_path(self, name: str) -> str:
        """
        Returns the path to the definition file for the given package.
        """
        return os.path.join(self.config_dir, f"{name}.yml")

    def validate(self, name: str) -> Iterable[str]:
        """
        Validates the given package's files, returning an iterable of each invalid file path.
        """
        manifest = self.manifest
        package = manifest.packages[name]
        for file in package.checksums:
            if checksum(file) != package.checksums[file]:
                logger.warning(f"checksum mismatch: {file}")
                yield file

    def commit_backups(self, operation: Operation) -> None:
        """
        Commits all temporary backup files for the given Operation to a permanent backup directory.
        """
        # TODO fix error when installing with -f
        manifest = self.manifest
        modified_files = manifest.modified_files
        original_files = manifest.original_files
        for original_path, temporary_path in operation.backups.items():
            if (
                original_path not in modified_files
                and original_path not in original_files
            ):
                # commit temporary backup to permanence
                logger.debug(f"committing backup for {original_path}")
                permanent_path = backup_path(original_path)
                os.makedirs(os.path.dirname(permanent_path), exist_ok=True)
                shutil.copy2(temporary_path, permanent_path)
                manifest.original_files[original_path] = permanent_path

    def install(
        self,
        name: str,
        version: str,
        force: bool = False,
        no_cache: bool = False,
        on_progress: ProgressCallback = progress_noop,
    ) -> bool:
        """
        Idempotently installs a version of the given package.

        :param force: If True, install even if already installed.
        :param no_cache: If True, don't retrieve package from cache.

        :returns: A boolean indicating whether or not the installation resulted in any changes.
        """
        op: Optional[Operation] = None
        package = self.package(name)
        package_path = None
        context = name

        on_step_progress = StepProgress.from_step_count(
            step_count=2 + len(package.steps), on_progress=on_progress
        )
        on_progress(0.0)
        on_restore_progress = RestoreProgress.step_progress(
            step_progress=on_step_progress, on_progress=on_progress
        )

        # region Versioning

        logger.info(f"{context} - resolving version info...")
        version_info = self.get_version_info(name, version)
        version = version_info.version
        logger.success(f"{context} - resolved info for version {version}")

        # endregion
        # region Early-out

        manifest = self.manifest
        if name in manifest.packages and manifest.packages[name].version == version:
            if force:
                logger.info(f"{context} - reinstalling")
            else:
                logger.info(f"{context} - already installed")
                return False

        # endregion
        # region Cache

        source_errors: List[Exception] = []

        logger.info(f"{context} - checking cache")
        cache_source = Cache(name=name)
        if no_cache:
            cache_miss = True
        else:
            op = Operation(on_restore_progress=on_restore_progress)
            try:
                cache_source.fetch_version(
                    version=version,
                    option=version_info.options[0],
                    operation=op,
                    on_progress=on_step_progress,
                )
            except Exception as exc:
                logger.info(f"{context} - not found in cache")
                err = Exception("not found in cache")
                err.__cause__ = exc
                source_errors.append(err)
                op.abort()
                op = None
                cache_miss = True
            else:
                if op.last_path:
                    logger.info(f"{context} - retrieved from cache")
                    package_path = op.last_path
                    on_step_progress.advance()
                    cache_miss = False
                else:
                    logger.error(
                        f"cache for {context} did not end operation with a path"
                    )
                    op.abort()
                    op = None
                    cache_miss = True

        # endregion
        # region Download

        if cache_miss:
            logger.info(f"{context} - downloading...")
            for source in package.sources:
                op = Operation(on_restore_progress=on_restore_progress)
                try:
                    source.fetch_version(
                        version=version,
                        option=version_info.options[0],
                        operation=op,
                        on_progress=on_step_progress,
                    )
                except Exception as exc:
                    logger.error(f"failed to load from source: {source}")
                    logger.exception(exc)
                    err = Exception(f"failed to load from source: {source}")
                    err.__cause__ = exc
                    source_errors.append(err)
                    op.abort()
                    op = None
                    continue
                else:
                    if op.last_path:
                        package_path = op.last_path
                        on_step_progress.advance()
                        logger.success(f"{context} - downloaded")
                        break
                    else:
                        logger.error(
                            f"source {source.type} for {context} did not end operation with a path"
                        )
                        op.abort()
                        op = None
                        continue

        # endregion

        if not op:
            raise NoSourcesError(
                f"no available sources for {context}",
                package=name,
                version=version or "latest",
                causes=source_errors,
            )

        with op:
            assert package_path, "operation did not end with a path"

            # region Cache update

            if cache_miss:
                logger.info(f"{context} - updating cache...")
                try:
                    cache_source.add_package(
                        version_info=version_info, package_path=package_path
                    )
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
                step.execute(
                    operation=op,
                    package_path=package_path,
                    root_dir=self.root_dir,
                    on_progress=on_step_progress,
                )
                on_step_progress.advance()

            if not op.new_paths:
                raise NoFilesError("mod has no files")

            # endregion
            # region Manifest

            self.commit_backups(op)

            manifest.packages[name] = ManifestPackage(
                version=version, options=[version_info.options[0]], files=op.new_paths
            )

            manifest.update_files(self.manifest_path, on_progress=on_step_progress)

            on_progress(1.0)

            # endregion
            logger.success(f"{context} - installed")

        return True

    def uninstall(
        self, name: str, on_progress: ProgressCallback = progress_noop
    ) -> bool:
        """
        Idempotently uninstalls the current version of the given package.

        :returns: A boolean indicating whether or not the uninstallation resulted in any changes.
        """
        manifest = self.manifest

        on_progress(0.0)

        try:
            del manifest.packages[name]
        except KeyError:
            return False

        manifest.update_files(self.manifest_path, on_progress=on_progress)
        on_progress(1.0)

        logger.success(f"{name} - uninstalled")
        return True

    def update(self, on_progress: ProgressCallback = progress_noop) -> bool:
        """
        Updates the local package definitions with the latest from the defined remote sources.
        """
        on_progress(0.0)

        dir = temp_path()
        os.makedirs(dir)
        updated = False
        try:
            logger.debug(
                f"retrieving config files from {self.git_url}/{self.git_config_dir}"
            )
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

            on_progress(1.0)
        finally:
            remove_path(dir)
        if not updated:
            logger.info("no changes")
        return updated

    def versions(self, name: str) -> Iterable[str]:
        """
        Returns an iterable of all versions available for the given package.

        :raises FileNotFoundError: If the package cannot be found.
        """
        package = self.package(name)
        versions: Set[str] = set()
        for source in package.sources:
            for version in source.get_versions():
                if version not in versions:
                    versions.add(version)
                    yield version

    def package(self, name: str) -> PackageDefinition:
        """
        Returns the definition for the given package.

        :raises FileNotFoundError: If the package cannot be found.
        """
        path = self.package_path(name)

        # Enforce case for consistency with uninstall() and across platforms
        path_cased = resolve_case(path)
        relpath_cased = os.path.relpath(path_cased, self.config_dir)
        pathname = relpath_cased[:-4].replace(os.path.sep, "/")
        if name != pathname:
            raise FileNotFoundError(f"{name=} does not match {pathname=}")

        return PackageDefinition.from_yaml(path)

    def packages(self) -> Iterable[Tuple[str, PackageDefinition]]:
        """
        Returns an iterable of 2-tuples containing the name and definition of all available packages.
        """
        for root, _, files in os.walk(self.config_dir):
            for file in files:
                path = os.path.join(root, file)
                relpath = os.path.relpath(path, self.config_dir)
                name = relpath[: relpath.rindex(os.extsep)]
                yield name, PackageDefinition.from_yaml(path)
