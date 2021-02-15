import os

from packman.utils.operation import Operation


def test_can_copy_file(mock_files: str) -> None:
    src_path = os.path.join(mock_files, "src.txt")
    dest_path = os.path.join(mock_files, "dest.txt")
    with open(src_path, "w") as fp:
        fp.write("mocktext")

    op = Operation()
    op.copy_file(src_path, dest_path)

    assert os.path.exists(dest_path), "dest file should be created"
    with open(dest_path, "r") as fp:
        assert fp.read() == "mocktext", "dest file should have src contents"


def test_can_overwrite_file(mock_files: str) -> None:
    src_path = os.path.join(mock_files, "src.txt")
    dest_path = os.path.join(mock_files, "dest.txt")
    with open(src_path, "w") as fp:
        fp.write("mocktext")
    with open(dest_path, "w") as fp:
        fp.write("otherfile")

    op = Operation()
    op.copy_file(src_path, dest_path)

    assert os.path.exists(dest_path), "dest file should exist"
    with open(dest_path, "r") as fp:
        assert fp.read() == "mocktext", "dest file should have src contents"


def test_backs_up_overwritten_file(mock_files: str) -> None:
    src_path = os.path.join(mock_files, "src.txt")
    dest_path = os.path.join(mock_files, "dest.txt")
    with open(src_path, "w") as fp:
        fp.write("mocktext")
    with open(dest_path, "w") as fp:
        fp.write("otherfile")

    op = Operation()
    op.copy_file(src_path, dest_path)

    assert dest_path in op.backups, "operation should store backup path"
    assert os.path.exists(
        op.backups[dest_path]
    ), "operation should copy overwitten file to the backup path"
