import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { register, getMovies, checkAvailability } from '../api'


const FALLBACK_IMG = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='300' style='background:%231a1a24'><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%237c6af7' font-size='14' font-family='sans-serif'>Poster Yok</text></svg>`

export default function RegisterPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(1)
  const [movies, setMovies] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    if (step === 2) {
      //film listesini çekiyoruz
      getMovies(searchTerm, '', 100)
        .then(data => setMovies(Array.isArray(data) ? data : []))
        .catch(console.error)
    }
  }, [step, searchTerm])

  const handleNextStep = async () => {
    if (!username || !email || !password) { setError('Lütfen tüm alanları doldurun.'); return }
    if (!email.includes('@')) { setError('Geçerli bir e-posta girin.'); return }
    if (password.length < 6) { setError('Şifre en az 6 karakter olmalı.'); return }

    try {
        setError('');
        await checkAvailability(username, email);
        setStep(2); //her şey okeyse film seçimine geç
    } catch (err) {
        setError(err.response?.data?.detail || 'Bu bilgiler zaten kullanımda.');
    }
  }

  const handleSubmit = async () => {
    if (selectedIds.length < 3) { setError('Lütfen en az 3 film seçin.'); return }
    setLoading(true)
    try {
      //backende kayıt isteği gönder
      const user = await register(username, email, password, selectedIds)
      sessionStorage.setItem('user', JSON.stringify(user))
      onLogin(user) 
      navigate('/') 
    } catch (e) {
      setError(e.response?.data?.detail || 'Kayıt başarısız oldu. Kullanıcı adı veya email alınmış olabilir.')
    } finally { setLoading(false) }
  }

  const toggleSelect = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(mid => mid !== id) : [...prev, id])
  }

  const s = {
    page: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f0f12' },
    card: { background: '#1a1a1e', border: '1px solid #2d2d35', borderRadius: 16, padding: '40px', width: step === 1 ? 380 : 700, transition: '0.3s' },
    title: { fontSize: 24, fontWeight: 700, marginBottom: 8, color: '#fff', textAlign: 'center' },
    subtitle: { fontSize: 14, color: '#9494a3', marginBottom: 25, textAlign: 'center' },
    input: { width: '100%', padding: '12px 16px', marginBottom: 15, background: '#25252b', border: '1px solid #33333b', borderRadius: 10, color: '#fff', outline: 'none' },
    btn: { width: '100%', padding: '12px', background: '#7c4dff', border: 'none', borderRadius: 10, color: '#fff', fontWeight: 600, cursor: 'pointer' },
    //poster grid yapısı
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 15, maxHeight: 400, overflowY: 'auto', padding: 10, background: '#25252b', borderRadius: 12, marginBottom: 20 },
    movieItem: (isSelected) => ({
      cursor: 'pointer', textAlign: 'center', transition: '0.2s', position: 'relative',
      border: isSelected ? '3px solid #7c4dff' : '1px solid transparent',
      borderRadius: 10, overflow: 'hidden', background: '#1a1a1e'
    }),
    poster: { width: '100%', aspectRatio: '2/3', objectFit: 'cover', display: 'block' },
    movieTitle: { fontSize: 11, color: '#fff', padding: '6px 4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
    link: { color: '#7c4dff', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, marginLeft: 5 }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.title}>{step === 1 ? 'Aramıza Katıl' : 'Zevkini Belirle'}</div>
        <div style={s.subtitle}>{step === 1 ? 'Hesabını oluştur' : 'Sana uygun öneriler için 3 film seç'}</div>

        {step === 1 ? (
          <>
            <input style={s.input} placeholder="Kullanıcı Adı" value={username} onChange={e => setUsername(e.target.value)} />
            <input style={s.input} placeholder="E-posta" value={email} onChange={e => setEmail(e.target.value)} />
            <input style={s.input} type="password" placeholder="Şifre (Min 6)" value={password} onChange={e => setPassword(e.target.value)} />
            {error && <div style={{ color: '#ff5252', fontSize: 13, marginBottom: 15, textAlign: 'center' }}>{error}</div>}
            <button style={s.btn} onClick={handleNextStep}>Devam Et</button>
            <div style={{ marginTop: 20, textAlign: 'center', color: '#9494a3', fontSize: 14 }}>
              Zaten hesabın var mı? <button style={s.link} onClick={() => navigate('/login')}>Giriş Yap</button>
            </div>
          </>
        ) : (
          <>
            <input style={s.input} placeholder=" Film ara..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
            <div style={s.grid}>
              {movies.map(m => (
                <div key={m.movie_id} style={s.movieItem(selectedIds.includes(m.movie_id))} onClick={() => toggleSelect(m.movie_id)}>
                  <img 
                    src={m.poster_url || FALLBACK_IMG} 
                    alt={m.title} 
                    style={s.poster}
                    onError={e => { e.target.onerror = null; e.target.src = FALLBACK_IMG }}
                  />
                  <div style={s.movieTitle}>{m.title}</div>
                  {selectedIds.includes(m.movie_id) && (
                     <div style={{ position: 'absolute', top: 5, right: 5, background: '#7c4dff', borderRadius: '50%', width: 20, height: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>✓</div>
                  )}
                </div>
              ))}
            </div>
            {error && <div style={{ color: '#ff5252', fontSize: 13, marginBottom: 15 }}>{error}</div>}
            <button style={s.btn} onClick={handleSubmit} disabled={loading}>
              {loading ? 'İşleniyor...' : `Kaydı Tamamla (${selectedIds.length}/3)`}
            </button>
          </>
        )}
      </div>
    </div>
  )
}