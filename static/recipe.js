(function () {
  const box = document.getElementById("recipe");

  function slot(name, extraClass) {
    const el = document.createElement("div");
    el.className = "slot " + (name ? "filled " : "empty ") + (extraClass || "");
    if (name) {
      el.title = name;
      const label = document.createElement("span");
      label.textContent = name;
      el.appendChild(label);
    }
    return el;
  }

  window.renderRecipe = function (recipe) {
    box.innerHTML = "";
    if (!recipe) {
      box.classList.add("hidden");
      return;
    }

    const title = document.createElement("p");
    title.className = "craft-title";
    title.textContent = recipe.type === "shaped"
      ? "Crafting grid (shaped)"
      : "Ingredients (shapeless)";

    const wrap = document.createElement("div");
    wrap.className = "craft";

    if (recipe.type === "shaped") {
      const grid = document.createElement("div");
      grid.className = "grid";
      recipe.grid.flat().forEach((name) => grid.appendChild(slot(name)));
      wrap.appendChild(grid);
    } else {
      const list = document.createElement("div");
      list.className = "ingredients";
      recipe.ingredients.forEach((name) => list.appendChild(slot(name)));
      wrap.appendChild(list);
    }

    const arrow = document.createElement("div");
    arrow.className = "arrow";
    arrow.textContent = "→";
    wrap.appendChild(arrow);

    const result = slot(recipe.result, "result");
    if (recipe.count > 1) {
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = recipe.count;
      result.appendChild(count);
    }
    wrap.appendChild(result);

    box.append(title, wrap);
    box.classList.remove("hidden");
  };
})();
