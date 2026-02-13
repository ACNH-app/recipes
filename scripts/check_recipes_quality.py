from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RECIPES_FILE = ROOT_DIR / "recipes.json"

REQUIRED_KEYS = [
    "id",
    "name_en",
    "name_ko",
    "category_en",
    "category_ko",
    "source_url",
    "owned",
]

STRING_KEYS = [
    "id",
    "name_en",
    "name_ko",
    "category_en",
    "category_ko",
    "image_url",
    "source_url",
    "materials_en",
    "materials_ko",
    "source_en",
    "source_ko",
    "buy_price",
    "sell_price",
]


def is_valid_http_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_recipes(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("recipes.json 루트 타입이 list가 아닙니다.")
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"{i}번 항목이 object(dict)가 아닙니다.")
    return payload


def print_top(title: str, values: list[str], limit: int = 10) -> None:
    print(f"\n[{title}]")
    if not values:
        print("  - 없음")
        return
    for v in values[:limit]:
        print(f"  - {v}")
    if len(values) > limit:
        print(f"  ... 외 {len(values) - limit}개")


def main() -> None:
    parser = argparse.ArgumentParser(description="recipes.json 품질 검사")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_RECIPES_FILE,
        help=f"검사할 JSON 파일 경로 (기본값: {DEFAULT_RECIPES_FILE})",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="오류가 하나라도 있으면 종료 코드를 1로 반환",
    )
    args = parser.parse_args()

    file_path = args.file.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {file_path}")

    recipes = load_recipes(file_path)
    total = len(recipes)
    print(f"[요약] 파일: {file_path}")
    print(f"[요약] 전체 레코드 수: {total}")

    id_counter = Counter()
    name_counter = Counter()
    category_counter = Counter()
    missing_keys = defaultdict(list)
    empty_string_counts = Counter()
    invalid_urls = {"source_url": [], "image_url": []}
    invalid_types = []

    for idx, item in enumerate(recipes):
        rid = str(item.get("id", "")).strip()
        if rid:
            id_counter[rid] += 1

        name = str(item.get("name_en", "")).strip()
        if name:
            name_counter[name] += 1

        category = str(item.get("category_en", "")).strip() or "(empty)"
        category_counter[category] += 1

        for key in REQUIRED_KEYS:
            if key not in item:
                missing_keys[key].append(f"index={idx}")

        for key in STRING_KEYS:
            value = item.get(key, "")
            if not isinstance(value, str):
                invalid_types.append(f"index={idx} key={key} type={type(value).__name__}")
                continue
            if value.strip() == "":
                empty_string_counts[key] += 1

        owned_value = item.get("owned")
        if not isinstance(owned_value, bool):
            invalid_types.append(f"index={idx} key=owned type={type(owned_value).__name__}")

        source_url = item.get("source_url", "")
        if isinstance(source_url, str) and source_url.strip() and not is_valid_http_url(source_url):
            invalid_urls["source_url"].append(f"index={idx} value={source_url}")

        image_url = item.get("image_url", "")
        if isinstance(image_url, str) and image_url.strip() and not is_valid_http_url(image_url):
            invalid_urls["image_url"].append(f"index={idx} value={image_url}")

    duplicate_ids = sorted([k for k, v in id_counter.items() if v > 1])
    duplicate_names = sorted([k for k, v in name_counter.items() if v > 1])
    has_error = False

    print("\n[카테고리 분포]")
    for category, count in sorted(category_counter.items()):
        pct = (count / total * 100) if total else 0
        print(f"  - {category}: {count}개 ({pct:.1f}%)")

    print("\n[빈 문자열 비율]")
    for key in STRING_KEYS:
        empty_count = empty_string_counts[key]
        pct = (empty_count / total * 100) if total else 0
        print(f"  - {key}: {empty_count}/{total} ({pct:.1f}%)")

    if duplicate_ids:
        has_error = True
        print_top("중복 ID", duplicate_ids)
    else:
        print("\n[중복 ID]\n  - 없음")

    if missing_keys:
        has_error = True
        print("\n[필수 키 누락]")
        for key in REQUIRED_KEYS:
            rows = missing_keys.get(key, [])
            if rows:
                print(f"  - {key}: {len(rows)}건 (예: {rows[0]})")
    else:
        print("\n[필수 키 누락]\n  - 없음")

    print_top("중복 영문 이름(name_en)", duplicate_names)
    print_top("잘못된 source_url", invalid_urls["source_url"])
    print_top("잘못된 image_url", invalid_urls["image_url"])

    if invalid_urls["source_url"] or invalid_types:
        has_error = True

    if invalid_types:
        print_top("타입 오류", invalid_types)
    else:
        print("\n[타입 오류]\n  - 없음")

    status = "FAIL" if has_error else "PASS"
    print(f"\n[결과] {status}")

    if args.strict and has_error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
