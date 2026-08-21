from app.brain.router import Router


def test_open_url_command():
    router = Router()
    outcome = router.route("go to https://example.com")
    assert outcome.tool_call.tool == "open_url"
    assert outcome.tool_call.arguments["url"] == "https://example.com"


def test_open_url_explicit_prefix():
    router = Router()
    outcome = router.route("open_url https://example.com")
    assert outcome.tool_call.tool == "open_url"


def test_search_web_command():
    router = Router()
    outcome = router.route("search the web for python tutorials")
    assert outcome.tool_call.tool == "search_web"
    assert outcome.tool_call.arguments["query"] == "python tutorials"


def test_read_page_command():
    router = Router()
    outcome = router.route("read the page")
    assert outcome.tool_call.tool == "read_page"
    assert outcome.tool_call.arguments == {}


def test_extract_text_command():
    router = Router()
    outcome = router.route("extract_text h1")
    assert outcome.tool_call.tool == "extract_text"
    assert outcome.tool_call.arguments["selector"] == "h1"


def test_click_element_command():
    router = Router()
    outcome = router.route("click #submit")
    assert outcome.tool_call.tool == "click_element"
    assert outcome.tool_call.arguments["selector"] == "#submit"


def test_type_into_page_command():
    router = Router()
    outcome = router.route("type_into_page #search :: hello world")
    assert outcome.tool_call.tool == "type_into_page"
    assert outcome.tool_call.arguments["selector"] == "#search"
    assert outcome.tool_call.arguments["text"] == "hello world"


def test_scroll_page_command():
    router = Router()
    outcome = router.route("scroll down")
    assert outcome.tool_call.tool == "scroll_page"
    assert outcome.tool_call.arguments["direction"] == "down"


def test_go_back_and_forward_commands():
    router = Router()
    assert router.route("go back").tool_call.tool == "go_back"
    assert router.route("go forward").tool_call.tool == "go_forward"


def test_open_tab_command_does_not_collide_with_open_application():
    router = Router()
    outcome = router.route("open tab https://example.com")
    assert outcome.tool_call.tool == "open_tab"
    assert outcome.tool_call.arguments["url"] == "https://example.com"


def test_open_tab_without_url():
    router = Router()
    outcome = router.route("new tab")
    assert outcome.tool_call.tool == "open_tab"
    assert outcome.tool_call.arguments["url"] is None


def test_close_tab_command():
    router = Router()
    outcome = router.route("close tab 2")
    assert outcome.tool_call.tool == "close_tab"
    assert outcome.tool_call.arguments["tab_id"] == 2


def test_screenshot_page_command_distinct_from_screenshot():
    router = Router()
    outcome = router.route("screenshot the page")
    assert outcome.tool_call.tool == "screenshot_page"

    # plain "screenshot" still maps to the computer-control tool
    outcome2 = router.route("take a screenshot")
    assert outcome2.tool_call.tool == "take_screenshot"


def test_open_application_still_works_after_adding_open_tab():
    router = Router()
    outcome = router.route("open notepad")
    assert outcome.tool_call.tool == "open_application"
    assert outcome.tool_call.arguments["application"] == "notepad"