import React, { useState, useEffect } from 'react'
import { getMovies, getSimilar, getMovie } from '../api'
import MovieCard from '../components/MovieCard'

const ALL_GENRES = ['Action','Adventure','Animation','Comedy','Crime',
  'Drama','Fantasy','Horror','Musical','Mystery','Romance','Sci-Fi','Thriller','War']

function fixTitle(title) {
  if (!title) return title
  return title.replace(/^(.*),\s*(The|A|An)\s*$/i, '$2 $1').trim()
}

export default function HomePage() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [genre, setGenre] = useState('')
  const [selected, setSelected] = useState(null)
  const [similar, setSimilar] = useState([])
  const [simLoading, setSimLoading] = useState(false)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    setLoading(true)
    getMovies(search, genre)
      .then(setMovies)
      .finally(() => setLoading(false))
  }, [search, genre])

  const handleSelect = async (movie) => {
    setSelected(movie)
    setSimilar([])
    setSimLoading(true)
    const [sim, det] = await Promise.all([
      getSimilar(movie.movie_id, 12),
      getMovie(movie.movie_id)
    ])
    setSimilar(sim)
    setDetail(det)
    setSimLoading(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const s = {
    page: { maxWidth: 1200, margin: '0 auto', padding: '24px 16px' },
    topBar: { display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' },
    input: {
      flex: 1, minWidth: 200, padding: '10px 16px',
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, color: 'var(--text)', fontSize: 14,
      outline: 'none'
    },
    select: {
      padding: '10px 16px', background: 'var(--surface)',
      border: '1px solid var(--border)', borderRadius: 8,
      color: 'var(--text)', fontSize: 14, cursor: 'pointer'
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
      gap: 16
    },
    detailBox: {
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: 20, marginBottom: 32,
      display: 'flex', gap: 20
    },
    detailPoster: { width: 120, borderRadius: 8, objectFit: 'cover', flexShrink: 0 },
    h2: { fontSize: 20, fontWeight: 700, marginBottom: 16 },
    h3: { fontSize: 16, fontWeight: 600, marginBottom: 4, color: 'var(--text)' },
    overview: { fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6 },
    closeBtn: {
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 6, color: 'var(--text-muted)', padding: '4px 12px',
      cursor: 'pointer', fontSize: 13
    }
  }

  return (
    <div style={s.page}>
      {/* Seçili film detay + benzer filmler */}
      {selected && (
        <div>
          <div style={s.detailBox}>
            <img
              src={detail?.poster_url || selected.poster_url || 'https://via.placeholder.com/120x180/1a1a24/7c6af7?text=?'}
              alt={fixTitle(selected.title)}
              style={s.detailPoster}
              onError={e => e.target.src = 'https://via.placeholder.com/120x180/1a1a24/7c6af7?text=?'}
            />
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h3 style={s.h3}>{fixTitle(selected.title)} {selected.release_year && `(${selected.release_year})`}</h3>
                <button style={s.closeBtn} onClick={() => { setSelected(null); setSimilar([]); setDetail(null) }}>✕ Kapat</button>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', margin: '6px 0' }}>
                {selected.genres?.join(' · ')}
                {selected.avg_rating && <span style={{ marginLeft: 8, color: '#f59e0b' }}>★ {selected.avg_rating.toFixed(1)}</span>}
              </div>
              <p style={s.overview}>{detail?.overview || 'Özet bilgisi yükleniyor...'}</p>
            </div>
          </div>

          <h2 style={s.h2}>🎯 Benzer Filmler</h2>
          {simLoading ? (
            <div style={{ color: 'var(--text-muted)', padding: 20 }}>Yükleniyor...</div>
          ) : (
            <div style={{ ...s.grid, marginBottom: 40 }}>
              {similar.map(m => <MovieCard key={m.movie_id} movie={m} showScore onClick={handleSelect} />)}
            </div>
          )}
          <hr style={{ border: 'none', borderTop: '1px solid var(--border)', marginBottom: 32 }} />
        </div>
      )}

      {/* Arama + filtre */}
      <div style={s.topBar}>
        <input
          style={s.input}
          placeholder="🔎 Film adı ara..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select style={s.select} value={genre} onChange={e => setGenre(e.target.value)}>
          <option value="">Tüm Türler</option>
          {ALL_GENRES.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-muted)', padding: 40, textAlign: 'center' }}>Filmler yükleniyor...</div>
      ) : (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 16 }}>
            {movies.length} film · Bir filme tıklayarak benzer öneriler alın
          </p>
          <div style={s.grid}>
            {movies.map(m => <MovieCard key={m.movie_id} movie={m} onClick={handleSelect} />)}
          </div>
        </>
      )}
    </div>
  )
}