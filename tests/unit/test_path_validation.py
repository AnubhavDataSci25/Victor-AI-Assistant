import pytest

from app.tools.filesystem.path_validation import (
    PathValidationError,
    resolve_allowed_roots,
    validate_path,
)


def test_path_inside_allowed_root_is_accepted(tmp_path):
    roots = resolve_allowed_roots([str(tmp_path)])
    sub = tmp_path / "sub"
    sub.mkdir()
    result = validate_path(str(sub), roots)
    assert result == sub.resolve()


def test_path_outside_allowed_root_is_rejected(tmp_path):
    roots = resolve_allowed_roots([str(tmp_path)])
    outside = tmp_path.parent / "definitely_outside"
    with pytest.raises(PathValidationError):
        validate_path(str(outside), roots)


def test_directory_traversal_is_rejected(tmp_path):
    roots = resolve_allowed_roots([str(tmp_path)])
    traversal = str(tmp_path / "sub" / ".." / ".." / "etc" / "passwd")
    with pytest.raises(PathValidationError):
        validate_path(traversal, roots)


def test_empty_path_is_rejected(tmp_path):
    roots = resolve_allowed_roots([str(tmp_path)])
    with pytest.raises(PathValidationError):
        validate_path("", roots)


def test_tilde_is_expanded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    roots = resolve_allowed_roots(["~"])
    assert roots[0] == tmp_path.resolve()