from app.brain.router import Router


def test_read_file_command():
    router = Router()
    outcome = router.route("read /tmp/notes.txt")
    assert outcome.tool_call.tool == "read_file"
    assert outcome.tool_call.arguments["path"] == "/tmp/notes.txt"


def test_create_directory_command():
    router = Router()
    outcome = router.route("create directory /tmp/newdir")
    assert outcome.tool_call.tool == "create_directory"
    assert outcome.tool_call.arguments["path"] == "/tmp/newdir"


def test_delete_file_command():
    router = Router()
    outcome = router.route("delete file /tmp/old.txt")
    assert outcome.tool_call.tool == "delete_file"
    assert outcome.tool_call.arguments["path"] == "/tmp/old.txt"


def test_delete_directory_command():
    router = Router()
    outcome = router.route("delete folder /tmp/olddir")
    assert outcome.tool_call.tool == "delete_directory"
    assert outcome.tool_call.arguments["path"] == "/tmp/olddir"


def test_copy_file_command():
    router = Router()
    outcome = router.route("copy /tmp/a.txt to /tmp/b.txt")
    assert outcome.tool_call.tool == "copy_file"
    assert outcome.tool_call.arguments["source"] == "/tmp/a.txt"
    assert outcome.tool_call.arguments["destination"] == "/tmp/b.txt"


def test_move_file_command():
    router = Router()
    outcome = router.route("move /tmp/a.txt to /tmp/b.txt")
    assert outcome.tool_call.tool == "move_file"


def test_rename_file_command():
    router = Router()
    outcome = router.route("rename /tmp/a.txt to b.txt")
    assert outcome.tool_call.tool == "rename_file"
    assert outcome.tool_call.arguments["new_name"] == "b.txt"


def test_find_file_command():
    router = Router()
    outcome = router.route("find config.yaml in /tmp")
    assert outcome.tool_call.tool == "find_file"
    assert outcome.tool_call.arguments["filename"] == "config.yaml"
    assert outcome.tool_call.arguments["path"] == "/tmp"


def test_search_files_command():
    router = Router()
    outcome = router.route("search for report in /tmp")
    assert outcome.tool_call.tool == "search_files"
    assert outcome.tool_call.arguments["query"] == "report"