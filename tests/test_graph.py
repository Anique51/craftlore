from pathlib import Path
from types import SimpleNamespace

import pytest

from app.graph import nodes

DATA_READY = Path("data/recipes.json").exists() and Path("data/items.json").exists()


class FakeLLM:
    def __init__(self, *replies):
        self.replies = list(replies)

    def invoke(self, messages):
        return SimpleNamespace(content=self.replies.pop(0))


@pytest.fixture
def fake_llm(monkeypatch):
    def install(*replies):
        llm = FakeLLM(*replies)
        monkeypatch.setattr(nodes, "get_llm", lambda: llm)
        return llm
    return install


def test_router_picks_mechanics(fake_llm):
    fake_llm("mechanics")
    assert nodes.router({"question": "How do I craft a beacon?"})["route"] == "mechanics"


def test_router_defaults_to_lore_on_unexpected_reply(fake_llm):
    fake_llm("I think this is about lore")
    assert nodes.router({"question": "Who is Notch?"})["route"] == "lore"


def test_verify_accepts_supported_answer(fake_llm):
    fake_llm("SUPPORTED")
    out = nodes.verify({"answer": "It explodes [1].", "context": [], "attempts": 1})
    assert out["verified"] is True


def test_verify_failure_on_last_attempt_adds_notice(fake_llm):
    fake_llm("The date 1999 is unsupported.")
    out = nodes.verify({"answer": "bad", "context": [], "attempts": nodes.MAX_ATTEMPTS})
    assert out["verified"] is False
    assert out["answer"].startswith("I could not fully verify")


def test_retry_loop_stops_at_max_attempts():
    assert nodes.after_verify({"verified": False, "attempts": 1}) == "answer"
    assert nodes.after_verify({"verified": False, "attempts": nodes.MAX_ATTEMPTS}) == "end"
    assert nodes.after_verify({"verified": True, "attempts": 1}) == "end"


@pytest.mark.skipif(not DATA_READY, reason="recipe data not downloaded (data/ is gitignored)")
def test_mechanics_puts_recipe_into_context(fake_llm):
    fake_llm("beacon")
    out = nodes.mechanics({"question": "What do I need for a beacon?"})
    assert "Nether Star" in out["context"][0]["text"]
    assert out["context"][0]["url"].startswith("https://github.com/PrismarineJS")
