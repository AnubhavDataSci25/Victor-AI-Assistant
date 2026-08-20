from app.tools.filesystem.delete_tools import (
    DeleteDirectoryArgs,
    DeleteDirectoryTool,
    DeleteFileArgs,
    DeleteFileTool,
)
from app.tools.filesystem.path_validation import resolve_allowed_roots


def _roots(tmp_path):
    return resolve_allowed_roots([str(tmp_path)])


def test_delete_file_succeeds_and_verifies(tmp_path):
    f = tmp_path / "delete_me.txt"
    f.write_text("bye")

    tool = DeleteFileTool(_roots(tmp_path))
    args = DeleteFileArgs(path=str(f))
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert not f.exists()


def test_delete_file_missing_fails(tmp_path):
    tool = DeleteFileTool(_roots(tmp_path))
    result = tool.run(DeleteFileArgs(path=str(tmp_path / "missing.txt")))
    assert result.success is False
    assert result.error == "not_found"


def test_delete_file_on_directory_fails(tmp_path):
    tool = DeleteFileTool(_roots(tmp_path))
    result = tool.run(DeleteFileArgs(path=str(tmp_path)))
    assert result.success is False
    assert result.error == "not_a_file"


def test_delete_empty_directory_succeeds(tmp_path):
    d = tmp_path / "empty_dir"
    d.mkdir()

    tool = DeleteDirectoryTool(_roots(tmp_path))
    args = DeleteDirectoryArgs(path=str(d))
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert not d.exists()


def test_delete_non_empty_directory_without_recursive_fails(tmp_path):
    d = tmp_path / "full_dir"
    d.mkdir()
    (d / "file.txt").write_text("x")

    tool = DeleteDirectoryTool(_roots(tmp_path))
    result = tool.run(DeleteDirectoryArgs(path=str(d), recursive=False))

    assert result.success is False
    assert result.error == "not_empty"
    assert d.exists()


def test_delete_non_empty_directory_with_recursive_succeeds(tmp_path):
    d = tmp_path / "full_dir"
    d.mkdir()
    (d / "file.txt").write_text("x")
    (d / "sub").mkdir()

    tool = DeleteDirectoryTool(_roots(tmp_path))
    result = tool.run(DeleteDirectoryArgs(path=str(d), recursive=True))

    assert result.success is True
    assert not d.exists()


def test_delete_directory_outside_allowed_roots_fails(tmp_path):
    tool = DeleteDirectoryTool(_roots(tmp_path))
    result = tool.run(DeleteDirectoryArgs(path=str(tmp_path.parent), recursive=True))
    assert result.success is False
    assert result.error == "path_validation_failed"