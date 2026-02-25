from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus, unquote, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener
from urllib.error import HTTPError
from zipfile import ZIP_DEFLATED, ZipFile
import http.cookiejar

DOMAIN_BY_COUNTRY = {
    "ar": "mercadolibre.com.ar",
    "cl": "mercadolibre.cl",
    "mx": "mercadolibre.com.mx",
    "co": "mercadolibre.com.co",
    "pe": "mercadolibre.com.pe",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

LOCAL_SHIPPING_FILTER = "SHIPPING*ORIGIN_10215068"
CONDITION_TOKEN_BY_FILTER = {
    "new": "ITEM*CONDITION_2230284",
    "used": "ITEM*CONDITION_2230581",
    "reconditioned": "ITEM*CONDITION_2234833",
}
DEFAULT_PAGE_SIZE = 48
MAX_EMPTY_PAGES = 5
REQUEST_COOKIE_HEADER: str | None = None


def _progress(prefix: str, current: int, total: int | None = None) -> None:
    if total and total > 0:
        pct = min(100, int((current / total) * 100))
        bar_w = 24
        filled = int((pct / 100) * bar_w)
        bar = "#" * filled + "-" * (bar_w - filled)
        msg = f"\r{prefix} [{bar}] {pct:3d}% ({current}/{total})"
    else:
        msg = f"\r{prefix} {current}"
    print(msg, end="", file=sys.stderr, flush=True)


def _progress_done() -> None:
    print(file=sys.stderr, flush=True)


def clean_html_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def extract_price_from_block(block: str) -> str | None:
    current_match = re.search(
        r'<div class="poly-price__current".*?</div>', block, flags=re.DOTALL
    )
    search_scope = current_match.group(0) if current_match else block

    fraction = re.search(
        r'data-andes-money-amount-fraction="true">([^<]+)</span>', search_scope
    )
    if fraction:
        value = clean_html_text(fraction.group(1))
        return f"$ {value}" if value else None

    aria = re.search(r'aria-label="((?!Antes:)[^\"]+)"', search_scope)
    if aria:
        return clean_html_text(aria.group(1))

    return None


def extract_image_from_block(block: str) -> str | None:
    image_match = re.search(r'<img[^>]+class="[^"]*poly-component__picture[^"]*"[^>]+>', block)
    if not image_match:
        return None

    tag = image_match.group(0)
    src_match = re.search(r'\ssrc="([^"]+)"', tag)
    if not src_match:
        src_match = re.search(r'\sdata-src="([^"]+)"', tag)
    if not src_match:
        return None

    return unescape(src_match.group(1))


def extract_discount_percent_from_block(block: str) -> int | None:
    patterns = [
        r'(\d{1,3})\s*%\s*OFF',
        r'(\d{1,3})\s*%\s*dcto',
        r'(\d{1,3})\s*%\s*de\s*descuento',
        r'andes-money-amount-discount[^>]*>\s*(\d{1,3})\s*%',
        r'poly-price__discount[^>]*>\s*(\d{1,3})\s*%',
    ]
    for pattern in patterns:
        match = re.search(pattern, block, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            value = int(match.group(1))
        except ValueError:
            continue
        if 0 <= value <= 100:
            return value
    return None


def extract_condition_from_block(block: str) -> str | None:
    text = clean_html_text(block).lower()
    if "reacondicion" in text:
        return "reconditioned"
    if "usado" in text:
        return "used"
    if "nuevo con caja abierta" in text:
        return "new"
    if "nuevo" in text:
        return "new"
    return None


def _build_opener() -> tuple[Any, http.cookiejar.CookieJar]:
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    return opener, jar


def _read_html(opener: Any, url: str, timeout: int) -> str:
    headers = {"User-Agent": USER_AGENT}
    if REQUEST_COOKIE_HEADER:
        headers["Cookie"] = REQUEST_COOKIE_HEADER
    req = Request(url, headers=headers)
    with opener.open(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def _parse_cookie_pairs(raw: str) -> str:
    parts = []
    for token in raw.split(";"):
        token = token.strip()
        if not token or "=" not in token:
            continue
        name, value = token.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name:
            parts.append(f"{name}={value}")
    return "; ".join(parts)


def configure_cookie_header(cookie_inline: str | None, cookie_file: str | None) -> None:
    global REQUEST_COOKIE_HEADER
    content = ""
    if cookie_file:
        content = Path(cookie_file).read_text(encoding="utf-8").lstrip("\ufeff").strip()
    elif cookie_inline:
        content = cookie_inline.lstrip("\ufeff").strip()
    REQUEST_COOKIE_HEADER = _parse_cookie_pairs(content) if content else None


def fetch_url_html(url: str, timeout: int = 20) -> str:
    opener, _ = _build_opener()
    return _read_html(opener, url, timeout)


def _solve_bm_challenge(cookie_jar: http.cookiejar.CookieJar, domain: str) -> bool:
    bm_cookie = next((c for c in cookie_jar if c.name == "_bmstate"), None)
    if not bm_cookie:
        return False

    decoded = unquote(bm_cookie.value)
    parts = decoded.split(";")
    if len(parts) < 2:
        return False

    token = parts[0]
    try:
        difficulty = int(parts[1])
    except ValueError:
        return False

    prefix = "0" * difficulty
    nonce = 0

    while nonce < 2_000_000:
        digest = hashlib.sha256(f"{token}{nonce}".encode("utf-8")).hexdigest()
        if digest.startswith(prefix):
            break
        nonce += 1
    else:
        return False

    value = quote(f"{token};{nonce}", safe="")
    challenge_cookie = http.cookiejar.Cookie(
        version=0,
        name="_bmc",
        value=value,
        port=None,
        port_specified=False,
        domain=f".{domain}",
        domain_specified=True,
        domain_initial_dot=True,
        path="/",
        path_specified=True,
        secure=False,
        expires=int(time.time()) + 86_000,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )
    cookie_jar.set_cookie(challenge_cookie)
    return True


def build_search_url(query: str, country: str, exclude_international: bool = True) -> str:
    domain = DOMAIN_BY_COUNTRY[country]
    slug = quote_plus(query.strip()).replace("+", "-")
    url = f"https://listado.{domain}/{slug}"
    if exclude_international:
        return f"{url}_NoIndex_True_{LOCAL_SHIPPING_FILTER}"
    return f"{url}_NoIndex_True"


def build_filter_tokens(
    min_price: int,
    max_price: int,
    min_discount: int,
    sort_price: bool,
    exclude_international: bool,
    condition_filter: str,
) -> list[str]:
    tokens: list[str] = []
    if sort_price:
        tokens.append("OrderId_PRICE")
    if min_price > 0 or max_price > 0:
        low = max(0, min_price)
        high = max_price if max_price > 0 else 999999999
        if high < low:
            low, high = high, low
        tokens.append(f"PriceRange_{low}-{high}")
    if min_discount > 0:
        tokens.append(f"Discount_{max(1, min(min_discount, 100))}-100")
    condition_token = CONDITION_TOKEN_BY_FILTER.get(condition_filter)
    if condition_token:
        tokens.append(condition_token)
    tokens.append("NoIndex_True")
    if exclude_international:
        tokens.append(LOCAL_SHIPPING_FILTER)
    return tokens


def append_filter_tokens(base_url: str, tokens: list[str]) -> str:
    if not tokens:
        return base_url
    return f"{base_url}_{'_'.join(tokens)}"


def build_search_url_with_start(
    query: str,
    country: str,
    start: int,
    exclude_international: bool = True,
    min_price: int = 0,
    max_price: int = 0,
    min_discount: int = 0,
    sort_price: bool = False,
    condition_filter: str = "any",
) -> str:
    domain = DOMAIN_BY_COUNTRY[country]
    slug = quote_plus(query.strip()).replace("+", "-")
    base = f"https://listado.{domain}/{slug}"
    if start > 1:
        base = f"{base}_Desde_{start}"
    return append_filter_tokens(
        base,
        build_filter_tokens(
            min_price, max_price, min_discount, sort_price, exclude_international, condition_filter
        ),
    )


def build_search_url_with_category(
    query: str,
    country: str,
    start: int,
    exclude_international: bool = True,
    min_price: int = 0,
    max_price: int = 0,
    min_discount: int = 0,
    sort_price: bool = False,
    condition_filter: str = "any",
) -> str:
    domain = DOMAIN_BY_COUNTRY[country]
    slug = quote_plus(query.strip()).replace("+", "-")
    base = f"https://listado.{domain}/_CustId_0_{slug}"
    if start > 1:
        base = f"{base}_Desde_{start}"
    return append_filter_tokens(
        base,
        build_filter_tokens(
            min_price, max_price, min_discount, sort_price, exclude_international, condition_filter
        ),
    )


def looks_like_results_page(html: str) -> bool:
    return (
        "poly-component__title" in html
        or "ui-search-layout" in html
        or "poly-card__content" in html
    )


def fetch_search_page_html(
    query: str, country: str, timeout: int = 20, exclude_international: bool = True
) -> str:
    url = build_search_url(query, country, exclude_international=exclude_international)
    domain = DOMAIN_BY_COUNTRY[country]

    opener, jar = _build_opener()
    html = _read_html(opener, url, timeout)

    if "This page requires JavaScript to work" not in html:
        return html

    if not _solve_bm_challenge(jar, domain):
        raise RuntimeError("Bloqueado por anti-bot y no se pudo resolver el desafío.")

    html = _read_html(opener, url, timeout)
    if "This page requires JavaScript to work" in html:
        raise RuntimeError("Bloqueado por anti-bot después de reintentar.")

    return html


def fetch_page_with_challenge(
    opener: Any, jar: http.cookiejar.CookieJar, url: str, country: str, timeout: int = 20
) -> str:
    html = _read_html(opener, url, timeout)
    if "This page requires JavaScript to work" not in html:
        return html

    domain = DOMAIN_BY_COUNTRY[country]
    if not _solve_bm_challenge(jar, domain):
        raise RuntimeError("Bloqueado por anti-bot y no se pudo resolver el desafío.")

    html = _read_html(opener, url, timeout)
    if "This page requires JavaScript to work" in html:
        raise RuntimeError("Bloqueado por anti-bot después de reintentar.")

    return html


def extract_next_page_url(html: str, current_url: str) -> str | None:
    next_match = re.search(r'<a[^>]+rel="next"[^>]+href="([^"]+)"', html)
    if not next_match:
        next_match = re.search(r'<a[^>]+title="Siguiente"[^>]+href="([^"]+)"', html)
    if not next_match:
        return None
    return urljoin(current_url, unescape(next_match.group(1)))


def collect_results(
    query: str,
    country: str,
    limit: int,
    fetch_all: bool,
    max_pages: int,
    exclude_international: bool,
    min_price: int,
    max_price: int,
    min_discount: int,
    sort_price: bool,
    condition_filter: str,
    search_url: str | None,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    opener, jar = _build_opener()
    current_start = 1

    seen_links: set[str] = set()
    collected: list[dict[str, Any]] = []
    page_count = 0
    page_size = DEFAULT_PAGE_SIZE
    empty_streak = 0

    unlimited_pages = max_pages <= 0
    shell_page_streak = 0
    next_url: str | None = search_url.strip() if search_url else None
    while unlimited_pages or page_count < max_pages:
        page_count += 1
        _progress(
            "Recolectando paginas",
            page_count,
            (None if unlimited_pages else (max_pages if fetch_all else None)),
        )
        if next_url:
            current_url = next_url
        else:
            current_url = build_search_url_with_start(
                query,
                country,
                current_start,
                exclude_international=exclude_international,
                min_price=min_price,
                max_price=max_price,
                min_discount=min_discount,
                sort_price=sort_price,
                condition_filter=condition_filter,
            )
        html = ""
        last_http_error: HTTPError | None = None
        for _ in range(3):
            try:
                html = fetch_page_with_challenge(opener, jar, current_url, country, timeout=timeout)
                last_http_error = None
                break
            except HTTPError as exc:
                last_http_error = exc
                if exc.code == 404:
                    break
                time.sleep(0.6)
                opener, jar = _build_opener()
        if last_http_error is not None:
            if last_http_error.code == 404:
                break
            raise last_http_error

        # Some queries return a generic shell page without SSR results.
        # Try an alternate listing URL before giving up on this page.
        if not looks_like_results_page(html):
            fallback_url = build_search_url_with_category(
                query,
                country,
                current_start,
                exclude_international=exclude_international,
                min_price=min_price,
                max_price=max_price,
                min_discount=min_discount,
                sort_price=sort_price,
                condition_filter=condition_filter,
            )
            if not next_url and fallback_url != current_url:
                try:
                    html_alt = fetch_page_with_challenge(opener, jar, fallback_url, country, timeout=timeout)
                    if looks_like_results_page(html_alt):
                        html = html_alt
                except HTTPError:
                    pass

        if not looks_like_results_page(html):
            shell_page_streak += 1
            if shell_page_streak >= 3:
                raise RuntimeError(
                    "Mercado Libre devolvió páginas sin resultados (bloqueo/anti-bot temporal). "
                    "Reintenta en unos minutos."
                )
            if next_url:
                break
            current_start += page_size
            continue
        shell_page_streak = 0

        page_items = parse_results_from_html(html, limit=200)
        if not page_items:
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_PAGES:
                break
            if next_url:
                next_url = extract_next_page_url(html, current_url)
                if not next_url:
                    break
            else:
                current_start += page_size
            continue
        empty_streak = 0

        new_items = 0
        for item in page_items:
            if item["link"] in seen_links:
                continue
            seen_links.add(item["link"])
            item["position"] = len(collected) + 1
            collected.append(item)
            new_items += 1
            if not fetch_all and len(collected) >= limit:
                return collected

        if not fetch_all and len(collected) >= limit:
            return collected

        # If an entire page repeats known links, we're probably at the end.
        if new_items == 0:
            empty_streak += 1
            if empty_streak >= MAX_EMPTY_PAGES:
                break
            if next_url:
                next_url = extract_next_page_url(html, current_url)
                if not next_url:
                    break
            else:
                current_start += page_size
            continue
        empty_streak = 0

        if next_url:
            next_url = extract_next_page_url(html, current_url)
            if not next_url:
                break
        else:
            current_start += page_size

    _progress_done()
    return collected if fetch_all else collected[:limit]


def parse_results_from_html(html: str, limit: int = 10) -> list[dict[str, Any]]:
    pattern = re.compile(
        r'<a href="(?P<link>https://[^\"]+)"[^>]*class="poly-component__title"[^>]*>'
        r'(?P<title>.*?)</a>',
        flags=re.DOTALL,
    )

    results: list[dict[str, Any]] = []
    for match in pattern.finditer(html):
        start = match.start()
        end = html.find('<h3 class="poly-component__title-wrapper">', start + 1)
        if end == -1:
            end = min(len(html), start + 6000)

        block = html[start:end]
        raw_link = unescape(match.group("link"))
        link = raw_link.split("#", 1)[0]
        if "mclicks" in link or "mclics" in link:
            continue

        title = clean_html_text(match.group("title"))
        price = extract_price_from_block(block)
        image = extract_image_from_block(block)
        discount_percent = extract_discount_percent_from_block(block)
        condition = extract_condition_from_block(block)

        if not title:
            continue

        results.append(
            {
                "position": len(results) + 1,
                "title": title,
                "price": price,
                "link": link,
                "image": image,
                "discount_percent": discount_percent,
                "condition": condition,
            }
        )
        if len(results) >= limit:
            break

    return results


def fetch_product_condition(link: str, timeout: int = 20) -> str | None:
    try:
        html = fetch_url_html(link, timeout=timeout)
    except Exception:
        return None

    match = re.search(r'"itemCondition"\s*:\s*"([^"]+)"', html)
    if not match:
        return None

    value = unescape(match.group(1)).lower()
    if "newcondition" in value:
        return "new"
    if "usedcondition" in value:
        return "used"
    if "refurbishedcondition" in value or "reconditionedcondition" in value:
        return "reconditioned"
    return None


def enrich_items_with_condition(items: list[dict[str, Any]], max_workers: int = 12) -> None:
    if not items:
        return

    workers = max(1, min(max_workers, 24))
    pending = [item for item in items if not item.get("condition")]
    if not pending:
        return

    def task(item: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
        return item, fetch_product_condition(item["link"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(task, item) for item in pending]
        done = 0
        total = len(futures)
        for future in concurrent.futures.as_completed(futures):
            item, condition = future.result()
            if condition:
                item["condition"] = condition
            done += 1
            _progress("Leyendo estado", done, total)
    _progress_done()


def parse_price_value(price_text: str | None) -> int | None:
    if not price_text:
        return None
    digits = "".join(ch for ch in str(price_text) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def apply_filters(
    items: list[dict[str, Any]],
    min_price: int,
    max_price: int,
    word: str,
    min_discount: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    word_lc = word.strip().lower()
    for item in items:
        price_val = parse_price_value(item.get("price"))
        if min_price > 0 and (price_val is None or price_val < min_price):
            continue
        if max_price > 0 and (price_val is None or price_val > max_price):
            continue
        if word_lc and word_lc not in str(item.get("title", "")).lower():
            continue
        discount = item.get("discount_percent")
        if min_discount > 0 and (discount is None or int(discount) < min_discount):
            continue
        out.append(item)
    return out


def sort_items_by_price(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key_fn(item: dict[str, Any]) -> tuple[int, int]:
        price = parse_price_value(item.get("price"))
        if price is None:
            return (1, 10**18)
        return (0, price)

    sorted_items = sorted(items, key=key_fn)
    for idx, item in enumerate(sorted_items, start=1):
        item["position"] = idx
    return sorted_items


def xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_xlsx_bytes(items: list[dict[str, Any]]) -> bytes:
    headers = ["Posicion", "Titulo", "Precio", "Descuento", "Estado", "Link"]
    rows: list[list[str | int]] = [headers]
    state_map = {"new": "Nuevo", "used": "Usado", "reconditioned": "Reacondicionado"}
    for idx, item in enumerate(items, start=1):
        rows.append(
            [
                idx,
                str(item.get("title") or ""),
                str(item.get("price") or ""),
                (f"{item.get('discount_percent')}%" if item.get("discount_percent") is not None else ""),
                state_map.get(str(item.get("condition") or "").lower(), "N/D"),
                str(item.get("link") or ""),
            ]
        )

    sheet_rows: list[str] = []
    for r_idx, row in enumerate(rows, start=1):
        cells: list[str] = []
        for c_idx, value in enumerate(row, start=1):
            col = ""
            n = c_idx
            while n:
                n, rem = divmod(n - 1, 26)
                col = chr(65 + rem) + col
            ref = f"{col}{r_idx}"
            if isinstance(value, int):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{xml_escape(str(value))}</t></is></c>')
        sheet_rows.append(f"<row r=\"{r_idx}\">{''.join(cells)}</row>")

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Resultados" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    buf = BytesIO()
    with ZipFile(buf, mode="w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


def export_xlsx(items: list[dict[str, Any]], query: str, country: str, output_path: str | None) -> Path:
    if output_path and output_path != "__AUTO__":
        out = Path(output_path)
    else:
        safe_query = re.sub(r"[^a-zA-Z0-9_-]+", "_", query)[:40].strip("_") or "busqueda"
        out = Path("exports") / f"mercadolibre_{country}_{safe_query}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(build_xlsx_bytes(items))
    return out


def run(
    query: str,
    limit: int,
    as_json: bool,
    country: str,
    condition_filter: str,
    fetch_all: bool,
    max_pages: int,
    include_condition: bool,
    exclude_international: bool,
    min_price: int,
    max_price: int,
    word_filter: str,
    min_discount: int,
    sort_price: bool,
    export_xlsx_path: str | None,
    condition_workers: int,
    skip_condition_in_export: bool,
    search_url: str | None,
) -> int:
    parse_limit = limit if condition_filter == "any" else min(max(limit * 4, limit), 80)
    items = collect_results(
        query=query,
        country=country,
        limit=parse_limit,
        fetch_all=fetch_all,
        max_pages=max_pages,
        exclude_international=exclude_international,
        min_price=min_price,
        max_price=max_price,
        min_discount=min_discount,
        sort_price=sort_price,
        condition_filter=condition_filter,
        search_url=search_url,
    )

    # Apply cheap filters first to avoid fetching product condition for thousands of items.
    items = apply_filters(
        items,
        min_price=min_price,
        max_price=max_price,
        word=word_filter,
        min_discount=min_discount,
    )

    if condition_filter != "any":
        for item in items:
            item["condition"] = condition_filter

    needs_condition = (
        include_condition
        or (export_xlsx_path is not None and not skip_condition_in_export)
    )
    if needs_condition and items:
        enrich_items_with_condition(items, max_workers=condition_workers)

    if condition_filter != "any":
        items = [item for item in items if item.get("condition") == condition_filter]
        if not fetch_all:
            items = items[:limit]

    if sort_price:
        items = sort_items_by_price(items)
    else:
        for idx, item in enumerate(items, start=1):
            item["position"] = idx

    if not items:
        print("No se encontraron resultados o cambió el HTML de Mercado Libre.")
        return 1

    if export_xlsx_path is not None:
        out = export_xlsx(items, query=query, country=country, output_path=export_xlsx_path)
        print(f"Excel generado: {out}")
        return 0

    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    print(f"Resultados para: {query!r} [{country.upper()}] (mostrando {len(items)})\n")
    for item in items:
        print(f"{item['position']}. {item['title']}")
        print(f"   Precio: {item['price'] or 'N/D'}")
        if item.get("discount_percent") is not None:
            print(f"   Descuento: {item['discount_percent']}%")
        if item.get("condition"):
            print(f"   Condición: {item['condition']}")
        print(f"   Link: {item['link']}")

    return 0


def main() -> int:
    started_at = time.perf_counter()
    exit_code = 0
    parser = argparse.ArgumentParser(
        description="Scraper simple de resultados de búsqueda en Mercado Libre."
    )
    parser.add_argument(
        "query",
        nargs="*",
        default=["notebook", "rtx"],
        help="Término de búsqueda (ej: notebook rtx)",
    )
    parser.add_argument(
        "--country",
        choices=sorted(DOMAIN_BY_COUNTRY.keys()),
        default="cl",
        help="País de Mercado Libre (default: cl)",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Cantidad máxima de resultados"
    )
    parser.add_argument(
        "--json", action="store_true", help="Imprime los resultados en JSON"
    )
    parser.add_argument(
        "--condition",
        choices=["any", "new", "used", "reconditioned"],
        default="any",
        help="Filtra por condición del producto",
    )
    parser.add_argument(
        "--estado",
        choices=["cualquiera", "nuevo", "usado", "reacondicionado"],
        default=None,
        help="Alias en español de --condition",
    )
    parser.add_argument(
        "--all-results",
        action="store_true",
        help="Intenta recorrer paginación para traer todos los resultados",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Máximo de páginas a recorrer cuando se usa --all-results (0 = sin límite)",
    )
    parser.add_argument(
        "--include-condition",
        action="store_true",
        help="Incluye condición de cada producto (new/used/reconditioned)",
    )
    parser.add_argument(
        "--include-international",
        action="store_true",
        help="Incluye publicaciones internacionales (por defecto se excluyen)",
    )
    parser.add_argument(
        "--min-price",
        type=int,
        default=0,
        help="Precio mínimo (entero sin separadores)",
    )
    parser.add_argument(
        "--max-price",
        type=int,
        default=0,
        help="Precio máximo (entero sin separadores)",
    )
    parser.add_argument(
        "--word",
        default="",
        help="Filtra resultados por palabra en el título",
    )
    parser.add_argument(
        "--min-discount",
        type=int,
        default=0,
        help="Porcentaje mínimo de descuento (ej: 10)",
    )
    parser.add_argument(
        "--sort-price",
        action="store_true",
        help="Ordena resultados por precio ascendente",
    )
    parser.add_argument(
        "--export-xlsx",
        nargs="?",
        const="__AUTO__",
        default=None,
        help="Exporta a Excel. Opcional: ruta de salida",
    )
    parser.add_argument(
        "--condition-workers",
        type=int,
        default=16,
        help="Cantidad de workers para obtener estado por producto",
    )
    parser.add_argument(
        "--skip-condition-in-export",
        action="store_true",
        help="Acelera export Excel omitiendo la lectura del estado por producto",
    )
    parser.add_argument(
        "--cookie",
        default=None,
        help="Cookie header inline: 'a=1; b=2'",
    )
    parser.add_argument(
        "--cookie-file",
        default=None,
        help="Archivo .txt con cookie header completo",
    )
    parser.add_argument(
        "--search-url",
        default=None,
        help="URL exacta de listado de Mercado Libre para replicar filtros del navegador",
    )

    args = parser.parse_args()
    query = " ".join(args.query).strip()

    condition = args.condition
    if args.estado:
        estado_map = {
            "cualquiera": "any",
            "nuevo": "new",
            "usado": "used",
            "reacondicionado": "reconditioned",
        }
        condition = estado_map[args.estado]

    if not query:
        print("Debes indicar un término de búsqueda.")
        exit_code = 2
        return exit_code

    if args.limit < 1:
        print("--limit debe ser >= 1")
        exit_code = 2
        return exit_code

    try:
        configure_cookie_header(args.cookie, args.cookie_file)
        exit_code = run(
            query,
            args.limit,
            args.json,
            args.country,
            condition,
            args.all_results,
            args.max_pages,
            args.include_condition,
            not args.include_international,
            max(0, args.min_price),
            max(0, args.max_price),
            args.word,
            max(0, min(100, args.min_discount)),
            args.sort_price,
            args.export_xlsx,
            max(1, args.condition_workers),
            args.skip_condition_in_export,
            args.search_url,
        )
        return exit_code
    except Exception as exc:
        print(f"Error al obtener datos de Mercado Libre: {exc}", file=sys.stderr)
        exit_code = 1
        return exit_code
    finally:
        elapsed = time.perf_counter() - started_at
        print(f"Tiempo total: {elapsed:.2f}s")


if __name__ == "__main__":
    raise SystemExit(main())
