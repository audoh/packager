
import os
import sys
from argparse import ArgumentParser

from loguru import logger

from packman import Packman
from packman.commands import (ExportCommand, ImportCommand, InstallCommand,
                              InstalledPackageListCommand, PackageListCommand,
                              UninstallCommand, UpdateCommand, ValidateCommand,
                              VersionListCommand)

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
    "import": ImportCommand(packman)
}


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("PACKMAN_LOGGING", "CRITICAL"))
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
