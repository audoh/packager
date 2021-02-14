from typing import Union


def get_version_name(version: Union[str, None]) -> str:
    return version if version is not None else "unknown"
