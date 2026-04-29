import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getMovies = (search = '', genre = '') =>
  api.get('/movies', { params: { search, genre, limit: 100 } }).then(r => r.data)

export const getMovie = (id) =>
  api.get(`/movies/${id}`).then(r => r.data)

export const getSimilar = (movieId, topN = 10) =>
  api.get(`/recommend/similar/${movieId}`, { params: { top_n: topN } }).then(r => r.data)

export const getUserRecommendations = (likedIds, ratings = null, topN = 10) =>
  api.post('/recommend/user', {
    liked_movie_ids: likedIds,
    ratings,
    top_n: topN
  }).then(r => r.data)

export const searchByText = (query, topN = 10) =>
  api.post('/recommend/search', { query, top_n: topN }).then(r => r.data)

export const getStatus = () =>
  api.get('/status').then(r => r.data)