import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ─── Basit In-Memory Cache ─────────────────────────────────────
// Sayfa geçişlerinde aynı veriler tekrar tekrar çekilmesini önler.
// TTL süresi dolunca ya da kullanıcı puan verince cache temizlenir.

const cache = new Map()

function cacheGet(key) {
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() > entry.expiresAt) {
    cache.delete(key)
    return null
  }
  return entry.data
}

function cacheSet(key, data, ttlMs = 5 * 60 * 1000) { // varsayılan: 5 dakika
  cache.set(key, { data, expiresAt: Date.now() + ttlMs })
}

export function invalidateCache(pattern) {
  // Belirli bir prefix ile başlayan tüm cache'leri temizler
  // Örnek: invalidateCache('personalized:') → kullanıcı önerilerini sıfırlar
  for (const key of cache.keys()) {
    if (key.startsWith(pattern)) cache.delete(key)
  }
}

// ─── Film Listesi ──────────────────────────────────────────────
// Arama olmadan çekilen tam liste 10 dakika cache'lenir.
// Arama yapılınca cache atlanır (anlık sonuç beklenir).

export const getMovies = async (search = '', genre = '', limit = 100) => {
  const cacheKey = `movies:${search}:${genre}:${limit}`

  // Arama yoksa cache'e bak
  if (!search && !genre) {
    const cached = cacheGet(cacheKey)
    if (cached) return cached
  }

  const response = await api.get('/movies', {
    params: {
      search: search || undefined,
      genre:  genre  || undefined,
      limit
    }
  })

  const data = response.data

  if (!search && !genre) {
    cacheSet(cacheKey, data, 10 * 60 * 1000) // 10 dakika
  }

  return data
}

export const getMovie = async (id) => {
  const cacheKey = `movie:${id}`
  const cached = cacheGet(cacheKey)
  if (cached) return cached

  const data = await api.get(`/movies/${id}`).then(r => r.data)
  cacheSet(cacheKey, data, 10 * 60 * 1000)
  return data
}

// ─── Benzer Film Önerileri ─────────────────────────────────────
// Bir film için benzer filmler nadiren değişir — 10 dk cache.

export const getSimilar = async (movieId, topN = 10) => {
  const cacheKey = `similar:${movieId}:${topN}`
  const cached = cacheGet(cacheKey)
  if (cached) return cached

  const data = await api.get(`/recommend/similar/${movieId}`, { params: { top_n: topN } }).then(r => r.data)
  cacheSet(cacheKey, data, 10 * 60 * 1000)
  return data
}

// ─── Kişisel Öneriler ──────────────────────────────────────────
// Kullanıcı puan verdikçe güncellenir — 3 dk cache.
// addRating çağrısı bu cache'i otomatik sıfırlar.

export const getPersonalized = async (userId, topN = 10) => {
  const cacheKey = `personalized:${userId}:${topN}`
  const cached = cacheGet(cacheKey)
  if (cached) return cached

  const data = await api.get(`/recommend/personalized/${userId}`, { params: { top_n: topN } }).then(r => r.data)
  cacheSet(cacheKey, data, 3 * 60 * 1000) // 3 dakika
  return data
}

// ─── Auth ──────────────────────────────────────────────────────

export const checkAvailability = (username, email) =>
  api.post('/auth/check-availability', { username, email }).then(r => r.data)

export const register = async (username, email, password, initial_movie_ids) => {
  const res = await api.post('/auth/register', { username, email, password, initial_movie_ids })
  return res.data
}

export const login = (username, password) =>
  api.post('/auth/login', { username, password }).then(r => r.data)

// ─── Puanlama ─────────────────────────────────────────────────
// Puan verince kişisel öneriler ve kullanıcı puanları cache'i sıfırlanır.

export const addRating = async (user_id, movie_id, rating) => {
  const data = await api.post('/ratings', { user_id, movie_id, rating }).then(r => r.data)

  // Bu kullanıcının öneri ve puan cache'ini temizle
  invalidateCache(`personalized:${user_id}`)
  invalidateCache(`userratings:${user_id}`)

  return data
}

// ─── Kullanıcı Puanları ───────────────────────────────────────

export const getUserRatings = async (user_id) => {
  const cacheKey = `userratings:${user_id}`
  const cached = cacheGet(cacheKey)
  if (cached) return cached

  const data = await api.get(`/ratings/${user_id}`).then(r => r.data)
  cacheSet(cacheKey, data, 3 * 60 * 1000)
  return data
}

// ─── Diğerleri ────────────────────────────────────────────────

export const getStatus = () =>
  api.get('/status').then(r => r.data)

export const addMovieRequest = (title, year) =>
  api.post('/add-movie', { title, year }).then(r => r.data)
