import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const tabs = [
  { label: '🎬 Filmler', path: '/' },
  { label: '👤 Profilim', path: '/profile' },
]

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

return (
    <nav style={{
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: 56,
      position: 'sticky', top: 0, zIndex: 100
    }}>
      <div style={{ fontWeight: 700, fontSize: 18, color: 'var(--accent)' }}>
        🎥 FilmÖneri
      </div>
      <div style={{ display: 'flex', gap: 4 }}>
        {tabs.map(t => (
          <button
            key={t.path}
            onClick={() => navigate(t.path)}
            style={{
              background: pathname === t.path ? 'var(--accent)' : 'transparent',
              color: pathname === t.path ? '#fff' : 'var(--text-muted)',
              border: 'none', borderRadius: 8, padding: '6px 16px',
              cursor: 'pointer', fontSize: 14, fontWeight: 500,
              transition: 'all 0.15s'
            }}
          >
            {t.label}
          </button>
        ))}

        {/* ŞEMA DEĞİŞİKLİĞİNE GÖRE GÜNCELLENEN ROL KONTROLÜ */}
        {user?.role === 'admin' && (
          <button
            onClick={() => navigate('/admin-portal')}
            style={{
              background: pathname === '/admin-portal' ? 'var(--accent)' : 'transparent',
              color: pathname === '/admin-portal' ? '#fff' : 'var(--accent)',
              border: '1px solid var(--accent)',
              borderRadius: 8, padding: '6px 16px',
              cursor: 'pointer', fontSize: 14, fontWeight: 600,
              marginLeft: 8, transition: 'all 0.15s'
            }}
          >
            ⚙️ Admin Paneli
          </button>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          {user?.username} ({user?.role === 'admin' ? 'Yönetici' : 'Kullanıcı'})
        </span>
        <button
          onClick={onLogout}
          style={{
            background: 'none', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text-muted)',
            padding: '5px 14px', cursor: 'pointer', fontSize: 13
          }}
        >
          Çıkış
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        
        <button
          onClick={onLogout}
          style={{
            background: 'none', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text-muted)',
            padding: '5px 14px', cursor: 'pointer', fontSize: 13
          }}
        >
          Çıkış
        </button>
      </div>
    </nav>
  )
}