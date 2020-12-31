import os
import shutil


def remove(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except FileNotFoundError:
        ...
    dir = os.path.dirname(path)
    try:
        siblings = os.listdir(dir)
    except FileNotFoundError:
        ...
    else:
        if not any(siblings):
            remove(dir)
