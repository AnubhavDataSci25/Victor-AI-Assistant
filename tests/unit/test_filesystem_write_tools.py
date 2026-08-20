from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.write_tools import (
    AppendFileArgs,
    AppendFileTool,
    CreateDirectoryArgs,
    CreateDirectoryTool,
    CreateFileArgs,
    CreateFileTool,
    WriteFileArgs,
    WriteFileTool,
)


def _roots(tmp_path):
    return resolve_allowed_roots([str(tmp_path)])


def test_create_file_succeeds_and_verifies(tmp_path):
    tool = CreateFileTool(_roots(tmp_path))
    args = CreateFileArgs(path=str(tmp_path / "new.txt"), content="hi")

    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert (tmp_path / "new.txt").read_text() == "hi"


def test_create_file_refuses_to_overwrite(tmp_path):
    existing = tmp_path / "existing.txt"
    existing.write_text("original")

    tool = CreateFileTool(_roots(tmp_path))
    result = tool.run(CreateFileArgs(path=str(existing), content="new"))

    assert result.success is False
    assert result.error == "already_exists"
    assert existing.read_text() == "original"


def test_create_file_missing_parent_fails(tmp_path):
    tool = CreateFileTool(_roots(tmp_path))
    result = tool.run(CreateFileArgs(path=str(tmp_path / "nope" / "file.txt")))
    assert result.success is False
    assert result.error == "parent_not_found"


def test_write_file_overwrites_existing_content(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("old content")

    tool = WriteFileTool(_roots(tmp_path))
    args = WriteFileArgs(path=str(f), content="new content")
    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert f.read_text() == "new content"


def test_write_file_creates_if_missing(tmp_path):
    f = tmp_path / "brand_new.txt"
    tool = WriteFileTool(_roots(tmp_path))
    result = tool.run(WriteFileArgs(path=str(f), content="fresh"))
    assert result.success is True
    assert f.read_text() == "fresh"


def test_append_file_creates_if_missing(tmp_path):
    f = tmp_path / "log.txt"
    tool = AppendFileTool(_roots(tmp_path))
    tool.run(AppendFileArgs(path=str(f), content="line1\n"))
    tool.run(AppendFileArgs(path=str(f), content="line2\n"))
    assert f.read_text() == "line1\nline2\n"


def test_append_file_never_destroys_existing_content(tmp_path):
    f = tmp_path / "log.txt"
    f.write_text("original\n")
    tool = AppendFileTool(_roots(tmp_path))
    tool.run(AppendFileArgs(path=str(f), content="added\n"))
    assert f.read_text() == "original\nadded\n"


def test_create_directory_succeeds_and_verifies(tmp_path):
    tool = CreateDirectoryTool(_roots(tmp_path))
    args = CreateDirectoryArgs(path=str(tmp_path / "newdir"))

    result = tool.run(args)
    result = tool.verify(args, result)

    assert result.success is True
    assert (tmp_path / "newdir").is_dir()


def test_create_directory_idempotent_if_already_exists(tmp_path):
    existing = tmp_path / "existing_dir"
    existing.mkdir()
    tool = CreateDirectoryTool(_roots(tmp_path))
    result = tool.run(CreateDirectoryArgs(path=str(existing)))
    assert result.success is True


def test_create_directory_fails_if_path_is_a_file(tmp_path):
    f = tmp_path / "afile.txt"
    f.write_text("x")
    tool = CreateDirectoryTool(_roots(tmp_path))
    result = tool.run(CreateDirectoryArgs(path=str(f)))
    assert result.success is False
    assert result.error == "not_a_directory"


def test_all_write_tools_reject_paths_outside_allowed_roots(tmp_path):
    outside = str(tmp_path.parent / "outside.txt")
    for tool, args in [
        (CreateFileTool(_roots(tmp_path)), CreateFileArgs(path=outside)),
        (WriteFileTool(_roots(tmp_path)), WriteFileArgs(path=outside, content="x")),
        (AppendFileTool(_roots(tmp_path)), AppendFileArgs(path=outside, content="x")),
        (CreateDirectoryTool(_roots(tmp_path)), CreateDirectoryArgs(path=outside)),
    ]:
        result = tool.run(args)
        assert result.success is False
        assert result.error == "path_validation_failed"