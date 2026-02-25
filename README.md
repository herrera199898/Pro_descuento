# MercadoLibre Scraper (CLI)

Script de consola para buscar productos en Mercado Libre y exportar resultados a Excel.

## Modo visual (React + API)

Ahora el proyecto incluye una interfaz visual para:

- Aplicar filtros (pais, precio, descuento, estado, palabra, etc.)
- Ver solo cantidad de resultados y tiempo
- Exportar Excel sin listar productos

### Requisitos adicionales

- Node.js LTS (para frontend React)
- Python 3.10+

### Levantar backend API (FastAPI)

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

### Levantar frontend React (Vite)

```bash
cd web
npm install
npm run dev
```

La UI quedara disponible en `http://127.0.0.1:5173` y usara proxy a `/api`.

### Un solo comando (backend + frontend)

```bash
python run_dev.py
```

## Requisitos

- Python 3.10+
- Conexión a internet

## Uso básico

```bash
python mercadolibre.py notebook rtx --country cl --limit 20
```

## Salida JSON

```bash
python mercadolibre.py notebook rtx --country cl --limit 20 --json
```

## Traer más resultados (paginación)

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --json
```

Sin límite de páginas (hasta que no haya más resultados):

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 0 --json
```

## Exportar a Excel (ruta automática)

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --sort-price --export-xlsx
```

## Exportar a Excel (ruta específica)

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --sort-price --export-xlsx exports\\notebook_rtx.xlsx
```

## Filtros útiles

### Precio mínimo y máximo

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --min-price 700000 --max-price 1800000 --export-xlsx
```

### Filtrar por palabra en el título

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --word victus --export-xlsx
```

### Descartar palabras en el título (múltiples)

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --exclude-word funda --exclude-word carcasa --export-xlsx
```

### Filtrar por descuento mínimo

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --min-discount 10 --export-xlsx
```

### Filtrar por condición

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --condition used --export-xlsx
```

Valores de `--condition`:

- `any`
- `new`
- `used`
- `reconditioned`

También puedes usar alias en español con `--estado`:

```bash
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --estado usado --export-xlsx
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --estado nuevo --export-xlsx
python mercadolibre.py notebook rtx --country cl --all-results --max-pages 20 --estado reacondicionado --export-xlsx
```

## Rendimiento

- El script imprime al final: `Tiempo total: X.XXs`.
- Ajusta `--max-pages` para equilibrar cobertura vs tiempo.
- Ajusta `--condition-workers` (default: 16) para acelerar lectura de estado.

## Notas

- Por defecto se excluyen publicaciones internacionales.
- Para incluir internacionales usa `--include-international`.
- Los excels se guardan por defecto en `exports/`.
## Sesion autenticada (cookies)

Si Mercado Libre bloquea resultados (pagina shell), puedes pasar cookies de sesion:

```bash
python mercadolibre.py celular --country cl --all-results --max-pages 0 --sort-price --export-xlsx --cookie "_d2id=...; _mldataSessionId=...; _csrf=..."
```

O desde archivo de texto:

```bash
python mercadolibre.py celular --country cl --all-results --max-pages 0 --sort-price --export-xlsx --cookie-file cookies.txt
```

`cookies.txt` debe contener una sola linea con formato `name=value; name2=value2`.

## Replicar exactamente la URL del navegador

Si quieres que el scraper use los mismos filtros/categorias de la URL del navegador:

```bash
python mercadolibre.py --search-url "https://listado.mercadolibre.cl/..." --all-results --max-pages 0 --export-xlsx --cookie-file cookies.txt
```
