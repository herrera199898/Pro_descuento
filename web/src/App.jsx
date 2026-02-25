import { useMemo, useState } from 'react'
import './App.css'

function App() {
  const [form, setForm] = useState({
    query: 'notebook rtx',
    country: 'cl',
    all_results: true,
    max_pages: 0,
    min_price: 0,
    max_price: 0,
    min_discount: 0,
    word: '',
    include_words: [],
    exclude_words: [],
    condition: 'any',
    sort_price: true,
    include_international: false,
    cookie_file: 'cookies.txt',
    search_url: '',
  })
  const [count, setCount] = useState(null)
  const [elapsed, setElapsed] = useState(null)
  const [applied, setApplied] = useState(null)
  const [status, setStatus] = useState('')
  const [loadingCount, setLoadingCount] = useState(false)
  const [loadingExport, setLoadingExport] = useState(false)
  const [countRunMs, setCountRunMs] = useState(0)
  const [exportRunMs, setExportRunMs] = useState(0)
  const [includeDraft, setIncludeDraft] = useState('')
  const [excludeDraft, setExcludeDraft] = useState('')

  const canSubmit = useMemo(
    () => Boolean(form.query.trim() || form.search_url.trim()),
    [form.query, form.search_url],
  )

  const onChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const runWithLiveTimer = async (setterLoading, setterRunMs, task) => {
    setterLoading(true)
    setterRunMs(0)
    const startedAt = performance.now()
    const tick = setInterval(() => {
      setterRunMs(performance.now() - startedAt)
    }, 120)
    try {
      await task()
    } finally {
      clearInterval(tick)
      setterRunMs(performance.now() - startedAt)
      setterLoading(false)
    }
  }

  const addExcludeWord = () => {
    const value = excludeDraft.trim()
    if (!value) return
    setForm((prev) => {
      if (prev.exclude_words.includes(value)) return prev
      return { ...prev, exclude_words: [...prev.exclude_words, value] }
    })
    setExcludeDraft('')
  }

  const addIncludeWord = () => {
    const value = includeDraft.trim()
    if (!value) return
    setForm((prev) => {
      if (prev.include_words.includes(value)) return prev
      return { ...prev, include_words: [...prev.include_words, value] }
    })
    setIncludeDraft('')
  }

  const removeIncludeWord = (word) => {
    setForm((prev) => ({
      ...prev,
      include_words: prev.include_words.filter((w) => w !== word),
    }))
  }

  const removeExcludeWord = (word) => {
    setForm((prev) => ({
      ...prev,
      exclude_words: prev.exclude_words.filter((w) => w !== word),
    }))
  }

  const runCount = async () => {
    if (!canSubmit) return
    setStatus('')
    await runWithLiveTimer(setLoadingCount, setCountRunMs, async () => {
      try {
        const res = await fetch('/api/count', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Error en conteo')
        setCount(data.count)
        setElapsed(data.elapsed_seconds)
        setApplied(data.applied_filters || null)
      } catch (err) {
        setStatus(err.message)
      }
    })
  }

  const runExport = async () => {
    if (!canSubmit) return
    setStatus('')
    await runWithLiveTimer(setLoadingExport, setExportRunMs, async () => {
      try {
        const res = await fetch('/api/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form),
        })
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || 'Error exportando')
        }
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `mercadolibre_export_${Date.now()}.xlsx`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
        setStatus('Excel exportado correctamente.')
      } catch (err) {
        setStatus(err.message)
      }
    })
  }

  return (
    <main className="page">
      <section className="panel">
        <h1>MercadoLibre Export UI</h1>
        <p className="hint">
          Configura filtros, calcula cantidad de resultados y exporta Excel sin listar productos.
        </p>

        <div className="grid">
          <label>
            Busqueda
            <input value={form.query} onChange={(e) => onChange('query', e.target.value)} />
          </label>
          <label>
            Pais
            <select value={form.country} onChange={(e) => onChange('country', e.target.value)}>
              <option value="cl">Chile</option>
              <option value="ar">Argentina</option>
              <option value="mx">Mexico</option>
              <option value="co">Colombia</option>
              <option value="pe">Peru</option>
            </select>
          </label>
          <label>
            Precio minimo
            <input
              type="number"
              value={form.min_price}
              onChange={(e) => onChange('min_price', Number(e.target.value || 0))}
            />
          </label>
          <label>
            Precio maximo
            <input
              type="number"
              value={form.max_price}
              onChange={(e) => onChange('max_price', Number(e.target.value || 0))}
            />
          </label>
          <label>
            Descuento minimo %
            <input
              type="number"
              min="0"
              max="100"
              value={form.min_discount}
              onChange={(e) => onChange('min_discount', Number(e.target.value || 0))}
            />
          </label>
          <label>
            Estado
            <select value={form.condition} onChange={(e) => onChange('condition', e.target.value)}>
              <option value="any">Cualquiera</option>
              <option value="new">Nuevo</option>
              <option value="used">Usado</option>
              <option value="reconditioned">Reacondicionado</option>
            </select>
          </label>
          <label className="full">
            Palabras a incluir (dinamico)
            <div className="exclude-editor">
              <input
                placeholder="ej: gamer"
                value={includeDraft}
                onChange={(e) => setIncludeDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addIncludeWord()
                  }
                }}
              />
              <button type="button" onClick={addIncludeWord}>
                Agregar
              </button>
            </div>
            <div className="chips">
              {form.include_words.map((word) => (
                <button
                  className="chip include"
                  key={word}
                  type="button"
                  onClick={() => removeIncludeWord(word)}
                  title="Quitar"
                >
                  {word} x
                </button>
              ))}
            </div>
          </label>
          <label className="full">
            Palabras a descartar (dinamico)
            <div className="exclude-editor">
              <input
                placeholder="ej: carcasa"
                value={excludeDraft}
                onChange={(e) => setExcludeDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addExcludeWord()
                  }
                }}
              />
              <button type="button" onClick={addExcludeWord}>
                Agregar
              </button>
            </div>
            <div className="chips">
              {form.exclude_words.map((word) => (
                <button
                  className="chip exclude"
                  key={word}
                  type="button"
                  onClick={() => removeExcludeWord(word)}
                  title="Quitar"
                >
                  {word} x
                </button>
              ))}
            </div>
          </label>
          <label>
            Max paginas (0 = sin limite)
            <input
              type="number"
              value={form.max_pages}
              onChange={(e) => onChange('max_pages', Number(e.target.value || 0))}
            />
          </label>
          <label className="full">
            URL exacta (opcional)
            <input
              placeholder="https://listado.mercadolibre.cl/..."
              value={form.search_url}
              onChange={(e) => onChange('search_url', e.target.value)}
            />
          </label>
          <label className="full">
            Archivo cookies (opcional)
            <input value={form.cookie_file} onChange={(e) => onChange('cookie_file', e.target.value)} />
          </label>
        </div>

        <div className="checks">
          <label>
            <input
              type="checkbox"
              checked={form.all_results}
              onChange={(e) => onChange('all_results', e.target.checked)}
            />
            Buscar todas las paginas
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.sort_price}
              onChange={(e) => onChange('sort_price', e.target.checked)}
            />
            Ordenar por precio
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.include_international}
              onChange={(e) => onChange('include_international', e.target.checked)}
            />
            Incluir internacionales
          </label>
        </div>

        <div className="actions">
          <button className="btn primary" disabled={!canSubmit || loadingCount} onClick={runCount}>
            {loadingCount ? (
              <span className="btn-content">
                <span className="loader" />
                Calculando... {(countRunMs / 1000).toFixed(1)}s
              </span>
            ) : (
              'Calcular cantidad'
            )}
          </button>
          <button className="btn success" disabled={!canSubmit || loadingExport} onClick={runExport}>
            {loadingExport ? (
              <span className="btn-content">
                <span className="loader" />
                Exportando... {(exportRunMs / 1000).toFixed(1)}s
              </span>
            ) : (
              'Exportar Excel'
            )}
          </button>
        </div>

        <div className="results">
          <div>
            <strong>Resultados:</strong> {count ?? '-'}
          </div>
          <div>
            <strong>Tiempo:</strong> {elapsed != null ? `${elapsed}s` : '-'}
          </div>
          {applied && (
            <div>
              <strong>Filtros aplicados:</strong>{' '}
              include=[{(applied.include_words || []).join(', ')}] exclude=[
              {(applied.exclude_words || []).join(', ')}]
            </div>
          )}
          {status && <div className="status">{status}</div>}
          {(loadingCount || loadingExport) && (
            <div className="running-hint">
              Proceso activo: {loadingCount ? 'calculo de resultados' : 'exportacion de Excel'}
            </div>
          )}
        </div>
      </section>
    </main>
  )
}

export default App
