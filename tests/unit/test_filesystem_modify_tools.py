from app.tools.filesystem.modify_tools import (
    CopyFileArgs,
    CopyFileTool,
    MoveFileArgs,
    MoveFileTool,
    RenameFileArgs,
    RenameFileTool,
)
from app.tools.filesystem.path_validation import resolve_allowed_roots


def _roots(tmp_path):
    return resolve_allowed_roots([str(tmp_path)])


def test_rename_file_succeeds_and_verifies(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("content")

    tool = RenameFileTool(_roots(tmp_path))
    args = RenameFileArgs(path=str(f), new_name="new.txt")
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert not f.exists()
    assert (tmp_path / "new.txt").read_text() == "content"


def test_rename_file_refuses_to_overwrite_destination(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("content")
    (tmp_path / "new.txt").write_text("existing")

    tool = RenameFileTool(_roots(tmp_path))
    result = tool.run(RenameFileArgs(path=str(f), new_name="new.txt"))

    assert result.success is False
    assert result.error == "already_exists"


def test_rename_file_rejects_path_separator_in_new_name(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("content")

    tool = RenameFileTool(_roots(tmp_path))
    result = tool.run(RenameFileArgs(path=str(f), new_name="../escape.txt"))

    assert result.success is False
    assert result.error == "path_validation_failed"


def test_copy_file_succeeds_and_verifies(tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("content")
    destination = tmp_path / "copy.txt"

    tool = CopyFileTool(_roots(tmp_path))
    args = CopyFileArgs(source=str(f), destination=str(destination))
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert f.exists()  # source untouched
    assert destination.read_text() == "content"


def test_copy_file_refuses_to_overwrite_destination(tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("content")
    destination = tmp_path / "copy.txt"
    destination.write_text("existing")

    tool = CopyFileTool(_roots(tmp_path))
    result = tool.run(CopyFileArgs(source=str(f), destination=str(destination)))

    assert result.success is False
    assert result.error == "already_exists"
    assert destination.read_text() == "existing"


def test_move_file_succeeds_and_verifies(tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("content")
    destination = tmp_path / "moved.txt"

    tool = MoveFileTool(_roots(tmp_path))
    args = MoveFileArgs(source=str(f), destination=str(destination))
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert not f.exists()
    assert destination.read_text() == "content"


def test_move_file_refuses_to_overwrite_destination(tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("content")
    destination = tmp_path / "moved.txt"
    destination.write_text("existing")

    tool = MoveFileTool(_roots(tmp_path))
    result = tool.run(MoveFileArgs(source=str(f), destination=str(destination)))

    assert result.success is False
    assert result.error == "already_exists"
    assert f.exists()  # untouched


def test_copy_and_move_reject_destination_outside_allowed_roots(tmp_path):
    f = tmp_path / "source.txt"
    f.write_text("content")
    outside = str(tmp_path.parent / "escaped.txt")

    copy_result = CopyFileTool(_roots(tmp_path)).run(
        CopyFileArgs(source=str(f), destination=outside)
    )
    move_result = MoveFileTool(_roots(tmp_path)).run(
        MoveFileArgs(source=str(f), destination=outside)
    )

    assert copy_result.success is False
    assert copy_result.error == "path_validation_failed"
    assert move_result.success is False
    assert move_result.error == "path_validation_failed"