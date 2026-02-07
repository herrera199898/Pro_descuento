import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://api.mercadolibre.com/sites/MLA/search?q={query}&limit={limit}"
OUT_FILE = Path("data/products.json")
SAMPLE_FILE = Path("data/sample_products.json")


def fetch_products(query: str, limit: int) -> list[dict]:
    url = BASE_URL.format(query=quote_plus(query), limit=limit)
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error from Mercado Libre API: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while connecting to Mercado Libre API: {exc.reason}") from exc

    products = []
    for item in payload.get("results", []):
        original_price = item.get("original_price")
        price = item.get("price")
        discount_pct = 0.0

        if original_price and price and original_price > 0:
            discount_pct = round((1 - (price / original_price)) * 100, 2)

        products.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": discount_pct,
                "currency_id": item.get("currency_id"),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
                "condition": item.get("condition"),
                "seller": (item.get("seller") or {}).get("nickname"),
            }
        )

    return products


def save_products(query: str, products: list[dict]) -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "query": query,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(products),
        "products": products,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch products from Mercado Libre")
    parser.add_argument("--query", required=True, help="Search term")
    parser.add_argument("--limit", type=int, default=50, help="Max products to fetch")
    parser.add_argument(
        "--use-sample-on-error",
        action="store_true",
        help="Use local sample dataset if the API is not reachable or returns forbidden",
    )
    args = parser.parse_args()

    try:
        products = fetch_products(args.query, args.limit)
    except RuntimeError as exc:
        if not args.use_sample_on_error:
            raise
        if not SAMPLE_FILE.exists():
            raise RuntimeError(f"{exc}. Sample file not found at {SAMPLE_FILE}") from exc
        sample_payload = json.loads(SAMPLE_FILE.read_text(encoding="utf-8-sig"))
        products = sample_payload.get("products", [])
        print(f"{exc}. Using sample dataset from {SAMPLE_FILE}.")

    save_products(args.query, products)
    print(f"Saved {len(products)} products to {OUT_FILE}")


if __name__ == "__main__":
    main()
