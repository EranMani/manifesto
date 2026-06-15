from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_claude_instructions_stay_lean_and_keep_required_controls() -> None:
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(text.encode("utf-8")) <= 20_878
    for required in (
        "explicit approval",
        "Claude-direct is the default",
        "Files To Modify Or Add",
        "SPLIT_REQUIRED",
        "claude_budget.py",
        "Cache-read tokens",
        "Never label a delegated commit as",
    ):
        assert required in text
