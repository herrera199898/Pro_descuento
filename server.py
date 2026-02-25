from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "mercadolibre.py"


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


@app.post("/api/count")
def count_results(payload: SearchPayload) -> dict:
    if not payload.query.strip() and not payload.search_url.strip():
        raise HTTPException(status_code=400, detail="Debes indicar query o search_url.")

    cmd = _build_base_cmd(payload) + ["--json"]
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
            detail=(proc.stderr or proc.stdout or "Error ejecutando scraper").strip(),
        )

    items = _extract_json(proc.stdout)
    return {
        "count": len(items),
        "elapsed_seconds": round(elapsed, 2),
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
