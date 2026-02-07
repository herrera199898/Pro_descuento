import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA_FILE = Path("data/products.json")
WEB_DIR = Path("web")


def load_data() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return payload.get("products", [])


def filter_products(products: list[dict], params: dict) -> list[dict]:
    q = (params.get("q", [""])[0] or "").strip().lower()
    min_price = params.get("min_price", [""])[0]
    max_price = params.get("max_price", [""])[0]
    min_discount = params.get("min_discount", [""])[0]

    def as_float(value: str):
        try:
            return float(value)
        except ValueError:
            return None

    min_price_v = as_float(min_price) if min_price else None
    max_price_v = as_float(max_price) if max_price else None
    min_discount_v = as_float(min_discount) if min_discount else None

    filtered = []
    for p in products:
        title = (p.get("title") or "").lower()
        price = p.get("price")
        discount = p.get("discount_pct") or 0

        if q and q not in title:
            continue
        if min_price_v is not None and (price is None or price < min_price_v):
            continue
        if max_price_v is not None and (price is None or price > max_price_v):
            continue
        if min_discount_v is not None and discount < min_discount_v:
            continue

        filtered.append(p)

    return filtered


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/products":
            params = parse_qs(parsed.query)
            products = load_data()
            result = filter_products(products, params)
            body = json.dumps({"count": len(result), "products": result}, ensure_ascii=False).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            return self._serve_file("index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self._serve_file("app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/styles.css":
            return self._serve_file("styles.css", "text/css; charset=utf-8")

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        return

    def _serve_file(self, filename: str, content_type: str):
        path = WEB_DIR / filename
        if not path.exists():
            self.send_error(404, "File not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Server running on http://localhost:8000")
    server.serve_forever()
