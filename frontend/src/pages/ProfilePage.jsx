import React, { useState, useEffect } from 'react'
import { getMovies, addRating, getUserRatings } from '../api'
import MovieCard from '../components/MovieCard'

const FALLBACK_IMG = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='300' style='background:%231a1a24'><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%237c6af7' font-size='14' font-family='sans-serif'>Poster Yok</text></svg>`

export default function ProfilePage({ user }) {
  const [allMovies, setAllMovies] = useState([])
  const [search, setSearch] = useState('')
  const [watched, setWatched] = useState([])
  const [saving, setSaving] = useState(false)
  const [moviesLoading, setMoviesLoading] = useState(true)

  useEffect(() => {
    // tüm filmleri çek 
    getMovies('', '', 500)
      .then(data => {
        setAllMovies(Array.isArray(data) ? data : [])
        setMoviesLoading(false)
      })
      .catch(() => setMoviesLoading(false))

    if (user) {
      // kullanıcının daha önce puanladığı filmler
      getUserRatings(user.user_id)
        .then(ratings => {
          const watchedList = ratings.map(r => ({
            movie: {
              movie_id: r.movie_id,
              title: r.title,
              poster_url: r.poster_url,
              genres: r.genres
            },
            rating: r.rating
          }))
          setWatched(watchedList)
        })
        .catch(() => {})
    }
  }, [user])

  // arama filtresi 
  const filtered = search.length >= 1
    ? allMovies
        .filter(m => m.title.toLowerCase().includes(search.toLowerCase()))
        .slice(0, 30)
    : []

  const addMovie = async (movie) => {
    if (watched.find(w => w.movie.movie_id === movie.movie_id)) return
    const newItem = { movie, rating: null }
    setWatched(prev => [...prev, newItem])
    setSearch('')
  }

  const updateRating = async (id, rating) => {
    setWatched(prev => prev.map(w => w.movie.movie_id === id ? { ...w, rating } : w))
    if (user) {
      setSaving(true)
      await addRating(user.user_id, id, rating).catch(() => {})
      setSaving(false)
    }
  }

  const removeMovie = (id) => setWatched(prev => prev.filter(w => w.movie.movie_id !== id))

  const s = {
    page: { maxWidth: 1100, margin: '0 auto', padding: '32px 16px' },
    title: { fontSize: 24, fontWeight: 700, marginBottom: 8 },
    sub: { color: 'var(--text-muted)', fontSize: 14, marginBottom: 28 },
    section: { marginBottom: 32 },
    label: {
      fontSize: 13, fontWeight: 600, color: 'var(--text-muted)',
      marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em'
    },
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
      maxHeight: 320, overflowY: 'auto',
      boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
    },
    dropItem: {
      padding: '10px 16px', cursor: 'pointer', fontSize: 13,
      borderBottom: '1px solid var(--border)', transition: 'background 0.1s'
    },
    watchedList: { display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 680 },
    watchedItem: {
      display: 'flex', alignItems: 'center', gap: 12,
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 14px'
    },
    posterThumb: {
      width: 40, height: 56, borderRadius: 4, objectFit: 'cover', flexShrink: 0
    },
    ratingRow: { display: 'flex', gap: 4 },
    starBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, padding: 2 },
    removeBtn: {
      marginLeft: 'auto', background: 'none', border: '1px solid var(--border)',
      borderRadius: 6, color: 'var(--text-muted)', cursor: 'pointer',
      padding: '2px 10px', fontSize: 12
    },
    saving: { fontSize: 12, color: 'var(--text-muted)', marginLeft: 12 },
    emptyMsg: {
      color: 'var(--text-muted)', fontSize: 13, padding: '16px 0',
      fontStyle: 'italic'
    }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>👤 {user?.username || 'Profilim'}</h1>
      <p style={s.sub}>İzlediğiniz filmleri ekleyin ve puanlayın, kişisel öneriler alın.</p>

      {/* film ekle arama */}
      <div style={s.section}>
        <div style={s.label}>İzlediğim Filmleri Ekle</div>
        <div style={s.searchBox}>
          <input
            style={s.input}
            placeholder={moviesLoading ? 'Filmler yükleniyor...' : 'Film adı yazın...'}
            value={search}
            onChange={e => setSearch(e.target.value)}
            disabled={moviesLoading}
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
          {/* film bulunamadı mesajı */}
          {search.length >= 1 && !moviesLoading && filtered.length === 0 && (
            <div style={{ ...s.dropdown, padding: '12px 16px', color: 'var(--text-muted)', fontSize: 13 }}>
              "{search}" için sonuç bulunamadı.
            </div>
          )}
        </div>
        {/* toplam film sayısı */}
        {!moviesLoading && allMovies.length > 0 && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
            {allMovies.length} film aranabilir
          </p>
        )}
      </div>

      {/* izleme Listesi */}
      <div style={s.section}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 10 }}>
          <div style={s.label}>
            Listem {watched.length > 0 ? `(${watched.length} film)` : ''}
          </div>
          {saving && <span style={s.saving}>kaydediliyor...</span>}
        </div>

        {watched.length === 0 ? (
          <p style={s.emptyMsg}>Henüz film eklemediniz. Yukarıdan film arayın ve ekleyin.</p>
        ) : (
          <div style={s.watchedList}>
            {watched.map(({ movie, rating }) => (
              <div key={movie.movie_id} style={s.watchedItem}>
                <img
                  src={movie.poster_url || FALLBACK_IMG}
                  alt={movie.title}
                  style={s.posterThumb}
                  onError={e => { e.target.onerror = null; e.target.src = FALLBACK_IMG }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {movie.title}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {movie.genres?.slice(0, 2).join(', ')}
                  </div>
                  <div style={s.ratingRow}>
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        style={s.starBtn}
                        title={`${star} yıldız`}
                        onClick={() => updateRating(movie.movie_id, star)}
                      >
                        <span style={{ color: star <= (rating || 0) ? '#f59e0b' : 'var(--border)' }}>
                          ★
                        </span>
                      </button>
                    ))}
                    {rating && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', alignSelf: 'center', marginLeft: 4 }}>
                        {rating}/5
                      </span>
                    )}
                  </div>
                </div>
                <button style={s.removeBtn} onClick={() => removeMovie(movie.movie_id)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}