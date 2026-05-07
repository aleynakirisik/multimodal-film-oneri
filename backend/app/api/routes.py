"""
Film ve Öneri API Endpoint'leri
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.services.recommender import get_engine

router = APIRouter()

class MovieResponse(BaseModel):
    movie_id: int
    title: str
    release_year: Optional[int]
    genres: List[str] = []
    poster_url: Optional[str]
    avg_rating: Optional[float]
    vote_count: Optional[int] = None
    overview: Optional[str] = None


class RecommendationResponse(BaseModel):
    movie_id: int
    title: str
    release_year: Optional[int]
    genres: List[str]
    poster_url: Optional[str]
    avg_rating: Optional[float]
    overview: Optional[str]
    similarity_score: float


class UserHistoryRequest(BaseModel):
    liked_movie_ids: List[int]
    ratings: Optional[List[float]] = None
    top_n: int = 10


@router.get("/movies", response_model=List[MovieResponse])
def list_movies(
    search: Optional[str] = Query(None, description="Film adı ile arama"),
    genre: Optional[str] = Query(None, description="Tür filtresi"),
    limit: int = Query(50, le=500)
):
    """Tüm filmleri listele, arama ve filtreleme destekler."""
    engine = get_engine()
    if not engine.is_ready:
        raise HTTPException(503, "Öneri motoru hazır değil. Önce build_index.py çalıştırın.")

    movies = engine.get_all_movies()

    if search:
        search_lower = search.lower()
        movies = [m for m in movies if search_lower in m["title"].lower()]

    if genre:
        genre_lower = genre.lower()
        movies = [m for m in movies if any(genre_lower in g.lower() for g in m.get("genres", []))]

    return movies[:limit]


@router.get("/movies/{movie_id}", response_model=MovieResponse)
def get_movie(movie_id: int):
    """Belirli bir film detayını döndürür."""
    engine = get_engine()
    if not engine.is_ready:
        raise HTTPException(503, "Öneri motoru hazır değil.")

    movie = engine.get_movie_by_id(movie_id)

    if not movie:
        raise HTTPException(404, f"Film bulunamadı: {movie_id}")

    return movie


@router.get("/recommend/similar/{movie_id}", response_model=List[RecommendationResponse])
def recommend_similar(
    movie_id: int,
    top_n: int = Query(10, ge=1, le=50)
):
    """
    Belirli bir filme benzer filmleri önerir.
    İçerik tabanlı - soğuk başlangıç için idealdir.
    """
    engine = get_engine()
    if not engine.is_ready:
        raise HTTPException(503, "Öneri motoru hazır değil.")

    results = engine.recommend_by_movie(movie_id, top_n=top_n)
    if not results:
        raise HTTPException(404, f"Film ID {movie_id} için öneri üretilemedi.")

    return results


@router.post("/recommend/user", response_model=List[RecommendationResponse])
def recommend_for_user(request: UserHistoryRequest):
    """
    Kullanıcının izleme geçmişine göre öneri üretir.
    liked_movie_ids: Beğenilen film ID'leri
    ratings: Her film için puan (opsiyonel, 1-5)
    """
    engine = get_engine()
    if not engine.is_ready:
        raise HTTPException(503, "Öneri motoru hazır değil.")

    if not request.liked_movie_ids:
        raise HTTPException(400, "En az bir film ID'si gereklidir.")

    results = engine.recommend_by_user_history(
        liked_movie_ids=request.liked_movie_ids,
        ratings=request.ratings,
        top_n=request.top_n
    )

    if not results:
        raise HTTPException(404, "Öneri üretilemedi. Film ID'leri geçerli mi?")

    return results



@router.get("/status")
def status():
    """Sistem durumu."""
    engine = get_engine()
    movie_count = len(engine.movie_ids) if engine.is_ready else 0
    return {
        "ready": engine.is_ready,
        "movie_count": movie_count,
        "message": "Sistem hazır." if engine.is_ready else "build_index.py çalıştırılmadı."
    }