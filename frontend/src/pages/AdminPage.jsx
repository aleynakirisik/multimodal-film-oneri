import React, { useState } from 'react'
import { addMovieRequest } from '../api'

export default function AdminPage() {
  const [data, setData] = useState({ title: '', year: '' })
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  // src/pages/AdminPage.jsx içindeki handleSubmit kısmını şöyle güncelle:
    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Backend'in 8000 portunda olduğundan emin oluyoruz
            const response = await fetch("http://localhost:8000/api/add-movie", { 
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: data.title,
                    year: parseInt(data.year)
                })
            });

            if (!response.ok) throw new Error("Backend hatası!");

            const res = await response.json();
            setStatus({ type: 'success', msg: res.message || 'Film başarıyla eklendi!' });
            setData({ title: '', year: '' });
        } catch (err) {
            console.error("Hata Detayı:", err); // Tarayıcı konsoluna hatayı yazar
            setStatus({ type: 'error', msg: 'Film eklenemedi! Arka planda AI hatası oluştu.' });
        } finally {
            setLoading(false);
        }
    }

  const s = {
    container: { maxWidth: 500, margin: '80px auto', padding: 32, background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--border)' },
    input: { width: '100%', padding: 12, marginBottom: 16, background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, color: '#fff' },
    btn: { width: '100%', padding: 12, background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }
  }

  return (
    <div style={s.container}>
      <h1 style={{ marginBottom: 24 }}> Admin Panel</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 20 }}>Eklemek istediğiniz filmin adını ve vizyon tarihini doldurunuz.</p>
      
      <form onSubmit={handleSubmit}>
        <input style={s.input} placeholder="Film Adı" value={data.title} onChange={e => setData({...data, title: e.target.value})} required />
        <input style={s.input} type="text" placeholder="Yıl" value={data.year} onChange={e => setData({...data, year: e.target.value})} required />
        <button style={s.btn} disabled={loading}>{loading ? 'Gönderiliyor...' : 'Filmi Ekle'}</button>
      </form>

      {status && (
        <div style={{ marginTop: 20, padding: 12, borderRadius: 8, background: status.type === 'success' ? '#065f46' : '#991b1b', fontSize: 13 }}>
          {status.msg}
        </div>
      )}
    </div>
  )
}