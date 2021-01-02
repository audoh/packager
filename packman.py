
import sys
from argparse import ArgumentParser

from packman.commands import (InstallCommand, InstalledPackageListCommand,
                              PackageListCommand, UninstallCommand,
                              UpdateCommand, VerifyCommand, VersionListCommand)

commands = {
    "install": InstallCommand(),
    "uninstall": UninstallCommand(),
    "list": InstalledPackageListCommand(),
    "update": UpdateCommand(),
    "packages": PackageListCommand(),
    "versions": VersionListCommand(),
    "verify": VerifyCommand()
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
