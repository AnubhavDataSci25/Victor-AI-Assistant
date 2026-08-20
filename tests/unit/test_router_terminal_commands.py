from app.brain.router import Router


def test_run_command_via_explicit_prefix():
    router = Router()
    outcome = router.route("run_command pytest")
    assert outcome.tool_call.tool == "run_command"
    assert outcome.tool_call.arguments["command"] == "pytest"


def test_run_command_via_natural_phrase():
    router = Router()
    outcome = router.route("run pytest -v")
    assert outcome.tool_call.tool == "run_command"
    assert outcome.tool_call.arguments["command"] == "pytest -v"


def test_run_python_command():
    router = Router()
    outcome = router.route("run_python print(1+1)")
    assert outcome.tool_call.tool == "run_python"
    assert outcome.tool_call.arguments["code"] == "print(1+1)"


def test_start_process_command():
    router = Router()
    outcome = router.route("start process npm run dev")
    assert outcome.tool_call.tool == "start_process"
    assert outcome.tool_call.arguments["command"] == "npm run dev"


def test_start_process_without_command_asks_for_command():
    router = Router()
    outcome = router.route("start process")
    assert outcome.kind == "conversation"
    assert "what to start" in outcome.reply.lower()


def test_stop_process_command():
    router = Router()
    outcome = router.route("stop process 1234")
    assert outcome.tool_call.tool == "stop_process"
    assert outcome.tool_call.arguments["pid"] == 1234


def test_stop_process_underscore_form():
    router = Router()
    outcome = router.route("stop_process 5678")
    assert outcome.tool_call.arguments["pid"] == 5678


def test_bare_low_risk_shell_command_routes_to_run_command():
    router = Router()
    outcome = router.route("python3 --version")
    assert outcome.tool_call.tool == "run_command"
    assert outcome.tool_call.arguments["command"] == "python3 --version"


def test_bare_blocked_shell_command_routes_to_run_command_for_validator():
    router = Router()
    outcome = router.route("shutdown")
    assert outcome.tool_call.tool == "run_command"
    assert outcome.tool_call.arguments["command"] == "shutdown"
