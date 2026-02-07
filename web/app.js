const q = document.getElementById('q');
const minPrice = document.getElementById('min_price');
const maxPrice = document.getElementById('max_price');
const minDiscount = document.getElementById('min_discount');
const searchBtn = document.getElementById('search');
const results = document.getElementById('results');
const summary = document.getElementById('summary');

function money(value, currency = 'ARS') {
  if (value == null) return '-';
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency }).format(value);
}

function card(item) {
  return `
    <div class="item">
      <img src="${item.thumbnail || ''}" alt="${item.title}" />
      <h3>${item.title}</h3>
      <div class="meta">Precio: ${money(item.price, item.currency_id || 'ARS')}</div>
      <div class="meta">Original: ${money(item.original_price, item.currency_id || 'ARS')}</div>
      <div class="meta">Descuento: ${item.discount_pct || 0}%</div>
      <a class="link" href="${item.permalink}" target="_blank" rel="noopener noreferrer">Ver producto</a>
    </div>
  `;
}

async function load() {
  const params = new URLSearchParams({
    q: q.value,
    min_price: minPrice.value,
    max_price: maxPrice.value,
    min_discount: minDiscount.value,
  });

  const response = await fetch(`/api/products?${params.toString()}`);
  const data = await response.json();

  summary.textContent = `Resultados: ${data.count}`;
  results.innerHTML = data.products.map(card).join('');
}

searchBtn.addEventListener('click', load);
load();
