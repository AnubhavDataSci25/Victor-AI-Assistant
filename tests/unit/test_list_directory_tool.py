from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.tool import ListDirectoryArgs, ListDirectoryTool


def _tool(tmp_path):
    return ListDirectoryTool(allowed_roots=resolve_allowed_roots([str(tmp_path)]))


def test_lists_files_and_directories(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    (tmp_path / "subdir").mkdir()

    tool = _tool(tmp_path)
    result = tool.run(ListDirectoryArgs(path=str(tmp_path)))

    assert result.success is True
    assert "a.txt" in result.data["entries"]
    assert "subdir/" in result.data["entries"]


def test_nonexistent_directory_fails_cleanly(tmp_path):
    tool = _tool(tmp_path)
    result = tool.run(ListDirectoryArgs(path=str(tmp_path / "nope")))

    assert result.success is False
    assert result.error == "not_found"


def test_file_path_instead_of_directory_fails_cleanly(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hi")

    tool = _tool(tmp_path)
    result = tool.run(ListDirectoryArgs(path=str(file_path)))

    assert result.success is False
    assert result.error == "not_a_directory"


def test_path_outside_allowed_roots_fails_cleanly(tmp_path):
    outside = tmp_path.parent
    tool = _tool(tmp_path)
    result = tool.run(ListDirectoryArgs(path=str(outside)))

    assert result.success is False
    assert result.error == "path_validation_failed"