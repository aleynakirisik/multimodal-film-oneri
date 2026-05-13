import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register, getMovies } from '../api'

export default function LoginPage({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('');
  const [step, setStep] = useState(1) 
  const [movies, setMovies] = useState([]) 
  const [selectedIds, setSelectedIds] = useState([]) 
  const navigate = useNavigate()
  
  useEffect(() => {
    if (isRegister && step === 2) {
      getMovies(searchTerm, '')
        .then(data => {
          // gelen verinin dizi mi
          if (data && Array.isArray(data)) {
            setMovies(data);
          } else if (data && data.movies) { 
            setMovies(data.movies);
          }
        })
        .catch(err => console.error("Filmler çekilemedi:", err));
    }
  }, [isRegister, step, searchTerm]);

  const handleSubmit = async () => {
  setError('')
  if (!username || !password) { setError('Tüm alanları doldurun.'); return }

  try {
    if (isRegister && step === 1) {
      setStep(2);
      return; 
    }

    setLoading(true)
    if (isRegister) {
      if (selectedIds.length < 3) {
        setError('Lütfen en az 3 film seçin.');
        setLoading(false);
        return;
      }
      const user = await register(username, password, selectedIds)
      sessionStorage.setItem('user', JSON.stringify(user))
      onLogin(user)
      navigate('/')
    } else {
      const user = await login(username, password)
      sessionStorage.setItem('user', JSON.stringify(user))
      onLogin(user)
      navigate('/')
    }
  } catch (e) {
    setError(e.response?.data?.detail || 'Bir hata oluştu.')
  } finally {
    setLoading(false)
  }
}

  const toggleSelect = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(mid => mid !== id))
    } else {
      setSelectedIds([...selectedIds, id])
    }
  }

  const s = {
    page: {
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--bg)'
    },
    card: {
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '40px 36px', width: step === 2 ? 500 : 360,
      transition: 'width 0.3s ease'
    },
    title: { fontSize: 22, fontWeight: 700, marginBottom: 6, color: 'var(--text)' },
    sub: { fontSize: 13, color: 'var(--text-muted)', marginBottom: 28 },
    label: { fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, display: 'block' },
    input: {
      width: '100%', padding: '10px 14px', marginBottom: 16,
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 8, color: 'var(--text)', fontSize: 14, outline: 'none',
      boxSizing: 'border-box'
    },
    btn: {
      width: '100%', padding: '11px', background: 'var(--accent)',
      border: 'none', borderRadius: 8, color: '#fff',
      fontSize: 14, fontWeight: 600, cursor: 'pointer', marginTop: 4
    },
    error: { color: '#ef4444', fontSize: 13, marginBottom: 12 },
    toggle: {
      marginTop: 20, textAlign: 'center', fontSize: 13,
      color: 'var(--text-muted)'
    },
    toggleBtn: {
      background: 'none', border: 'none', color: 'var(--accent)',
      cursor: 'pointer', fontWeight: 600, fontSize: 13
    },
    movieGrid: {
      display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10,
      maxHeight: 300, overflowY: 'auto', marginBottom: 20,
      padding: '10px', background: 'var(--surface2)', borderRadius: 8
    },
    movieItem: (isSelected) => ({
      padding: '8px 12px',
      border: '1px solid',
      borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
      borderRadius: 8,
      cursor: 'pointer',
      fontSize: 12,
      color: 'var(--text)',
      background: isSelected ? 'var(--accent)' : 'transparent',
      textAlign: 'center',
        transition: '0.2s'
    }), 
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.title}>🎥 FilmÖneri</div>
        <div style={s.sub}>
          {isRegister 
            ? (step === 1 ? 'Hesap oluştur' : 'Seni tanımamız için en az 3 film seç') 
            : 'Giriş yap'}
        </div>

        {step === 1 ? (
          <>
            <label style={s.label}>Kullanıcı Adı</label>
            <input
              style={s.input}
              placeholder="kullanici_adi"
              value={username}
              onChange={e => setUsername(e.target.value)}
            />

            <label style={s.label}>Şifre</label>
            <input
              style={s.input}
              type="password"
              placeholder="••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            />
          </>
        ) : (
          <>
            <input
              style={{...s.input, marginBottom: 12, border: '1px solid var(--accent)'}}
              placeholder="🔎 Film ara..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              autoFocus
            />

            <div style={s.movieGrid}>
              {Array.isArray(movies) && movies.length > 0 ? (
                movies.map(m => (
                  <div 
                    key={m.movie_id} 
                    style={s.movieItem(selectedIds.includes(m.movie_id))}
                    onClick={() => toggleSelect(m.movie_id)}
                  >
                    {m.title}
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', gridColumn: '1/-1', padding: '20px' }}>
                  Film yükleniyor veya bulunamadı...
                </div>
              )}
            </div>
          </>
        )}

        {error && <div style={s.error}>{error}</div>}

        <button style={s.btn} onClick={handleSubmit} disabled={loading}>
          {loading 
            ? 'İşleniyor...' 
            : isRegister 
              ? (step === 1 ? 'Devam Et' : `Kaydı Tamamla (${selectedIds.length} Seçildi)`) 
              : 'Giriş Yap'}
        </button>

        {isRegister && step === 2 && (
          <button 
            style={{...s.toggleBtn, width: '100%', marginTop: 10}} 
            onClick={() => setStep(1)}
          >
            ⬅ Bilgileri Düzenle
          </button>
        )}

        <div style={s.toggle}>
          {isRegister ? 'Zaten hesabın var mı?' : 'Hesabın yok mu?'}
          <button style={s.toggleBtn} onClick={() => { 
            setIsRegister(!isRegister); 
            setStep(1); 
            setError(''); 
            setSelectedIds([]);
          }}>
            {isRegister ? ' Giriş Yap' : ' Kayıt Ol'}
          </button>
        </div>
      </div>
    </div>
  )
}