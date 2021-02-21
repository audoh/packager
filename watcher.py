import os
import time
from pathlib import PurePath
from sys import argv, stderr

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

TEST_DIRS = ("./tests",)
WATCH_FILES = "**/*.py"
TEST_GLOB = "**/test_*.py"

_dirname = os.path.dirname(__file__)
_test_dirs = [
    os.path.abspath(os.path.join(_dirname, _test_dir)) for _test_dir in TEST_DIRS
]
_cmd = argv[2] if len(argv) >= 3 else os.environ.get("PYTEST_CMD", "pytest")
_scheduled_cmd = None


def _run_test_path(path: str) -> None:
    global _scheduled_cmd
    path = path.replace(os.sep, "/")
    exec = f"{_cmd} {path}"
    _scheduled_cmd = exec


class Handler(FileSystemEventHandler):
    def on_modified(self, event: FileModifiedEvent):
        super().on_modified(event)

        if event.is_directory:
            return

        src_path = os.path.abspath(event.src_path)

        pure_path = PurePath(src_path)
        if not pure_path.match(WATCH_FILES):
            return

        test_dir = next(
            (dir_path for dir_path in _test_dirs if src_path.startswith(dir_path)), None
        )
        if test_dir:
            is_test_file = pure_path.match(TEST_GLOB)
            src_relpath = os.path.relpath(src_path, ".")
            if is_test_file:
                # run only file tests
                _run_test_path(src_relpath)
            else:
                # run only directory tests
                src_dir = os.path.dirname(src_relpath)
                _run_test_path(src_dir)
        else:
            # run all tests
            _run_test_path("")


if __name__ == "__main__":
    event_handler = Handler()
    observer = Observer()
    path = argv[1] if len(argv) >= 2 else "."
    name = os.path.basename(__file__)
    print(f"{name}: watching {path}", file=stderr)
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
            if _scheduled_cmd is not None:
                print(f"{name}: {_scheduled_cmd}", file=stderr)
                os.system(_scheduled_cmd)
                _scheduled_cmd = None
    finally:
        observer.stop()
        observer.join()
