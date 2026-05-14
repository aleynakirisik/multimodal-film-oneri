import React, { useState, useEffect } from 'react'
import { Routes, Route, useNavigate , Navigate} from 'react-router-dom'
import Navbar from './components/Navbar'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ProfilePage from './pages/ProfilePage'

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="/profile" element={user ? <ProfilePage user={user} /> : <LoginPage onLogin={handleLogin} />} />
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/admin-portal" element={user?.role === 'admin' ? <AdminPage /> : <Navigate to="/" />} />
        <Route path="/register" element={<RegisterPage onLogin={handleLogin} />} />
      </Routes>
    </>
  )
}