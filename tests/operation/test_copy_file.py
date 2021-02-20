import os
from typing import Iterator

import pytest
from packman.utils.operation import Operation


@pytest.mark.parametrize("data", ["the data"])
def test_copy_file(file_paths: Iterator[str], data: str) -> None:
    src_path = next(file_paths)
    dest_path = next(file_paths)
    with open(src_path, "w") as fp:
        fp.write(data)

    op = Operation()
    op.copy_file(src_path, dest_path)

    # Test copy
    assert os.path.exists(dest_path), "dest file should be created"
    with open(dest_path, "r") as fp:
        assert fp.read() == data, "dest file should have src contents"

    # Test rollback
    op.restore()
    assert not os.path.exists(dest_path), "dest file should be deleted after restore"


@pytest.mark.parametrize("new_data,old_data", [("new data", "old data")])
def test_copy_and_overwrite_file(
    file_paths: Iterator[str], new_data: str, old_data: str
) -> None:
    src_path = next(file_paths)
    dest_path = next(file_paths)
    with open(src_path, "w") as fp:
        fp.write(new_data)
    with open(dest_path, "w") as fp:
        fp.write(old_data)

    op = Operation()
    op.copy_file(src_path, dest_path)

    # Test copy
    assert os.path.exists(dest_path), "dest file should exist"
    with open(dest_path, "r") as fp:
        assert fp.read() == new_data, "dest file should have src contents"

    # Test rollback
    op.restore()
    assert os.path.exists(dest_path), "dest file should still exist"
    with open(dest_path, "r") as fp:
        assert fp.read() == old_data
