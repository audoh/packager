from abc import ABC, abstractmethod
from argparse import ArgumentParser
from typing import Any

from loguru import logger
from packman.manager import Packman
from packman.utils.output import ConsoleOutput


class Command(ABC):
    output = ConsoleOutput()

    def __init__(self, packman: Packman) -> None:
        super().__init__()
        self.packman = packman

    @property
    @abstractmethod
    def help(self) -> str:
        ...

    def configure_parser(self, parser: ArgumentParser) -> None:
        return

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> None:
        ...

    def execute_safe(self, *args: Any, **kwargs: Any) -> bool:
        try:
            self.execute(*args, **kwargs)
        except Exception as exc:
            logger.exception(exc)
            self.output.write_line(str(exc))
            return False
        except KeyboardInterrupt:
            self.output.write_line("Aborted due to keyboard interrupt.")
            return False
        else:
            return True
        finally:
            self.output.end()
