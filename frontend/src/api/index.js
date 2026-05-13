import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getMovies = async (search = '', genre = '', limit = 100) => {
  const response = await api.get('/movies', {
    params: {
      search: search || undefined,
      genre:  genre  || undefined,
      limit
    }
  })
  return response.data
}

export const getMovie = (id) =>
  api.get(`/movies/${id}`).then(r => r.data)

export const getSimilar = (movieId, topN = 10) =>
  api.get(`/recommend/similar/${movieId}`, { params: { top_n: topN } }).then(r => r.data)

export const getPersonalized = (userId, topN = 10) =>
  api.get(`/recommend/personalized/${userId}`, { params: { top_n: topN } }).then(r => r.data)

export const register = async (username, password, initial_movie_ids) => {
  const res = await api.post('/auth/register', { username, password, initial_movie_ids })
  return res.data
}

export const login = (username, password) =>
  api.post('/auth/login', { username, password }).then(r => r.data)

export const addRating = (user_id, movie_id, rating) =>
  api.post('/ratings', { user_id, movie_id, rating }).then(r => r.data)

export const getUserRatings = (user_id) =>
  api.get(`/ratings/${user_id}`).then(r => r.data)

export const getStatus = () =>
  api.get('/status').then(r => r.data)

export const addMovieRequest = (title, year) =>
  api.post('/add-movie', { title, year }).then(r => r.data)