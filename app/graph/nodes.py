from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import CraftState
from app.llm import get_llm
from app.retrieval.bm25 import load_keyword_index
from app.retrieval.hybrid import search
from app.retrieval.store import get_vectorstore
from app.tools.recipes import lookup_recipe, recipe_layout

MAX_ATTEMPTS = 2
TOP_N = 5
RECIPE_SOURCE = "https://github.com/PrismarineJS/minecraft-data"

ROUTER_PROMPT = (
    "Classify the user's Minecraft question. Reply with exactly one word.\n\n"
    "Reply 'mechanics' ONLY if the user wants the crafting recipe or the ingredients "
    "needed to craft one specific item they own or want to build. Examples:\n"
    "- What ingredients do I need for a stone pickaxe?\n"
    "- How do I craft a fishing rod?\n\n"
    "Reply 'lore' for everything else. This includes what a mob drops, where something "
    "is found, how a block forms in the world, and how a structure is built in the game. "
    "Examples:\n"
    "- What does a skeleton drop when it dies?\n"
    "- Where do endermen spawn?"
)
EXTRACT_PROMPT = (
    "Extract the Minecraft item name the user wants a recipe for. "
    "Reply with only the item name in lowercase, with no punctuation. Example: beacon"
)
ANSWER_PROMPT = (
    "You answer Minecraft questions using ONLY the numbered sources below.\n"
    "- Cite the source number for each fact, like [1].\n"
    "- If the sources do not answer the question, say you don't know. Do not guess.\n"
    "- Keep the answer under 120 words.\n\n"
    "Sources:\n{sources}"
)
VERIFY_PROMPT = (
    "You are a strict fact checker.\n\nSources:\n{sources}\n\nAnswer:\n{answer}\n\n"
    "List every factual claim in the answer that the sources do not support. "
    "If every claim is supported, reply with only the word SUPPORTED."
)


@lru_cache(maxsize=1)
def _retrieval():
    """Load the Chroma index and keyword index once, not on every question."""
    return get_vectorstore(), load_keyword_index()


def _format_sources(context: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] {c['title']} - {c['section']}\n{c['text']}" for i, c in enumerate(context, 1)
    )


def router(state: CraftState) -> dict:
    reply = get_llm().invoke([SystemMessage(ROUTER_PROMPT), HumanMessage(state["question"])]).content
    label = reply.strip().lower().strip(".")
    return {"route": "mechanics" if label == "mechanics" else "lore"}


def rag(state: CraftState) -> dict:
    vectorstore, keyword_index = _retrieval()
    docs = search(state["question"], vectorstore, keyword_index, mode="hybrid", top_n=TOP_N)
    return {
        "context": [
            {
                "text": d.page_content,
                "url": d.metadata["url"],
                "title": d.metadata["title"],
                "section": d.metadata["section"],
            }
            for d in docs
        ]
    }


def mechanics(state: CraftState) -> dict:
    reply = get_llm().invoke([SystemMessage(EXTRACT_PROMPT), HumanMessage(state["question"])]).content
    item = reply.strip().strip(".\"'").lower()
    recipe_text = lookup_recipe.invoke({"item_name": item})
    return {
        "context": [
            {
                "text": recipe_text,
                "url": RECIPE_SOURCE,
                "title": "minecraft-data (Minecraft 26.1)",
                "section": "recipes.json",
            }
        ],
        "recipe": recipe_layout(item),
    }


def answer(state: CraftState) -> dict:
    messages = [
        SystemMessage(ANSWER_PROMPT.format(sources=_format_sources(state["context"]))),
        HumanMessage(state["question"]),
    ]
    if state.get("verdict"):
        messages.append(
            HumanMessage(
                "Your previous answer had unsupported claims:\n"
                f"{state['verdict']}\n"
                "Rewrite the answer using only the sources."
            )
        )
    text = get_llm().invoke(messages).content.strip()
    return {"answer": text, "attempts": state.get("attempts", 0) + 1}


def verify(state: CraftState) -> dict:
    prompt = VERIFY_PROMPT.format(
        sources=_format_sources(state["context"]), answer=state["answer"]
    )
    verdict = get_llm().invoke([HumanMessage(prompt)]).content.strip()

    if verdict.upper().startswith("SUPPORTED"):
        return {"verified": True, "verdict": ""}

    if state.get("attempts", 0) >= MAX_ATTEMPTS:
        notice = "I could not fully verify this answer against the sources.\n\n"
        return {"verified": False, "verdict": verdict, "answer": notice + state["answer"]}

    return {"verified": False, "verdict": verdict}


def after_verify(state: CraftState) -> str:
    if state.get("verified") or state.get("attempts", 0) >= MAX_ATTEMPTS:
        return "end"
    return "answer"
