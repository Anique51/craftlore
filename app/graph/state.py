from typing import Literal, TypedDict


class CraftState(TypedDict, total=False):
    question: str
    route: Literal["lore", "mechanics"]
    context: list[dict]   # each: {"text", "url", "title", "section"}
    answer: str
    verified: bool
    verdict: str          # unsupported claims from the last failed check
    attempts: int
