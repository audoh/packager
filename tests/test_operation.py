import os
from typing import Iterator, Union

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
        op.abort()


@pytest.mark.parametrize("start_data", [b"start data"])
@pytest.mark.parametrize("end_data", [b"end data"])
def test_backup_file_should_be_cleaned_up_on_close(
    file_paths: Iterator[str], start_data: bytes, end_data: bytes
) -> None:
    path = next(file_paths)
    with open(path, "wb") as fp:
        fp.write(start_data)

    op = Operation()
    backup_path = op.backup_file(path)

    assert os.path.exists(backup_path), "backup file should be created"
    with open(backup_path, "rb") as fp:
        assert (
            fp.read() == start_data
        ), "backup file should contain original file contents"

    with open(path, "wb") as fp:
        fp.write(end_data)

    op.close()
    assert not os.path.exists(
        backup_path
    ), "backup file should be deleted after restore"


@pytest.mark.parametrize("start_data", [b"start data"])
@pytest.mark.parametrize("end_data", [b"end data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_backup_file_should_be_restored_and_cleaned_up_on_error(
    file_paths: Iterator[str], start_data: bytes, end_data: bytes, use_context: bool
) -> None:
    path = next(file_paths)
    with open(path, "wb") as fp:
        fp.write(start_data)

    op = Operation()
    backup_path = op.backup_file(path)

    assert os.path.exists(backup_path), "backup file should be created"
    with open(backup_path, "rb") as fp:
        assert (
            fp.read() == start_data
        ), "backup file should contain original file contents"

    with open(path, "wb") as fp:
        fp.write(end_data)

    _trigger_restore(op=op, use_context=use_context)
    with open(path, "rb") as fp:
        assert fp.read() == start_data, "file contents should be restored"
    assert not os.path.exists(
        backup_path
    ), "backup file should be deleted after restore"


@pytest.mark.parametrize("data", [b"the data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_copy_file(file_paths: Iterator[str], data: bytes, use_context: bool) -> None:
    src_path = next(file_paths)
    dest_path = next(file_paths)
    with open(src_path, "wb") as fp:
        fp.write(data)

    op = Operation()
    op.copy_file(src_path, dest_path)

    # Test copy
    assert os.path.exists(dest_path), "dest file should be created"
    with open(dest_path, "rb") as fp:
        assert fp.read() == data, "dest file should have src contents"

    # Test rollback
    _trigger_restore(op, use_context)
    assert not os.path.exists(dest_path), "dest file should be deleted after restore"


@pytest.mark.parametrize("old_data", [b"old data"])
@pytest.mark.parametrize("new_data", [b"new data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_copy_and_overwrite_file(
    file_paths: Iterator[str], new_data: bytes, old_data: bytes, use_context: bool
) -> None:
    src_path = next(file_paths)
    dest_path = next(file_paths)
    with open(src_path, "wb") as fp:
        fp.write(new_data)
    with open(dest_path, "wb") as fp:
        fp.write(old_data)

    op = Operation()
    op.copy_file(src_path, dest_path)

    # Test copy
    assert os.path.exists(dest_path), "dest file should exist"
    with open(dest_path, "rb") as fp:
        assert fp.read() == new_data, "dest file should have src contents"

    # Test rollback
    _trigger_restore(op, use_context)
    assert os.path.exists(dest_path), "dest file should still exist after restore"
    with open(dest_path, "rb") as fp:
        assert fp.read() == old_data, "dest file should contain original contents"


@pytest.mark.parametrize("data", [b"the data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_remove_file(file_paths: Iterator[str], data: bytes, use_context: bool) -> None:
    path = next(file_paths)
    with open(path, "wb") as fp:
        fp.write(data)

    op = Operation()
    op.remove_file(path)

    # Test removal
    assert not os.path.exists(path), "file should no longer exist"

    # Test rollback
    _trigger_restore(op, use_context=use_context)
    assert os.path.exists(path), "file should exist again after restore"
    with open(path, "rb") as fp:
        assert fp.read() == data, "file should contain original contents"


@pytest.mark.parametrize("data", ["the data", b"the data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_write_file(
    file_paths: Iterator[str], data: Union[bytes, str], use_context: bool
) -> None:
    path = next(file_paths)
    op = Operation()
    op.write_file(path, data)

    # Test write
    data = bytes(data, encoding="utf-8") if isinstance(data, str) else data
    assert os.path.exists(path), "file should exist"
    with open(path, "rb") as fp:
        assert fp.read() == data, "file should contain contents"

    # Test rollback
    _trigger_restore(op, use_context=use_context)
    assert not os.path.exists(path), "file should no longer exist"


@pytest.mark.parametrize("old_data", [b"the old data"])
@pytest.mark.parametrize("new_data", ["the data", b"the data"])
@pytest.mark.parametrize("use_context", [True, False])
def test_write_to_existing_file(
    file_paths: Iterator[str],
    old_data: bytes,
    new_data: Union[bytes, str],
    use_context: bool,
) -> None:
    path = next(file_paths)
    with open(path, "wb") as fp:
        fp.write(old_data)

    op = Operation()
    op.write_file(path, new_data)

    # Test write
    new_data = (
        bytes(new_data, encoding="utf-8") if isinstance(new_data, str) else new_data
    )
    assert os.path.exists(path), "file should exist"
    with open(path, "rb") as fp:
        assert fp.read() == new_data, "file should contain contents"

    # Test rollback
    _trigger_restore(op, use_context=use_context)
    with open(path, "rb") as fp:
        assert fp.read() == old_data, "file should contain original contents"
