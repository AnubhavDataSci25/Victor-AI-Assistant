from app.brain.router import Router


def test_small_talk_does_not_produce_tool_call():
    router = Router()
    outcome = router.route("How are you?")
    assert outcome.kind == "conversation"
    assert outcome.tool_call is None
    assert "well" in outcome.reply.lower()


def test_list_directory_natural_phrase_produces_tool_call():
    router = Router()
    outcome = router.route("list files in /tmp")
    assert outcome.kind == "tool_call"
    assert outcome.tool_call.tool == "list_directory"
    assert outcome.tool_call.arguments["path"] == "/tmp"


def test_list_directory_explicit_command_produces_tool_call():
    router = Router()
    outcome = router.route("list_directory /tmp")
    assert outcome.kind == "tool_call"
    assert outcome.tool_call.arguments["path"] == "/tmp"


def test_unrecognized_input_is_conversational_not_a_tool_call():
    router = Router()
    outcome = router.route("please delete everything")
    assert outcome.kind == "conversation"
    assert outcome.tool_call is None


def test_empty_input_does_not_crash():
    router = Router()
    outcome = router.route("   ")
    assert outcome.kind == "conversation"