from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import requests
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "recipes.json"
CACHE_FILE = ROOT_DIR / "translations.ko.cache.json"

SOURCES = [
    {
        "category_en": "Savory",
        "category_ko": "푸드",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Savory",
    },
    {
        "category_en": "Sweet",
        "category_ko": "디저트",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Sweet",
    },
    {
        "category_en": "Other",
        "category_ko": "기타",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Other",
    },
    {
        "category_en": "Tools",
        "category_ko": "도구",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Tools",
    },
    {
        "category_en": "Housewares",
        "category_ko": "하우스웨어",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Housewares",
    },
    {
        "category_en": "Miscellaneous",
        "category_ko": "잡화",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Miscellaneous",
    },
    {
        "category_en": "Wall-mounted",
        "category_ko": "벽걸이",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Wall-mounted",
    },
    {
        "category_en": "Ceiling decor",
        "category_ko": "천장 장식",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Ceiling_decor",
    },
    {
        "category_en": "Interior",
        "category_ko": "인테리어",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Interior",
    },
    {
        "category_en": "Clothing",
        "category_ko": "의류",
        "url": "https://nookipedia.com/wiki/DIY_recipes/Clothing",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
TRANSLATE_DELAY_SEC = 0.1
DETAIL_FETCH_DELAY_SEC = 0.05


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def to_absolute_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    elif url.startswith("/"):
        url = f"https://nookipedia.com{url}"

    split = urlsplit(url)
    fragment = split.fragment or ""
    media_marker = "/media/File:"

    # Nookipedia media modal anchor URL은 이미지 파일 직접 URL이 아니므로 변환한다.
    if media_marker in fragment:
        filename = fragment.split(media_marker, 1)[1].strip()
        if filename:
            filename = unquote(filename)
            return f"https://nookipedia.com/wiki/Special:FilePath/{quote(filename, safe='()_-.,')}"

    return normalize_image_url(url)


def normalize_image_url(url: str) -> str:
    if not url:
        return ""

    # MediaWiki thumb URL -> original image URL
    # e.g. /images/thumb/9/98/File.png/64px-File.png -> /images/9/98/File.png
    url = re.sub(
        r"(https?://dodo\.ac/np/images)/thumb/([0-9a-f])/([0-9a-f]{2})/([^/]+)/[^/]+$",
        r"\1/\2/\3/\4",
        url,
        flags=re.IGNORECASE,
    )
    return url


def slugify(value: str) -> str:
    value = value.lower().replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, str]) -> None:
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def translate_to_ko(text: str, cache: dict[str, str]) -> str:
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    if cleaned in cache:
        return cache[cleaned]

    endpoint = (
        "https://translate.googleapis.com/translate_a/single"
        f"?client=gtx&sl=en&tl=ko&dt=t&q={quote(cleaned)}"
    )

    try:
        response = requests.get(endpoint, headers=HEADERS, timeout=20)
        response.raise_for_status()
        payload = response.json()
        translated = normalize_text("".join(part[0] for part in payload[0] if part and part[0]))
        result = translated or cleaned
    except Exception:
        result = cleaned

    cache[cleaned] = result
    time.sleep(TRANSLATE_DELAY_SEC)
    return result


def get_header_row(table):
    for row in table.select("tr"):
        if row.select("th"):
            return row
    return None


def _score_recipe_table(table) -> int:
    header_row = get_header_row(table)
    if not header_row:
        return 0

    headers = [normalize_text(th.get_text()).lower() for th in header_row.select("th")]
    if not headers:
        return 0

    joined = " ".join(headers)
    score = 0
    if any(token in joined for token in ["recipe", "name", "item"]):
        score += 4
    if any(token in joined for token in ["materials", "ingredients"]):
        score += 3
    if "source" in joined:
        score += 2
    if any(token in joined for token in ["buy", "sell", "price"]):
        score += 1

    data_rows = [r for r in table.select("tr") if r.select("td")]
    if len(data_rows) >= 5:
        score += 2
    elif data_rows:
        score += 1

    return score


def get_recipe_table(soup: BeautifulSoup):
    best_table = None
    best_score = 0

    for table in soup.select("table"):
        score = _score_recipe_table(table)
        if score > best_score:
            best_table = table
            best_score = score

    return best_table if best_score >= 4 else None


def read_header_indexes(table) -> dict[str, int]:
    header_row = get_header_row(table)
    headers = [normalize_text(th.get_text()) for th in header_row.select("th")] if header_row else []

    def find_index(patterns: list[str]) -> int:
        for i, header in enumerate(headers):
            lower = header.lower()
            if any(p in lower for p in patterns):
                return i
        return -1

    return {
        "name": find_index(["recipe", "name", "item"]),
        "materials": find_index(["materials", "ingredients"]),
        "source": find_index(
            [
                "source",
                "obtain",
                "obtained",
                "how to obtain",
                "recipe source",
                "available from",
                "available",
            ]
        ),
        "buy": find_index(["buy"]),
        "sell": find_index(["sell"]),
    }


def get_cell_text(cells, idx: int) -> str:
    if idx < 0 or idx >= len(cells):
        return ""
    cell = cells[idx]
    text = normalize_text(cell.get_text(" ", strip=True))
    if text:
        return text

    for attr in ["data-sort-value", "title", "aria-label"]:
        value = normalize_text(cell.get(attr, ""))
        if value:
            return value
    return ""


def _unique_keep_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def get_source_cell_text(cells, idx: int) -> str:
    if idx < 0 or idx >= len(cells):
        return ""
    cell = cells[idx]

    li_values = [
        normalize_text(li.get_text(" ", strip=True))
        for li in cell.select("li")
    ]
    li_values = _unique_keep_order([v for v in li_values if v and not re.fullmatch(r"\[\d+\]", v)])
    if li_values:
        return " / ".join(li_values)

    lines = [
        normalize_text(line)
        for line in cell.get_text("\n", strip=True).splitlines()
    ]
    lines = _unique_keep_order([v for v in lines if v and not re.fullmatch(r"\[\d+\]", v)])
    if lines:
        return " / ".join(lines)

    return get_cell_text(cells, idx)


def _pick_first_srcset_url(value: str) -> str:
    # srcset: "url1 1x, url2 2x" -> url1
    first = (value or "").split(",")[0].strip()
    return first.split(" ")[0].strip() if first else ""


def get_image_url_from_row(row, name_cell) -> str:
    candidates = []
    if name_cell is not None:
        candidates.append(name_cell)
    candidates.append(row)

    for container in candidates:
        img = container.select_one("img")
        if not img:
            continue

        for attr in ["data-src", "data-image-src", "data-lazy-src", "src"]:
            value = img.get(attr, "")
            if value:
                return to_absolute_url(value)

        for attr in ["data-srcset", "srcset"]:
            value = _pick_first_srcset_url(img.get(attr, ""))
            if value:
                return to_absolute_url(value)

    return ""


def get_detail_soup(url: str, page_cache: dict[str, BeautifulSoup]) -> BeautifulSoup | None:
    if not url:
        return None

    cached = page_cache.get(url)
    if cached is not None:
        return cached

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_cache[url] = soup
        time.sleep(DETAIL_FETCH_DELAY_SEC)
        return soup
    except Exception:
        return None


def get_image_url_from_detail_page(url: str, page_cache: dict[str, BeautifulSoup]) -> str:
    soup = get_detail_soup(url, page_cache)
    if soup is None:
        return ""

    meta_og = soup.select_one('meta[property="og:image"]')
    if meta_og and meta_og.get("content"):
        return to_absolute_url(meta_og.get("content", ""))

    meta_twitter = soup.select_one('meta[name="twitter:image"]')
    if meta_twitter and meta_twitter.get("content"):
        return to_absolute_url(meta_twitter.get("content", ""))

    for selector in [
        ".infobox img",
        "table.infobox img",
        ".portable-infobox img",
        ".pi-image-thumbnail",
        "#mw-content-text img",
    ]:
        img = soup.select_one(selector)
        if not img:
            continue
        for attr in ["data-src", "data-image-src", "data-lazy-src", "src"]:
            value = img.get(attr, "")
            if value:
                return to_absolute_url(value)
        for attr in ["data-srcset", "srcset"]:
            value = _pick_first_srcset_url(img.get(attr, ""))
            if value:
                return to_absolute_url(value)

    return ""


def get_source_from_detail_page(url: str, page_cache: dict[str, BeautifulSoup]) -> str:
    soup = get_detail_soup(url, page_cache)
    if soup is None:
        return ""

    patterns = [
        "source",
        "obtain",
        "obtained",
        "how to obtain",
        "obtain method",
        "recipe source",
        "available from",
        "available",
    ]

    for row in soup.select("table.infobox tr"):
        th = row.select_one("th")
        td = row.select_one("td")
        if not th or not td:
            continue
        key = normalize_text(th.get_text(" ", strip=True)).lower()
        if not any(pattern in key for pattern in patterns):
            continue
        value = normalize_text(td.get_text(" ", strip=True))
        if value and value != "-":
            return value

    for item in soup.select(".portable-infobox .pi-item"):
        label = item.select_one(".pi-data-label")
        value_node = item.select_one(".pi-data-value")
        if not label or not value_node:
            continue
        key = normalize_text(label.get_text(" ", strip=True)).lower()
        if not any(pattern in key for pattern in patterns):
            continue
        value = normalize_text(value_node.get_text(" ", strip=True))
        if value and value != "-":
            return value

    return ""


def parse_category(source: dict[str, str], cache: dict[str, str]) -> list[dict]:
    response = requests.get(source["url"], headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table = get_recipe_table(soup)
    if table is None:
        raise RuntimeError(f"레시피 표를 찾지 못했습니다: {source['url']}")

    indexes = read_header_indexes(table)
    recipes = []
    detail_page_cache: dict[str, BeautifulSoup] = {}

    rows = table.select("tr")
    header_row = get_header_row(table)
    if header_row in rows:
        rows = rows[rows.index(header_row) + 1 :]

    for row in rows:
        cells = row.select("td")
        if not cells:
            continue

        name_idx = indexes["name"] if indexes["name"] >= 0 else 0
        name_cell = cells[name_idx] if name_idx < len(cells) else None
        if name_cell is None:
            continue

        links = name_cell.select("a")
        name_link = links[-1] if links else None
        name_en = normalize_text(name_link.get_text() if name_link else name_cell.get_text())
        if not name_en:
            continue

        href = to_absolute_url(name_link.get("href", "") if name_link else "")
        image_url = get_image_url_from_row(row, name_cell)
        if not image_url and href:
            image_url = get_image_url_from_detail_page(href, detail_page_cache)

        materials_en = get_cell_text(cells, indexes["materials"])
        source_en = get_source_cell_text(cells, indexes["source"])
        if not source_en and href:
            source_en = get_source_from_detail_page(href, detail_page_cache)
        buy_price = get_cell_text(cells, indexes["buy"])
        sell_price = get_cell_text(cells, indexes["sell"])

        name_ko = translate_to_ko(name_en, cache)
        materials_ko = translate_to_ko(materials_en, cache) if materials_en else ""
        source_ko = translate_to_ko(source_en, cache) if source_en else ""

        recipes.append(
            {
                "id": slugify(name_en),
                "name_en": name_en,
                "name_ko": name_ko,
                "category_en": source["category_en"],
                "category_ko": source["category_ko"],
                "image_url": image_url,
                "source_url": href or source["url"],
                "materials_en": materials_en,
                "materials_ko": materials_ko,
                "source_en": source_en,
                "source_ko": source_ko,
                "buy_price": buy_price,
                "sell_price": sell_price,
                "owned": False,
            }
        )

    return recipes


def main() -> None:
    cache = load_cache()
    all_recipes = []

    for source in SOURCES:
        print(f"[수집] {source['category_ko']} ({source['url']})")
        recipes = parse_category(source, cache)
        print(f"  -> {len(recipes)}개")
        all_recipes.extend(recipes)

    save_cache(cache)
    OUTPUT_FILE.write_text(
        json.dumps(all_recipes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"완료: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
