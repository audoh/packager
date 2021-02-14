from argparse import ArgumentParser
from typing import List, Optional

from loguru import logger
from packman.commands.util import get_version_name
from packman.utils.operation import StateFileExistsError

from .command import Command


class InstallCommand(Command):
    help = (
        "Installs or updates one or more packages using the current local configuration"
    )

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages",
            help="The package or packages to install, by name or in package@version format; if none specified, all"
            "packages will be updated to their latest versions",
            nargs="*",
        )
        parser.add_argument(
            "-f",
            "--force",
            help="Forces re-installation when the package version is already installed",
            action="store_true",
        )
        parser.add_argument(
            "--no-cache",
            help="Forces re-download when the package version is already downloaded",
            action="store_true",
            dest="no_cache",
        )

    def execute(
        self,
        packages: Optional[List[str]] = None,
        force: bool = False,
        no_cache: bool = False,
    ) -> None:
        if not packages:
            manifest = self.packman.manifest
            if not manifest.packages:
                self.output.write("No installed packages to update.")
                return
            packages = list(manifest.packages.keys())

        output = self.output
        output.step_count = len(packages)
        not_installed = 0
        for package in packages:
            at_idx = package.find("@")
            if at_idx == -1:
                name = package
                version_info = self.packman.get_latest_version_info(name)
                version = version_info.version
            else:
                name, version = package.split("@")

            version_name = get_version_name(version)
            step_name = f"+ {name}@{version_name}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)

            try:
                if not self.packman.install(
                    name=name,
                    version=version,
                    force=force,
                    no_cache=no_cache,
                    on_progress=on_progress,
                ):
                    not_installed += 1
                    output.write_step_error(step_name, "already installed")
                else:
                    output.write_step_complete(step_name)
            except StateFileExistsError as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))
                output.write(
                    "A previously interrupted operation was detected; use 'recover' to recover and roll it back."
                )
                break
            except Exception as exc:
                logger.exception(exc)
                output.write_step_error(step_name, str(exc))
            except KeyboardInterrupt as exc:
                self.output.write_step_error(step_name, "cancelled")
                raise exc from None

        if not_installed == 1:
            output.write(
                f"{not_installed} package was not installed. Use -f to force installation."
            )
        elif not_installed > 1:
            output.write(
                f"{not_installed} packages were not installed. Use -f to force installation."
            )

        if self.packman.manifest.orphaned_files:
            count = len(self.packman.manifest.orphaned_files)
            print(
                f"You have {count} orphaned file{'s' if count != 1 else ''}; use 'clean' to resolve them"
            )


class UninstallCommand(Command):
    help = "Uninstalls one or more packages previously installed using this tool"

    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "packages",
            help="Names of the package or packages to remove; if none specified, all packages will be removed",
            nargs="*",
        )

    def execute(self, packages: Optional[List[str]] = None) -> None:
        if not packages:
            manifest = self.packman.manifest
            if not manifest.packages:
                self.output.write("No installed packages to uninstall.")
                return
            packages = list(manifest.packages.keys())

        output = self.output
        output.step_count = len(packages)
        for name in packages:
            step_name = f"- {name}"

            def on_progress(p: float) -> None:
                output.write_step_progress(step_name, p)

            on_progress(0.0)
            try:
                if not self.packman.uninstall(name=name, on_progress=on_progress):
                    output.write_step_error(
                        step_name,
                        "not uninstalled; perhaps you didn't install it using this tool?",
                    )
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
                f"You have {count} orphaned file{'s' if count != 1 else ''}; use 'clean' to resolve them"
            )


class RecoverCommand(Command):
    help = "Recovers and rolls back a previously interrupted operation"

    def execute(self) -> None:
        step_name = "⭯ rollback"
        output = self.output

        def on_progress(p: float) -> None:
            output.write_step_progress(step_name, p)

        on_progress(0.0)
        try:
            self.packman.recover(on_progress=on_progress)
        except Exception as exc:
            logger.exception(exc)
            output.write_step_error(step_name, str(exc))
        except KeyboardInterrupt as exc:
            output.write_step_error(step_name, "cancelled")
            raise exc from None
        else:
            output.write_step_complete(step_name)
