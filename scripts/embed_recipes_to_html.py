from __future__ import annotations

import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
HTML_FILE = ROOT_DIR / "index.html"
RECIPES_FILE = ROOT_DIR / "recipes.json"

BLOCK_PATTERN = re.compile(
    r'(<script id="embeddedRecipes" type="application/json">\n)(.*?)(\n\s*</script>)',
    re.S,
)


def main() -> None:
    html = HTML_FILE.read_text(encoding="utf-8")
    recipes = json.loads(RECIPES_FILE.read_text(encoding="utf-8"))
    payload = json.dumps(recipes, ensure_ascii=False, indent=2)

    updated, count = BLOCK_PATTERN.subn(
        lambda m: f"{m.group(1)}{payload}{m.group(3)}",
        html,
        count=1,
    )
    if count != 1:
        raise RuntimeError("embeddedRecipes 스크립트 블록을 찾지 못했습니다.")

    HTML_FILE.write_text(updated, encoding="utf-8")
    print(f"완료: {HTML_FILE} (레시피 {len(recipes)}개 내장)")


if __name__ == "__main__":
    main()
