import os
from typing import Iterator

import pytest
from packman.utils.operation import Operation


class MockError(Exception):
    pass


def _raise_error_in_context(op: Operation) -> None:
    try:
        with op:
            raise MockError("error!")
    except MockError:
        pass
    else:
        assert False, "error should be raised"


def _trigger_restore(op: Operation, use_context: bool) -> None:
    if use_context:
        _raise_error_in_context(op)
    else:
        op.restore()


@pytest.mark.parametrize("use_context", [True, False])
@pytest.mark.parametrize("data", ["the data"])
def test_copy_file(file_paths: Iterator[str], data: str, use_context: bool) -> None:
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
    _trigger_restore(op, use_context)
    assert not os.path.exists(dest_path), "dest file should be deleted after restore"


@pytest.mark.parametrize("old_data", ["old data"])
@pytest.mark.parametrize("new_data", ["new data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_copy_and_overwrite_file(
    file_paths: Iterator[str], new_data: str, old_data: str, use_context: bool
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
    _trigger_restore(op, use_context)
    assert os.path.exists(dest_path), "dest file should still exist after restore"
    with open(dest_path, "r") as fp:
        assert fp.read() == old_data, "dest file should contain original contents"
