import React from 'react'

const FALLBACK = 'https://via.placeholder.com/200x300/1a1a24/7c6af7?text=No+Poster'

function fixTitle(title) {
  if (!title) return title
  return title.replace(/^(.*),\s*(The|A|An)\s*$/i, '$2 $1').trim()
}

const styles = {
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    overflow: 'hidden',
    cursor: 'pointer',
    transition: 'transform 0.2s, border-color 0.2s',
    display: 'flex',
    flexDirection: 'column',
  },
  poster: {
    width: '100%',
    aspectRatio: '2/3',
    objectFit: 'cover',
    background: 'var(--surface2)',
  },
  body: { padding: '12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' },
  title: { fontSize: '14px', fontWeight: 600, lineHeight: 1.3, color: 'var(--text)' },
  meta: { fontSize: '12px', color: 'var(--text-muted)' },
  genres: { display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' },
  genreTag: {
    fontSize: '11px', padding: '2px 8px',
    background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: '20px', color: 'var(--text-muted)'
  },
  score: {
    marginTop: 'auto', paddingTop: '8px',
    fontSize: '12px', color: 'var(--accent)', fontWeight: 600
  },
  rating: { fontSize: '12px', color: '#f59e0b' }
}

export default function MovieCard({ movie, onClick, showScore = false }) {
  const [imgErr, setImgErr] = React.useState(false)

  return (
    <div
      style={styles.card}
      onClick={() => onClick && onClick(movie)}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-4px)'
        e.currentTarget.style.borderColor = 'var(--accent)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      <img
        src={imgErr || !movie.poster_url ? FALLBACK : movie.poster_url}
        alt={fixTitle(movie.title)}
        style={styles.poster}
        onError={() => setImgErr(true)}
      />
      <div style={styles.body}>
        <div style={styles.title}>{fixTitle(movie.title)}</div>
        <div style={styles.meta}>
          {movie.release_year && <span>{movie.release_year}</span>}
          {movie.avg_rating && (
            <span style={{ marginLeft: 8, ...styles.rating }}>
              ★ {movie.avg_rating.toFixed(1)}
              {movie.vote_count && <span style={{ color: 'var(--text-muted)' }}> ({movie.vote_count})</span>}
            </span>
          )}
        </div>
        {movie.genres?.length > 0 && (
          <div style={styles.genres}>
            {movie.genres.slice(0, 3).map(g => (
              <span key={g} style={styles.genreTag}>{g}</span>
            ))}
          </div>
        )}
        {showScore && movie.similarity_score !== undefined && (
          <div style={styles.score}>
            Benzerlik: %{(movie.similarity_score * 100).toFixed(1)}
          </div>
        )}
      </div>
    </div>
  )
}