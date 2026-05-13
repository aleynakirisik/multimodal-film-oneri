import React, { useState, useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'

export default function App() {
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const saved = sessionStorage.getItem('user')
    if (saved) setUser(JSON.parse(saved))
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    sessionStorage.setItem('user', JSON.stringify(userData))
  }

  const handleLogout = () => {
    setUser(null)
    sessionStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <>
      {user && <Navbar user={user} onLogout={handleLogout} />}
      <Routes>
<<<<<<< HEAD
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/" element={user ? <HomePage /> : <LoginPage onLogin={handleLogin} />} />
        <Route path="/profile" element={user ? <ProfilePage user={user} /> : <LoginPage onLogin={handleLogin} />} />
=======
        <Route path="/" element={<HomePage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/admin-portal" element={<AdminPage />} />
>>>>>>> c9397c8ecc1d14103515ded92ccd8659f3668da4
      </Routes>
    </>
  )
}