import os
import time
from argparse import ArgumentParser
from pathlib import PurePath
from sys import argv, stderr
from typing import Iterable

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

TEST_DIRS = ("./tests",)
FILE_GLOB = "**/*.py"
TEST_GLOB = "**/test_*.py"
PYTEST_CMD = "pytest"

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

    def _run_test_path(self, path: str) -> None:
        # Scheduling the command avoids spam, esp. when an automatic lint on save etc. is set up
        path = path.replace(os.sep, "/")
        exec = f"{self.command} {path}"
        self._scheduled_cmd = exec

    def process_changes(self) -> bool:
        if self._scheduled_cmd is not None:
            print(f"{_context_name}: {self._scheduled_cmd}", file=stderr)
            print("...", end="\r")
            os.system(self._scheduled_cmd)
            self._scheduled_cmd = None
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


if __name__ == "__main__":
    _dirname = os.path.dirname(__file__)

    argparser = ArgumentParser(
        description="Cross-platform source file watcher which runs an arbitrary command on changes"
    )
    argparser.add_argument(
        "-p", "--path", dest="path", help="Where to watch files", default="."
    )
    argparser.add_argument(
        "-d",
        "--test-dirs",
        dest="test_dirs",
        help="Paths of test directories",
        default=TEST_DIRS,
    )
    argparser.add_argument(
        "-f",
        "--files",
        dest="file_glob",
        help="Glob pattern matching files to watch",
        default=FILE_GLOB,
    )
    argparser.add_argument(
        "--test-pattern",
        dest="test_glob",
        help="Glob pattern matching test files",
        default=TEST_GLOB,
    )
    argparser.add_argument(
        "-c",
        "--command",
        dest="command",
        help="Command to run on change",
        default=PYTEST_CMD,
    )
    args = vars(argparser.parse_args(argv[1:]))
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
            time.sleep(1)
            if event_handler.process_changes():
                print("zzz", end="\r")
    finally:
        observer.stop()
        observer.join()
