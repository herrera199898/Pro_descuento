from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import mercadolibre as ml

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "mercadolibre.py"
COUNT_CACHE_TTL_SECONDS = 300
_COUNT_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_LOCK = threading.Lock()


class SearchPayload(BaseModel):
    query: str = Field(default="")
    country: str = Field(default="cl")
    all_results: bool = Field(default=True)
    max_pages: int = Field(default=0)
    min_price: int = Field(default=0)
    max_price: int = Field(default=0)
    min_discount: int = Field(default=0)
    word: str = Field(default="")
    include_words: list[str] = Field(default_factory=list)
    exclude_words: list[str] = Field(default_factory=list)
    condition: str = Field(default="any")
    sort_price: bool = Field(default=True)
    include_international: bool = Field(default=False)
    cookie_file: str = Field(default="")
    search_url: str = Field(default="")
    preview_limit: int = Field(default=200)


app = FastAPI(title="MercadoLibre UI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_base_cmd(payload: SearchPayload) -> list[str]:
    cmd = [sys.executable, str(SCRIPT)]
    query = payload.query.strip()
    if query:
        cmd.extend(query.split())

    cmd.extend(["--country", payload.country])
    if payload.all_results:
        cmd.append("--all-results")
    cmd.extend(["--max-pages", str(payload.max_pages)])
    cmd.extend(["--min-price", str(max(0, payload.min_price))])
    cmd.extend(["--max-price", str(max(0, payload.max_price))])
    cmd.extend(["--min-discount", str(max(0, min(100, payload.min_discount)))])
    if payload.word.strip():
        cmd.extend(["--word", payload.word.strip()])
    for word in payload.include_words:
        word = str(word).strip()
        if word:
            cmd.extend(["--include-word", word])
    for word in payload.exclude_words:
        word = str(word).strip()
        if word:
            cmd.extend(["--exclude-word", word])
    if payload.condition != "any":
        cmd.extend(["--condition", payload.condition])
    if payload.sort_price:
        cmd.append("--sort-price")
    if payload.include_international:
        cmd.append("--include-international")
    if payload.cookie_file.strip():
        cmd.extend(["--cookie-file", payload.cookie_file.strip()])
    if payload.search_url.strip():
        cmd.extend(["--search-url", payload.search_url.strip()])
    return cmd


def _extract_json(stdout_text: str) -> list[dict]:
    start = stdout_text.find("[")
    end = stdout_text.rfind("]")
    if start < 0 or end < 0 or end <= start:
        return []
    try:
        return json.loads(stdout_text[start : end + 1])
    except json.JSONDecodeError:
        return []


def _to_excel_preview_rows(items: list[dict]) -> list[dict]:
    state_map = {"new": "Nuevo", "used": "Usado", "reconditioned": "Reacondicionado"}
    rows: list[dict] = []
    for idx, item in enumerate(items, start=1):
        raw_condition = str(item.get("condition") or "").lower().strip()
        rows.append(
            {
                "Posicion": idx,
                "Titulo": str(item.get("title") or ""),
                "Precio": str(item.get("price") or ""),
                "Descuento": (
                    f"{item.get('discount_percent')}%"
                    if item.get("discount_percent") is not None
                    else ""
                ),
                "Estado": state_map.get(raw_condition, "N/D"),
                "Link": str(item.get("link") or ""),
            }
        )
    return rows


def _payload_cache_key(payload: SearchPayload) -> str:
    normalized = {
        "query": payload.query.strip(),
        "country": payload.country,
        "all_results": bool(payload.all_results),
        "max_pages": int(payload.max_pages),
        "min_price": int(max(0, payload.min_price)),
        "max_price": int(max(0, payload.max_price)),
        "min_discount": int(max(0, min(100, payload.min_discount))),
        "word": payload.word.strip(),
        "include_words": sorted([str(w).strip() for w in payload.include_words if str(w).strip()]),
        "exclude_words": sorted([str(w).strip() for w in payload.exclude_words if str(w).strip()]),
        "condition": payload.condition,
        "sort_price": bool(payload.sort_price),
        "include_international": bool(payload.include_international),
        "cookie_file": payload.cookie_file.strip(),
        "search_url": payload.search_url.strip(),
    }
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict | None:
    now = time.time()
    with _CACHE_LOCK:
        entry = _COUNT_CACHE.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at < now:
            _COUNT_CACHE.pop(key, None)
            return None
        return value


def _cache_set(key: str, value: dict) -> None:
    expires_at = time.time() + COUNT_CACHE_TTL_SECONDS
    with _CACHE_LOCK:
        _COUNT_CACHE[key] = (expires_at, value)


def _count_in_process(payload: SearchPayload) -> dict:
    ml.configure_cookie_header(None, payload.cookie_file.strip() or None)
    condition_filter = payload.condition if payload.condition in {"any", "new", "used", "reconditioned"} else "any"
    fetch_all = bool(payload.all_results)
    limit = 10

    items = ml.collect_results(
        query=payload.query.strip(),
        country=payload.country,
        limit=limit if condition_filter == "any" else min(max(limit * 4, limit), 80),
        fetch_all=fetch_all,
        max_pages=int(payload.max_pages),
        exclude_international=not bool(payload.include_international),
        min_price=max(0, int(payload.min_price)),
        max_price=max(0, int(payload.max_price)),
        min_discount=max(0, min(100, int(payload.min_discount))),
        sort_price=bool(payload.sort_price),
        condition_filter=condition_filter,
        search_url=payload.search_url.strip() or None,
        quiet=True,
    )

    items = ml.apply_filters(
        items,
        min_price=max(0, int(payload.min_price)),
        max_price=max(0, int(payload.max_price)),
        word=payload.word.strip(),
        include_words=[str(w).strip() for w in payload.include_words if str(w).strip()],
        min_discount=max(0, min(100, int(payload.min_discount))),
        exclude_words=[str(w).strip() for w in payload.exclude_words if str(w).strip()],
    )

    if condition_filter != "any":
        items = [item for item in items if item.get("condition") == condition_filter]
        if not fetch_all:
            items = items[:limit]

    return {"count": len(items)}


@app.post("/api/count")
def count_results(payload: SearchPayload) -> dict:
    if not payload.query.strip() and not payload.search_url.strip():
        raise HTTPException(status_code=400, detail="Debes indicar query o search_url.")

    cache_key = _payload_cache_key(payload)
    cached = _cache_get(cache_key)
    if cached is not None:
        return {
            **cached,
            "cache_hit": True,
        }

    started = time.perf_counter()
    try:
        computed = _count_in_process(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error ejecutando scraper: {exc}") from exc
    elapsed = time.perf_counter() - started
    response = {
        "count": computed["count"],
        "elapsed_seconds": round(elapsed, 2),
        "cache_hit": False,
        "applied_filters": {
            "query": payload.query,
            "min_price": payload.min_price,
            "max_price": payload.max_price,
            "include_words": payload.include_words,
            "exclude_words": payload.exclude_words,
            "condition": payload.condition,
            "country": payload.country,
        },
    }
    _cache_set(cache_key, response)
    return response


@app.post("/api/export")
def export_results(payload: SearchPayload):
    if not payload.query.strip() and not payload.search_url.strip():
        raise HTTPException(status_code=400, detail="Debes indicar query o search_url.")

    with tempfile.NamedTemporaryFile(prefix="ml_export_", suffix=".xlsx", delete=False) as tmp:
        export_path = Path(tmp.name)

    cmd = _build_base_cmd(payload) + ["--export-xlsx", str(export_path)]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=1800,
        check=False,
    )
    if proc.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=(proc.stderr or proc.stdout or "Error exportando").strip(),
        )
    if not export_path.exists():
        raise HTTPException(status_code=500, detail="No se generó el archivo Excel.")

    return FileResponse(
        path=export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=export_path.name,
    )


@app.post("/api/preview")
def preview_results(payload: SearchPayload) -> dict:
    if not payload.query.strip() and not payload.search_url.strip():
        raise HTTPException(status_code=400, detail="Debes indicar query o search_url.")

    limit = max(1, min(int(payload.preview_limit or 200), 2000))
    cmd = _build_base_cmd(payload) + ["--json", "--include-condition", "--limit", str(limit)]
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=1800,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=(proc.stderr or proc.stdout or "Error en previsualización").strip(),
        )

    items = _extract_json(proc.stdout)
    rows = _to_excel_preview_rows(items)
    return {
        "columns": ["Posicion", "Titulo", "Precio", "Descuento", "Estado", "Link"],
        "rows": rows,
        "count": len(rows),
        "elapsed_seconds": round(elapsed, 2),
        "limit": limit,
    }
