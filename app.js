const STORAGE_KEY = "acnh_owned_recipe_ids";

let allRecipes = [];
let currentCategory = "all";
let searchText = "";
let ownedIds = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));

const recipeGrid = document.getElementById("recipeGrid");
const stats = document.getElementById("stats");
const searchInput = document.getElementById("searchInput");
const categoryFilters = document.getElementById("categoryFilters");
const cardTemplate = document.getElementById("recipeCardTemplate");

function saveOwned() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ownedIds]));
}

function getFilteredRecipes() {
  return allRecipes.filter((recipe) => {
    const categoryMatch =
      currentCategory === "all" || recipe.category_en === currentCategory;
    const keyword = searchText.trim().toLowerCase();
    const textMatch =
      !keyword ||
      recipe.name_ko.toLowerCase().includes(keyword) ||
      recipe.name_en.toLowerCase().includes(keyword);
    return categoryMatch && textMatch;
  });
}

function renderStats(visibleRecipes) {
  const ownedCount = visibleRecipes.filter((recipe) =>
    ownedIds.has(recipe.id),
  ).length;

  stats.textContent = `표시 ${visibleRecipes.length}개 | 보유 ${ownedCount}개`;
}

function renderRecipes() {
  const visible = getFilteredRecipes();
  recipeGrid.innerHTML = "";
  renderStats(visible);

  for (const recipe of visible) {
    const node = cardTemplate.content.cloneNode(true);
    const card = node.querySelector(".card");
    const img = node.querySelector(".thumb");
    const nameKo = node.querySelector(".name-ko");
    const nameEn = node.querySelector(".name-en");
    const category = node.querySelector(".category");
    const materials = node.querySelector(".materials");
    const source = node.querySelector(".source");
    const checkbox = node.querySelector(".owned-checkbox");

    img.src = recipe.image_url || "";
    img.alt = `${recipe.name_ko} 이미지`;
    nameKo.textContent = recipe.name_ko || recipe.name_en;
    nameEn.textContent = recipe.name_en;
    category.textContent = recipe.category_ko;
    materials.textContent = recipe.materials_ko || recipe.materials_en || "-";
    source.textContent = recipe.source_ko || recipe.source_en || "-";
    checkbox.checked = ownedIds.has(recipe.id);

    checkbox.addEventListener("change", () => {
      if (checkbox.checked) ownedIds.add(recipe.id);
      else ownedIds.delete(recipe.id);
      saveOwned();
      renderStats(getFilteredRecipes());
    });

    card.addEventListener("dblclick", () => {
      if (recipe.source_url) {
        window.open(recipe.source_url, "_blank", "noopener,noreferrer");
      }
    });

    recipeGrid.append(node);
  }
}

async function loadRecipes() {
  if (window.location.protocol === "file:") {
    throw new Error(
      "index.html을 파일로 직접 열면 데이터 로딩이 차단됩니다. 터미널에서 `python3 -m http.server 5500` 실행 후 http://localhost:5500 으로 접속하세요.",
    );
  }
  const res = await fetch("./recipes.json");
  if (!res.ok) throw new Error("recipes.json 파일을 읽지 못했습니다.");
  allRecipes = await res.json();
}

function bindEvents() {
  searchInput.addEventListener("input", (e) => {
    searchText = e.target.value;
    renderRecipes();
  });

  categoryFilters.addEventListener("click", (e) => {
    const button = e.target.closest(".filter");
    if (!button) return;
    currentCategory = button.dataset.category;

    for (const item of categoryFilters.querySelectorAll(".filter")) {
      item.classList.toggle("active", item === button);
    }
    renderRecipes();
  });
}

async function init() {
  try {
    await loadRecipes();
    bindEvents();
    renderRecipes();
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    stats.textContent = "데이터 로딩 실패";
    recipeGrid.innerHTML = `<p>오류: ${message}</p>`;
  }
}

init();
