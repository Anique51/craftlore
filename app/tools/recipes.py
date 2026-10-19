import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

ITEMS_FILE = Path("data/items.json")
RECIPES_FILE = Path("data/recipes.json")
MAX_RECIPES = 3


def normalize(name: str) -> str:
    """'minecraft:ender_pearl' -> 'ender pearl', 'Crafting Table' -> 'crafting table'."""
    n = name.strip().lower()
    if n.startswith("minecraft:"):
        n = n[len("minecraft:"):]
    return " ".join(n.replace("_", " ").split())


@lru_cache(maxsize=1)
def _load():
    items = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    recipes = json.loads(RECIPES_FILE.read_text(encoding="utf-8"))
    name_to_id: dict[str, int] = {}
    id_to_name: dict[int, str] = {}
    for item in items:
        id_to_name[item["id"]] = item.get("displayName") or item["name"]
        for key in (item["name"], item.get("displayName", "")):
            if key:
                name_to_id.setdefault(normalize(key), item["id"])
    return name_to_id, id_to_name, recipes


def _item_name(id_to_name: dict, item_id) -> str:
    if item_id is None:
        return "empty"
    return id_to_name.get(item_id, f"unknown item {item_id}")


def _describe(recipe: dict, id_to_name: dict) -> str:
    result = recipe["result"]
    if isinstance(result, dict):
        out_id, count = result["id"], result.get("count", 1)
    else:
        out_id, count = result, 1

    if "inShape" in recipe:
        grid = recipe["inShape"]
        width, height = len(grid[0]), len(grid)
        rows = [
            f"  Row {r + 1}: " + ", ".join(_item_name(id_to_name, i) for i in row)
            for r, row in enumerate(grid)
        ]
        header = f"{_item_name(id_to_name, out_id)} x{count} (shaped, {width}x{height} grid):"
        return "\n".join([header, *rows])

    ingredients = [i for i in recipe.get("ingredients", []) if i is not None]
    counts = Counter(_item_name(id_to_name, i) for i in ingredients)
    parts = [f"{name} x{c}" if c > 1 else name for name, c in counts.items()]
    header = f"{_item_name(id_to_name, out_id)} x{count} (shapeless):"
    return f"{header}\n  Ingredients: " + ", ".join(parts)


@tool
def lookup_recipe(item_name: str) -> str:
    """Look up the crafting recipe for a Minecraft Java item by name, e.g. 'beacon' or 'crafting table'."""
    name_to_id, id_to_name, recipes = _load()
    item_id = name_to_id.get(normalize(item_name))
    if item_id is None:
        return f"No recipe found: '{item_name}' is not a known item name."

    recipe_list = recipes.get(str(item_id), [])
    if not recipe_list:
        display = id_to_name.get(item_id, item_name)
        return f"{display} has no crafting recipe. It is obtained another way, such as mining, trading, or loot."

    return "\n\n".join(_describe(r, id_to_name) for r in recipe_list[:MAX_RECIPES])


def _pad_grid(rows: list[list]) -> list[list]:
    """Pad a shaped recipe to a 3x3 display grid, filling empty cells with None."""
    rows = [list(r) + [None] * (3 - len(r)) for r in rows][:3]
    while len(rows) < 3:
        rows.append([None, None, None])
    return rows


def recipe_layout(item_name: str) -> dict | None:
    """Structured recipe for drawing a crafting grid. Returns None if no recipe exists."""
    name_to_id, id_to_name, recipes = _load()
    item_id = name_to_id.get(normalize(item_name))
    if item_id is None:
        return None
    recipe_list = recipes.get(str(item_id), [])
    if not recipe_list:
        return None
    rec = recipe_list[0]
    result = rec["result"]
    out_id, count = (result["id"], result.get("count", 1)) if isinstance(result, dict) else (result, 1)
    result_name = id_to_name.get(out_id, f"unknown item {out_id}")

    if "inShape" in rec:
        grid = [[None if i is None else _item_name(id_to_name, i) for i in row] for row in rec["inShape"]]
        return {"result": result_name, "count": count, "type": "shaped",
                "grid": _pad_grid(grid), "ingredients": None}

    ingredients = [_item_name(id_to_name, i) for i in rec.get("ingredients", []) if i is not None]
    return {"result": result_name, "count": count, "type": "shapeless",
            "grid": None, "ingredients": ingredients}


def _pad_grid(rows: list[list]) -> list[list]:
    """Pad a shaped recipe to a 3x3 display grid, filling empty cells with None."""
    rows = [list(r) + [None] * (3 - len(r)) for r in rows][:3]
    while len(rows) < 3:
        rows.append([None, None, None])
    return rows


def recipe_layout(item_name: str) -> dict | None:
    """Structured recipe for drawing a crafting grid. Returns None if no recipe exists."""
    name_to_id, id_to_name, recipes = _load()
    item_id = name_to_id.get(normalize(item_name))
    if item_id is None:
        return None
    recipe_list = recipes.get(str(item_id), [])
    if not recipe_list:
        return None
    rec = recipe_list[0]
    result = rec["result"]
    out_id, count = (result["id"], result.get("count", 1)) if isinstance(result, dict) else (result, 1)
    result_name = id_to_name.get(out_id, f"unknown item {out_id}")

    if "inShape" in rec:
        grid = [[None if i is None else _item_name(id_to_name, i) for i in row] for row in rec["inShape"]]
        return {"result": result_name, "count": count, "type": "shaped",
                "grid": _pad_grid(grid), "ingredients": None}

    ingredients = [_item_name(id_to_name, i) for i in rec.get("ingredients", []) if i is not None]
    return {"result": result_name, "count": count, "type": "shapeless",
            "grid": None, "ingredients": ingredients}
