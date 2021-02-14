import os
import shlex
import sys
from argparse import ArgumentError, ArgumentParser
from typing import Dict, List, Optional

from _typeshed import SupportsWrite
from loguru import logger

from packman import InstallStep, PackageSource, Packman, sources, steps
from packman.commands import (
    CleanCommand,
    Command,
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
DEFAULT_COMMANDS = {
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


class PackmanCLI:
    def __init__(
        self,
        commands: Dict[str, Command] = DEFAULT_COMMANDS,
        no_interactive_mode: bool = False,
        file: Optional[SupportsWrite[str]] = None,
    ) -> None:
        desc = "Rudimentary file package management intended for modifications for games such as KSP and RimWorld"
        parser = ArgumentParser(description=desc)
        command_parsers = parser.add_subparsers(
            metavar="<command>", help="Valid commands:", dest="command", required=False
        )
        for name, command in commands.items():
            command_parser = command_parsers.add_parser(name, help=command.help)
            command.configure_parser(command_parser)

        self.commands = commands
        self.parser = parser
        self.command_parsers = command_parsers
        self.interactive_mode_enabled = not no_interactive_mode
        self.command_parsers.required = not self.interactive_mode_enabled
        self.interactive_mode = False
        self.file = file

        self.update_usage()

    def update_usage(self) -> None:
        self.parser.usage = self.parser.format_help()[7:]

    def print(self, value: str) -> None:
        print(value, file=self.file)

    def start_interactive_mode(self) -> None:
        if self.interactive_mode:
            return
        self.interactive_mode = True

        parser = self.parser
        command_parsers = self.command_parsers

        setattr(parser, "exit_on_error", False)
        command_parsers.required = True
        command_parsers.add_parser("exit", help="Quits this interactive session")
        self.parser.format_help
        self.update_usage()

        self.print("Packman interactive session started.")
        self.print(
            "Type \u0022exit\u0022 to quit or \u0022--help\u0022 for more information."
        )

        while True:
            raw = input("> ")
            argv = shlex.split(raw)
            if argv:
                arg0 = argv[0].lower()
                if arg0.startswith(
                    ("exit", "quit", "stop", "abort", "goaway", "cancel")
                ) or arg0 in (
                    "q",
                    "e",
                ):
                    self.stop_interactive_mode()
                    break
            try:
                args = parser.parse_args(argv)
                args_dict = vars(args)
                command_name = args_dict.pop("command")
                assert command_name is not None, "command_name cannot be None"
                command = self.commands[command_name]
                command.execute_safe(**args_dict)
            except ArgumentError as exc:
                self.print(f"error: {exc.message}")
            except Exception as exc:
                self.print(f"error: {exc}")
            except SystemExit as exc:
                if exc.code != 2:
                    raise

    def stop_interactive_mode(self) -> None:
        if not self.interactive_mode:
            return
        # FIXME clean up 'exit' parser
        self.command_parsers.required = not self.interactive_mode_enabled
        self.interactive_mode = False

    def parse(self, argv: List[str]) -> None:
        parser = self.parser
        args = parser.parse_args(argv)
        args_dict = vars(args)
        command_name: Optional[str] = args_dict.pop("command")
        if command_name is None:
            if self.interactive_mode_enabled:
                self.start_interactive_mode()
            else:
                raise Exception("no command provided")
        else:
            command = DEFAULT_COMMANDS[command_name]
            command.execute_safe(**args_dict)


if __name__ == "__main__":
    # TODO set up docs generation, including the yaml schema
    # TODO add autocomplete

    # Set up yaml handlers
    PackageSource.register(
        sources.GitHubPackageSource,
        sources.SpaceDockPackageSource,
        sources.LinkPackageSource,
    )
    InstallStep.register(steps.CopyFolderInstallStep)

    # Set up logger
    logger.remove()
    logger.add(sys.stderr, level=os.environ.get("PACKMAN_LOGGING", "CRITICAL"))

    # Set up parser
    cli = PackmanCLI(commands=DEFAULT_COMMANDS)
    cli.parse(argv=sys.argv[1:])
