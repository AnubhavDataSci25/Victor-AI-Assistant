from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.read_tools import (
    FindFileArgs,
    FindFileTool,
    ReadFileArgs,
    ReadFileTool,
    SearchFilesArgs,
    SearchFilesTool,
)


def _roots(tmp_path):
    return resolve_allowed_roots([str(tmp_path)])


def test_search_files_finds_substring_matches(tmp_path):
    (tmp_path / "report_2024.txt").write_text("a")
    (tmp_path / "report_2025.txt").write_text("a")
    (tmp_path / "notes.txt").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "report_archive.txt").write_text("a")

    tool = SearchFilesTool(_roots(tmp_path))
    result = tool.run(SearchFilesArgs(path=str(tmp_path), query="report"))

    assert result.success is True
    assert len(result.data["matches"]) == 3


def test_search_files_outside_allowed_roots_fails(tmp_path):
    tool = SearchFilesTool(_roots(tmp_path))
    result = tool.run(SearchFilesArgs(path=str(tmp_path.parent), query="x"))
    assert result.success is False
    assert result.error == "path_validation_failed"


def test_search_files_respects_max_results(tmp_path):
    for i in range(5):
        (tmp_path / f"match_{i}.txt").write_text("a")
    tool = SearchFilesTool(_roots(tmp_path))
    result = tool.run(SearchFilesArgs(path=str(tmp_path), query="match", max_results=2))
    assert len(result.data["matches"]) == 2
    assert result.data["truncated"] is True


def test_find_file_exact_match(tmp_path):
    (tmp_path / "config.yaml").write_text("a")
    (tmp_path / "config.yaml.bak").write_text("a")

    tool = FindFileTool(_roots(tmp_path))
    result = tool.run(FindFileArgs(path=str(tmp_path), filename="config.yaml"))

    assert result.success is True
    assert len(result.data["matches"]) == 1


def test_find_file_not_found(tmp_path):
    tool = FindFileTool(_roots(tmp_path))
    result = tool.run(FindFileArgs(path=str(tmp_path), filename="nope.txt"))
    assert result.success is False
    assert result.error == "not_found"


def test_read_file_returns_content(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello world")

    tool = ReadFileTool(_roots(tmp_path), max_read_bytes=1_000_000)
    result = tool.run(ReadFileArgs(path=str(f)))

    assert result.success is True
    assert result.data["content"] == "hello world"


def test_read_file_missing_fails(tmp_path):
    tool = ReadFileTool(_roots(tmp_path), max_read_bytes=1_000_000)
    result = tool.run(ReadFileArgs(path=str(tmp_path / "missing.txt")))
    assert result.success is False
    assert result.error == "not_found"


def test_read_file_directory_fails(tmp_path):
    tool = ReadFileTool(_roots(tmp_path), max_read_bytes=1_000_000)
    result = tool.run(ReadFileArgs(path=str(tmp_path)))
    assert result.success is False
    assert result.error == "not_a_file"


def test_read_file_over_size_limit_fails(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 100)

    tool = ReadFileTool(_roots(tmp_path), max_read_bytes=10)
    result = tool.run(ReadFileArgs(path=str(f)))

    assert result.success is False
    assert result.error == "file_too_large"


def test_read_file_outside_allowed_roots_fails(tmp_path):
    tool = ReadFileTool(_roots(tmp_path), max_read_bytes=1_000_000)
    result = tool.run(ReadFileArgs(path=str(tmp_path.parent / "etc" / "passwd")))
    assert result.success is False
    assert result.error == "path_validation_failed"