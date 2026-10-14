from pathlib import Path

import pytest

from app.tools.recipes import lookup_recipe, normalize

DATA_READY = Path("data/recipes.json").exists() and Path("data/items.json").exists()
needs_data = pytest.mark.skipif(
    not DATA_READY, reason="recipe data not downloaded (data/ is gitignored)"
)


def test_normalize_strips_prefix_and_underscores():
    assert normalize("minecraft:ender_pearl") == "ender pearl"
    assert normalize("  Crafting Table ") == "crafting table"


@needs_data
def test_beacon_recipe_contains_nether_star_and_obsidian():
    out = lookup_recipe.invoke({"item_name": "beacon"})
    assert "Nether Star" in out
    assert "Obsidian" in out


@needs_data
def test_crafting_table_recipe_uses_planks():
    out = lookup_recipe.invoke({"item_name": "crafting table"})
    assert "Planks" in out


@needs_data
def test_torch_recipe_uses_stick():
    out = lookup_recipe.invoke({"item_name": "torch"})
    assert "Stick" in out


@needs_data
def test_accepts_minecraft_prefix_and_underscores():
    out = lookup_recipe.invoke({"item_name": "minecraft:crafting_table"})
    assert "Planks" in out


@needs_data
def test_unknown_item_is_not_guessed():
    out = lookup_recipe.invoke({"item_name": "flying sword of doom"})
    assert out.startswith("No recipe found")


@needs_data
def test_item_without_recipe_says_so():
    out = lookup_recipe.invoke({"item_name": "bedrock"})
    assert "no crafting recipe" in out
