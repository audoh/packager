import asyncio
import os
from argparse import ArgumentParser
from pathlib import PurePath
from sys import argv, stderr
from typing import Iterable, List

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

TEST_DIRS = ("./tests",)
FILE_GLOB = "**/*.py"
TEST_GLOB = "**/test_*.py"
PYTEST_CMD = "pytest"
POLL_TIME = 1

_context_name = os.path.basename(__file__)


class Handler(FileSystemEventHandler):
    def __init__(
        self, test_dirs: Iterable[str], file_glob: str, test_glob: str, command: str
    ) -> None:
        self.test_dirs = test_dirs
        self.file_glob = file_glob
        self.test_glob = test_glob
        self.command = command
        self._scheduled_cmd = None
        self._running = False

    def _run_test_path(self, path: str) -> None:
        print("...", end="\r")  # let it be known something is happening
        # Scheduling the command avoids spam, esp. when an automatic lint on save etc. is set up
        path = path.replace(os.sep, "/")
        exec = f"{self.command} {path}"
        self._scheduled_cmd = exec

    async def process_changes(self) -> bool:
        if self._scheduled_cmd is not None and not self._running:
            self._running = True
            print(f"{_context_name}: {self._scheduled_cmd}", file=stderr)
            print("...", end="\r")
            cmd = self._scheduled_cmd
            self._scheduled_cmd = None
            process = await asyncio.create_subprocess_shell(cmd)
            await process.wait()
            self._running = False
            return True
        return False

    def on_modified(self, event: FileModifiedEvent):
        super().on_modified(event)

        if event.is_directory:
            return

        src_path = os.path.abspath(event.src_path)

        pure_path = PurePath(src_path)
        if not pure_path.match(self.file_glob):
            return

        test_dir = next(
            (dir_path for dir_path in self.test_dirs if src_path.startswith(dir_path)),
            None,
        )
        if test_dir:
            is_test_file = pure_path.match(self.test_glob)
            src_relpath = os.path.relpath(src_path, ".")
            if is_test_file:
                # run only file tests
                self._run_test_path(src_relpath)
            else:
                # run only directory tests
                src_dir = os.path.dirname(src_relpath)
                self._run_test_path(src_dir)
        else:
            # run all tests
            self._run_test_path("")


def csv(val: str) -> List[str]:
    return [subval.strip() for subval in val.split(",")]


async def main() -> None:
    _dirname = os.path.dirname(__file__)

    argparser = ArgumentParser(
        description="Cross-platform source file watcher which runs an arbitrary command on changes"
    )
    argparser.add_argument(
        "-p", "--path", dest="path", help="Where to watch files", default=".", type=str
    )
    argparser.add_argument(
        "-d",
        "--test-dirs",
        dest="test_dirs",
        help="Paths of test directories",
        default=TEST_DIRS,
        type=csv,
    )
    argparser.add_argument(
        "-f",
        "--files",
        dest="file_glob",
        help="Glob pattern matching files to watch",
        default=FILE_GLOB,
        type=str,
    )
    argparser.add_argument(
        "--test-pattern",
        dest="test_glob",
        help="Glob pattern matching test files",
        default=TEST_GLOB,
        type=str,
    )
    argparser.add_argument(
        "-c",
        "--command",
        dest="command",
        help="Command to run on change",
        default=PYTEST_CMD,
        type=str,
    )
    argparser.add_argument("--poll-time", dest="poll_time", default=POLL_TIME, type=int)
    args = vars(argparser.parse_args(argv[1:]))
    poll_time = args.pop("poll_time")
    path = args.pop("path")

    event_handler = Handler(
        test_dirs=[
            os.path.abspath(os.path.join(_dirname, test_dir))
            for test_dir in args.pop("test_dirs")
        ],
        **args,
    )
    observer = Observer()

    print(f"{_context_name}: now watching {path}", file=stderr)
    print("zzz", end="\r")
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            await asyncio.sleep(poll_time)
            if await event_handler.process_changes():
                print("zzz", end="\r")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
