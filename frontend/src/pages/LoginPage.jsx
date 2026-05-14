import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async () => {
    setError('')
    if (!username || !password) { setError('Lütfen tüm alanları doldurun.'); return }
    setLoading(true)
    try {
      const user = await login(username, password)
      sessionStorage.setItem('user', JSON.stringify(user))
      onLogin(user)
      navigate('/')
    } catch (e) {
      setError('Kullanıcı adı veya şifre hatalı.')
    } finally {
      setLoading(false)
    }
  }

  const s = {
    page: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f0f12' },
    card: { background: '#1a1a1e', border: '1px solid #2d2d35', borderRadius: 16, padding: '40px', width: 380, boxShadow: '0 20px 40px rgba(0,0,0,0.4)' },
    title: { fontSize: 26, fontWeight: 700, marginBottom: 8, color: '#fff', textAlign: 'center' },
    subtitle: { fontSize: 14, color: '#9494a3', marginBottom: 30, textAlign: 'center' },
    input: { width: '100%', padding: '12px 16px', marginBottom: 16, background: '#25252b', border: '1px solid #33333b', borderRadius: 10, color: '#fff', fontSize: 14, outline: 'none' },
    btn: { width: '100%', padding: '12px', background: '#7c4dff', border: 'none', borderRadius: 10, color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: 16, marginTop: 10, transition: '0.2s' },
    error: { color: '#ff5252', fontSize: 13, marginBottom: 15, textAlign: 'center' },
    toggle: { marginTop: 25, textAlign: 'center', color: '#9494a3', fontSize: 14 },
    link: { color: '#7c4dff', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, marginLeft: 5 }
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.title}>Tekrar Hoş Geldin</div>
        <div style={s.subtitle}>Film dünyasına giriş yapın</div>
        
        <input style={s.input} placeholder="Kullanıcı Adı" value={username} onChange={e => setUsername(e.target.value)} />
        <input style={s.input} type="password" placeholder="Şifre" value={password} onChange={e => setPassword(e.target.value)} />
        
        {error && <div style={s.error}>{error}</div>}
        
        <button style={s.btn} onClick={handleSubmit} disabled={loading}>
          {loading ? 'Giriş Yapılıyor...' : 'Giriş Yap'}
        </button>

        <div style={s.toggle}>
          Hesabın yok mu? 
          <button style={s.link} onClick={() => navigate('/register')}>Kayıt Ol</button>
        </div>
      </div>
    </div>
  )
}