import os
import time
from sys import argv

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

_dirname = os.path.abspath(os.path.dirname(__file__))
_test_dirs = (os.path.join(_dirname, "tests"),)
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

        ext_idx = src_path.rfind(os.path.extsep)
        if ext_idx < 0:
            return

        ext = src_path[ext_idx:]
        if ext not in (".py",):
            return

        test_dir = next(
            (dir_path for dir_path in _test_dirs if src_path.startswith(dir_path)), None
        )
        if test_dir:
            is_test_file = os.path.basename(src_path).startswith("test_")
            src_relpath = os.path.relpath(src_path, ".")
            if is_test_file:
                # run all directory tests
                _run_test_path(src_relpath)
            else:
                # run all directory tests
                src_dir = os.path.dirname(src_relpath)
                _run_test_path(src_dir)
        else:
            # run all tests
            _run_test_path("")


if __name__ == "__main__":
    event_handler = Handler()
    observer = Observer()
    path = argv[1] if len(argv) >= 2 else "."
    print(f"watching {path}")
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
            if _scheduled_cmd is not None:
                print(_scheduled_cmd)
                os.system(_scheduled_cmd)
                _scheduled_cmd = None
    finally:
        observer.stop()
        observer.join()
