# Proyecto Descuento

Proyecto base para recolectar productos de Mercado Libre, analizarlos y exponerlos en una web de prueba.

## Requisitos

- Python 3.10+

## Flujo

1. Ejecutar el scraper para traer productos a `data/products.json`.
2. Levantar servidor local.
3. Usar la web para filtrar por precio, descuento y palabras clave.

## Uso

```bash
python scripts/fetch_mercadolibre.py --query "notebook" --limit 50
python server.py
```

Si la API devuelve `403` desde tu red, usa:

```bash
python scripts/fetch_mercadolibre.py --query "notebook" --limit 50 --use-sample-on-error
```

Luego abrir:

- http://localhost:8000

## Filtros disponibles (web)

- Texto libre (`q`)
- Precio mínimo y máximo
- Descuento mínimo (%)

## Notas

- Se usa la API pública de búsqueda de Mercado Libre:
  `https://api.mercadolibre.com/sites/MLA/search?q=...`
- El dataset queda local para que luego me compartas tus pedidos y yo te ayude a analizar.
