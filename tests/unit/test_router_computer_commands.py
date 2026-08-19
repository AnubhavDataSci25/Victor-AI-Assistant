from app.brain.router import Router


def test_open_application_command():
    router = Router()
    outcome = router.route("open notepad")
    assert outcome.kind == "tool_call"
    assert outcome.tool_call.tool == "open_application"
    assert outcome.tool_call.arguments["application"] == "notepad"


def test_close_application_command():
    router = Router()
    outcome = router.route("close notepad")
    assert outcome.tool_call.tool == "close_application"
    assert outcome.tool_call.arguments["application"] == "notepad"


def test_screenshot_command():
    router = Router()
    outcome = router.route("take a screenshot")
    assert outcome.tool_call.tool == "take_screenshot"
    assert outcome.tool_call.arguments == {}


def test_switch_window_command():
    router = Router()
    outcome = router.route("switch to Chrome")
    assert outcome.tool_call.tool == "switch_window"
    assert outcome.tool_call.arguments["title"] == "Chrome"


def test_focus_window_command():
    router = Router()
    outcome = router.route("focus Notepad")
    assert outcome.tool_call.tool == "focus_window"
    assert outcome.tool_call.arguments["title"] == "Notepad"


def test_hotkey_command_splits_on_plus():
    router = Router()
    outcome = router.route("hotkey ctrl+shift+esc")
    assert outcome.tool_call.tool == "hotkey"
    assert outcome.tool_call.arguments["keys"] == ["ctrl", "shift", "esc"]


def test_press_key_command():
    router = Router()
    outcome = router.route("press enter")
    assert outcome.tool_call.tool == "press_key"
    assert outcome.tool_call.arguments["key"] == "enter"


def test_type_text_command():
    router = Router()
    outcome = router.route("type hello there")
    assert outcome.tool_call.tool == "type_text"
    assert outcome.tool_call.arguments["text"] == "hello there"