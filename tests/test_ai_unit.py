"""Pure-function tests: prompt construction and context truncation."""

from ai import build_prompt, truncate_context, PROMPTS, VALID_ACTIONS, NullProvider


def test_build_prompt_includes_selected_text():
    out = build_prompt("rewrite", "hello there", None)
    assert "hello there" in out
    assert "Document context" not in out


def test_build_prompt_adds_context_block():
    out = build_prompt("rewrite", "hello", "wider document text")
    assert "Document context" in out
    assert "wider document text" in out


def test_build_prompt_unknown_action_fallback():
    out = build_prompt("mystery", "some text", None)
    assert "some text" in out


def test_prompts_cover_core_actions():
    required = {"summarize", "rewrite", "translate", "restructure", "expand", "grammar"}
    assert required.issubset(PROMPTS.keys())
    assert required.issubset(VALID_ACTIONS)


def test_truncate_context_passthrough_short():
    assert truncate_context("short", "sel", limit=100) == "short"


def test_truncate_context_none_returns_none():
    assert truncate_context("", "sel") is None
    assert truncate_context(None, "sel") is None


def test_truncate_context_windows_around_selection():
    selected = "NEEDLE"
    context = "A" * 3000 + selected + "B" * 3000
    out = truncate_context(context, selected, limit=1000)
    assert selected in out
    # Ellipsis on both sides since we're in the interior
    assert out.startswith("…")
    assert out.endswith("…")
    assert len(out) <= 1002  # limit + two ellipsis chars


def test_truncate_context_head_when_selection_missing():
    context = "A" * 5000
    out = truncate_context(context, "NOT-IN-DOC", limit=100)
    assert len(out) == 100
    assert out == "A" * 100


def test_null_provider_stream_matches_complete_output():
    provider = NullProvider("alpha beta gamma")
    assert "".join(provider.stream_complete("ignored prompt")) == "alpha beta gamma"


def test_null_provider_exposes_metadata():
    provider = NullProvider("alpha beta gamma")
    assert provider.provider_name == "null"
    assert provider.model_name == "null-provider"
