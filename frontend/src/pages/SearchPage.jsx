import React, { useState } from 'react'
import { searchByText } from '../api'
import MovieCard from '../components/MovieCard'

const EXAMPLES = [
  'romantic comedy with love story',
  'space adventure science fiction',
  'dark thriller mystery crime',
  'animated family children movie',
  'war historical drama',
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (q = query) => {
    if (!q.trim()) return
    setLoading(true)
    setSearched(true)
    const res = await searchByText(q.trim(), 12).catch(() => [])
    setResults(res)
    setLoading(false)
  }

  const s = {
    page: { maxWidth: 900, margin: '0 auto', padding: '40px 16px' },
    title: { fontSize: 26, fontWeight: 700, marginBottom: 8 },
    sub: { color: 'var(--text-muted)', marginBottom: 32, fontSize: 14 },
    row: { display: 'flex', gap: 10, marginBottom: 20 },
    input: {
      flex: 1, padding: '12px 16px',
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, color: 'var(--text)', fontSize: 14, outline: 'none'
    },
    btn: {
      padding: '12px 24px', background: 'var(--accent)',
      border: 'none', borderRadius: 8, color: '#fff',
      fontSize: 14, fontWeight: 600, cursor: 'pointer'
    },
    examples: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 32 },
    chip: {
      padding: '6px 14px', background: 'var(--surface)',
      border: '1px solid var(--border)', borderRadius: 20,
      fontSize: 12, cursor: 'pointer', color: 'var(--text-muted)',
      transition: 'all 0.15s'
    },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>🔍 Metin ile Film Ara</h1>
      <p style={s.sub}>
        İngilizce olarak istediğiniz film türünü veya konuyu yazın,
        Sentence-BERT anlamsal benzerlik ile en uygun filmleri bulsun.
      </p>

      <div style={s.row}>
        <input
          style={s.input}
          placeholder="Örn: action movie with superheroes"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button style={s.btn} onClick={() => handleSearch()}>Ara</button>
      </div>

      <div style={s.examples}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>Örnek:</span>
        {EXAMPLES.map(ex => (
          <span
            key={ex}
            style={s.chip}
            onClick={() => { setQuery(ex); handleSearch(ex) }}
            onMouseEnter={e => { e.target.style.borderColor = 'var(--accent)'; e.target.style.color = 'var(--text)' }}
            onMouseLeave={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.color = 'var(--text-muted)' }}
          >
            {ex}
          </span>
        ))}
      </div>

      {loading && <div style={{ color: 'var(--text-muted)', padding: 20 }}>Aranıyor...</div>}

      {!loading && searched && results.length === 0 && (
        <div style={{ color: 'var(--text-muted)', padding: 20 }}>Sonuç bulunamadı.</div>
      )}

      {!loading && results.length > 0 && (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
            "{query}" için {results.length} öneri
          </p>
          <div style={s.grid}>
            {results.map(m => <MovieCard key={m.movie_id} movie={m} showScore />)}
          </div>
        </>
      )}
    </div>
  )
}