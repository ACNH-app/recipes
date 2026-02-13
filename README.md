# 모동숲 레시피 체크 앱

Nookipedia의 푸드/디저트 DIY 레시피를 수집해 `recipes.json`으로 저장하고,
브라우저에서 보유 여부를 체크하는 간단한 웹앱입니다.

## 1) 설치

```bash
python3 -m pip install -r requirements.txt
```

## 2) 레시피 JSON 생성

```bash
python3 scripts/fetch_recipes.py
```

생성 결과:

- `recipes.json` (앱에서 사용하는 데이터)
- `translations.ko.cache.json` (영문->한글 번역 캐시)

`file://`로도 열고 싶다면(서버 없이 실행):

```bash
python3 scripts/embed_recipes_to_html.py
```

## 2-1) 데이터 품질 점검

```bash
python3 scripts/check_recipes_quality.py
```

엄격 모드(오류 시 종료 코드 1):

```bash
python3 scripts/check_recipes_quality.py --strict
```

## 3) 앱 실행

```bash
python3 -m http.server 5500
```

브라우저에서 아래 주소를 열어 확인합니다.

- `http://localhost:5500`

## 데이터 형식

`recipes.json`의 각 항목은 아래 필드를 포함합니다.

- `id`
- `name_en`
- `name_ko`
- `category_en`
- `category_ko`
- `image_url`
- `source_url`
- `materials_en`
- `materials_ko`
- `source_en`
- `source_ko`
- `buy_price`
- `sell_price`
- `owned`

## 참고

- 체크 상태는 브라우저 `localStorage`에 저장됩니다.
- 번역 API 응답 실패 시 `name_ko` 등은 영문 원문이 저장될 수 있습니다.
