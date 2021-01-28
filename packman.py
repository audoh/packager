import argparse
import os
import shlex
import sys
from argparse import ArgumentError, ArgumentParser
from logging import error
from typing import Optional

from loguru import logger

from packman import InstallStep, PackageSource, Packman, sources, steps
from packman.commands import (
    CleanCommand,
    ExportCommand,
    ImportCommand,
    InstallCommand,
    InstalledPackageListCommand,
    PackageListCommand,
    UninstallCommand,
    UpdateCommand,
    ValidateCommand,
    VersionListCommand,
)

packman = Packman()
commands = {
    "install": InstallCommand(packman),
    "uninstall": UninstallCommand(packman),
    "list": InstalledPackageListCommand(packman),
    "update": UpdateCommand(packman),
    "packages": PackageListCommand(packman),
    "versions": VersionListCommand(packman),
    "validate": ValidateCommand(packman),
    "export": ExportCommand(packman),
    "import": ImportCommand(packman),
    "clean": CleanCommand(packman),
}


if __name__ == "__main__":
    # TODO set up docs generation, including the yaml schema

    # Set up yaml handlers
    PackageSource.register(sources.GitHubPackageSource, sources.SpaceDockPackageSource)
    InstallStep.register(steps.CopyFolderInstallStep)

    # Set up logger
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("PACKMAN_LOGGING", "CRITICAL"))

    # Set up parser
    parser = ArgumentParser(
        description="Rudimentary file package management intended for modifications for games such as KSP and RimWorld"
    )
    command_parsers = parser.add_subparsers(
        metavar="<command>", help="Valid commands:", dest="command", required=False
    )
    for name, command in commands.items():
        command_parser = command_parsers.add_parser(name, help=command.help)
        command.configure_parser(command_parser)
    parser.usage = parser.format_help()[7:]

    # Run
    args = parser.parse_args(sys.argv[1:])
    args_dict = vars(args)
    command_name: Optional[str] = args_dict.pop("command")
    if command_name is None:
        parser.exit_on_error = False
        command_parsers.required = True
        command_parsers.add_parser("exit", help="Quits this interactive session")
        parser.usage = parser.format_help()[7:]

        print("Packman interactive session started.")
        print('Type "exit" to quit or "--help" for more information.')

        while True:
            raw = input("> ")
            argv = shlex.split(raw)
            if argv:
                arg0 = argv[0].lower()
                if arg0.startswith(("exit", "quit")) or arg0 in ("q", "e"):
                    sys.exit(0)
            try:
                args = parser.parse_args(argv)
                args_dict = vars(args)
                command_name: str = args_dict.pop("command")
                command = commands[command_name]
                command.execute_safe(**args_dict)
            except ArgumentError as exc:
                print(f"error: {exc.message}")
            except Exception as exc:
                print(f"error: {exc}")
            except SystemExit as exc:
                if exc.code != 2:
                    raise

    else:
        command = commands[command_name]
        command.execute_safe(**args_dict)
