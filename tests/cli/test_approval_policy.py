"""Which tools the CLI stops to ask about, per mode."""

from cli.commands.agent import _ALWAYS_ASK_TOOLS, _EDIT_TOOLS, _Mode, _should_ask


def asks(tool, mode, approved=None, always_ask=False):
    return _should_ask(tool, mode, approved or set(), always_ask)


def test_shell_is_asked_about_even_in_yolo():
    """Choosing yolo says the prompts are tedious, not that an unread shell
    command may run on the user's machine."""
    for tool in ("run_shell", "system_propose", "system_confirm", "git_commit"):
        assert asks(tool, _Mode.YOLO), f"{tool} slipped through yolo"


def test_shell_is_asked_about_in_auto_edit():
    """system_propose used to sit in _EDIT_TOOLS, so auto-edit ran server
    shell silently while run_shell still stopped to ask."""
    assert asks("system_propose", _Mode.AUTO_EDIT)
    assert asks("run_shell", _Mode.AUTO_EDIT)


def test_the_two_shell_tools_are_treated_alike():
    """system_propose is run_shell under another name; a policy that splits
    them just moves the risk to whichever one the model happens to pick."""
    for mode in (_Mode.DEFAULT, _Mode.CONFIRM_RISKY, _Mode.AUTO_EDIT, _Mode.YOLO):
        assert asks("run_shell", mode) == asks("system_propose", mode), mode


def test_auto_edit_still_skips_file_edits():
    assert not asks("edit_file", _Mode.AUTO_EDIT)
    assert not asks("write_file", _Mode.AUTO_EDIT)


def test_file_edits_are_asked_about_outside_auto_edit():
    assert asks("edit_file", _Mode.DEFAULT)
    assert asks("write_file", _Mode.CONFIRM_RISKY)


def test_reads_are_never_asked_about():
    for tool in ("read_file", "list_directory", "git_status", "web_search"):
        assert not asks(tool, _Mode.DEFAULT)


def test_plan_mode_asks_nothing_because_nothing_runs():
    for tool in ("run_shell", "write_file", "system_propose"):
        assert not asks(tool, _Mode.PLAN)


def test_an_explicit_always_approve_is_honoured():
    """The user picked this tool by name after seeing what it wanted to do —
    that is a stronger signal than any blanket mode."""
    assert not asks("run_shell", _Mode.DEFAULT, approved={"run_shell"})


def test_the_always_ask_set_is_actually_consulted():
    """It was defined and never referenced, so yolo auto-approved everything
    it names."""
    for tool in _ALWAYS_ASK_TOOLS:
        assert asks(tool, _Mode.YOLO), f"{tool} is in _ALWAYS_ASK_TOOLS but not asked"


def test_the_two_sets_do_not_overlap():
    """A tool in both would be asked about and auto-approved at once; the
    order decides silently."""
    assert not (_ALWAYS_ASK_TOOLS & _EDIT_TOOLS)


def test_the_servers_verdict_overrides_yolo():
    """The point of always_ask: a tool the server flags is not auto-approved
    here even if this CLI has never heard of it."""
    assert asks("some_new_dangerous_tool", _Mode.YOLO, always_ask=True)
    assert asks("some_new_dangerous_tool", _Mode.AUTO_EDIT, always_ask=True)


def test_a_tool_this_cli_does_not_know_is_still_gated_by_the_server():
    """The old design needed every client to learn each new dangerous tool by
    name; until then it auto-approved them."""
    assert not asks("brand_new_tool", _Mode.YOLO)
    assert asks("brand_new_tool", _Mode.YOLO, always_ask=True)


def test_the_servers_verdict_does_not_override_plan_mode():
    """Plan mode executes nothing, so there is nothing to approve."""
    assert not asks("run_shell", _Mode.PLAN, always_ask=True)


def test_an_explicit_always_approve_still_wins():
    """Chosen by name after seeing what the tool wanted to do — a stronger
    signal than a blanket verdict."""
    assert not asks("run_shell", _Mode.YOLO, approved={"run_shell"}, always_ask=True)


def test_the_local_floor_covers_the_dangerous_tools_when_the_server_is_silent():
    """An older server sends no verdict; the CLI must not fall open."""
    for tool in ("browser_evaluate", "browser_connect", "download_file"):
        assert asks(tool, _Mode.YOLO), f"{tool} auto-approved with no server verdict"
