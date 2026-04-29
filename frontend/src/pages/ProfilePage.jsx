import React, { useState, useEffect } from 'react'
import { getMovies, getUserRecommendations } from '../api'
import MovieCard from '../components/MovieCard'

export default function ProfilePage() {
  const [allMovies, setAllMovies] = useState([])
  const [search, setSearch] = useState('')
  const [watched, setWatched] = useState([]) // [{movie, rating}]
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getMovies('', '').then(setAllMovies)
  }, [])

  const filtered = search.length > 1
    ? allMovies.filter(m => m.title.toLowerCase().includes(search.toLowerCase())).slice(0, 20)
    : []

  const addMovie = (movie) => {
    if (watched.find(w => w.movie.movie_id === movie.movie_id)) return
    setWatched(prev => [...prev, { movie, rating: 4 }])
    setSearch('')
  }

  const removeMovie = (id) => setWatched(prev => prev.filter(w => w.movie.movie_id !== id))

  const updateRating = (id, rating) =>
    setWatched(prev => prev.map(w => w.movie.movie_id === id ? { ...w, rating } : w))

  const getRecommendations = async () => {
    if (watched.length === 0) return
    setLoading(true)
    const ids = watched.map(w => w.movie.movie_id)
    const ratings = watched.map(w => w.rating)
    const res = await getUserRecommendations(ids, ratings, 12).catch(() => [])
    setRecommendations(res)
    setLoading(false)
  }

  const s = {
    page: { maxWidth: 1100, margin: '0 auto', padding: '32px 16px' },
    title: { fontSize: 24, fontWeight: 700, marginBottom: 8 },
    sub: { color: 'var(--text-muted)', fontSize: 14, marginBottom: 28 },
    section: { marginBottom: 32 },
    label: { fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' },
    searchBox: { position: 'relative', maxWidth: 400 },
    input: {
      width: '100%', padding: '10px 16px',
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, color: 'var(--text)', fontSize: 14, outline: 'none'
    },
    dropdown: {
      position: 'absolute', top: '100%', left: 0, right: 0,
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 8, marginTop: 4, zIndex: 50,
      maxHeight: 280, overflowY: 'auto'
    },
    dropItem: {
      padding: '8px 16px', cursor: 'pointer', fontSize: 13,
      borderBottom: '1px solid var(--border)', transition: 'background 0.1s'
    },
    watchedList: { display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 600 },
    watchedItem: {
      display: 'flex', alignItems: 'center', gap: 12,
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 14px'
    },
    ratingRow: { display: 'flex', gap: 4 },
    starBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, padding: 2 },
    removeBtn: {
      marginLeft: 'auto', background: 'none', border: '1px solid var(--border)',
      borderRadius: 6, color: 'var(--text-muted)', cursor: 'pointer',
      padding: '2px 10px', fontSize: 12
    },
    recBtn: {
      padding: '12px 28px', background: watched.length ? 'var(--accent)' : 'var(--surface2)',
      border: 'none', borderRadius: 8, color: watched.length ? '#fff' : 'var(--text-muted)',
      fontSize: 14, fontWeight: 600, cursor: watched.length ? 'pointer' : 'not-allowed'
    },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>👤 Profilim</h1>
      <p style={s.sub}>İzlediğiniz filmleri ekleyin ve puanlayın, kişisel öneriler alın.</p>

      {/* Film Ekle */}
      <div style={s.section}>
        <div style={s.label}>İzlediğim Filmler Ekle</div>
        <div style={s.searchBox}>
          <input
            style={s.input}
            placeholder="Film adı yazın..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {filtered.length > 0 && (
            <div style={s.dropdown}>
              {filtered.map(m => (
                <div
                  key={m.movie_id}
                  style={s.dropItem}
                  onClick={() => addMovie(m)}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--border)'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}
                >
                  <strong>{m.title}</strong>
                  <span style={{ color: 'var(--text-muted)', marginLeft: 8, fontSize: 12 }}>
                    {m.release_year} · {m.genres?.slice(0, 2).join(', ')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* İzleme Listesi */}
      {watched.length > 0 && (
        <div style={s.section}>
          <div style={s.label}>Listem ({watched.length} film)</div>
          <div style={s.watchedList}>
            {watched.map(({ movie, rating }) => (
              <div key={movie.movie_id} style={s.watchedItem}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{movie.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{movie.genres?.slice(0, 2).join(', ')}</div>
                </div>
                <div style={s.ratingRow}>
                  {[1,2,3,4,5].map(star => (
                    <button
                      key={star}
                      style={s.starBtn}
                      onClick={() => updateRating(movie.movie_id, star)}
                    >
                      <span style={{ color: star <= rating ? '#f59e0b' : 'var(--border)' }}>★</span>
                    </button>
                  ))}
                </div>
                <button style={s.removeBtn} onClick={() => removeMovie(movie.movie_id)}>✕</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Öneri Al */}
      <div style={s.section}>
        <button style={s.recBtn} onClick={getRecommendations}>
          {loading ? 'Hesaplanıyor...' : '✨ Öneri Al'}
        </button>
        {watched.length === 0 && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
            Önce film eklemeniz gerekiyor.
          </p>
        )}
      </div>

      {/* Öneriler */}
      {recommendations.length > 0 && (
        <div style={s.section}>
          <div style={s.label}>Sizin İçin Öneriler</div>
          <div style={s.grid}>
            {recommendations.map(m => <MovieCard key={m.movie_id} movie={m} showScore />)}
          </div>
        </div>
      )}
    </div>
  )
}