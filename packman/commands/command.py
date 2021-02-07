from abc import ABC, abstractmethod
from argparse import ArgumentParser
from math import ceil
from typing import Any, Iterable, Optional

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


class ListCommand(Command, ABC):
    def configure_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--page",
            "-p",
            default=None,
            type=int,
            dest="page",
            help="1-based page number",
            metavar="<page>",
        )
        parser.add_argument(
            "--limit",
            "-l",
            default=None,
            type=int,
            dest="limit",
            help="Maximum of packages to show",
            metavar="<limit>",
        )

    def execute(
        self,
        *args: Any,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        iterable = self.get_iterable(*args, **kwargs)

        if page is not None:
            if limit is None:
                limit = 10
            elif limit < 1:
                raise ValueError("limit cannot be less than 1")

            iterable = list(iterable)
            page_count = ceil(len(iterable) / limit)
            page = max(1, min(page, page_count))

            start = (page - 1) * limit
            end = start + limit
            iterable = iterable[start:end]
            self.output.write_line(f"Showing page {page} of {page_count}")

        self.write_iterable(iterable, *args, **kwargs)

    @abstractmethod
    def get_iterable(self, *args: Any, **kwargs: Any) -> Iterable:
        raise NotImplementedError

    @abstractmethod
    def write_iterable(self, iterable: Iterable, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError
