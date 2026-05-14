"""
Film ve Öneri API Endpoint'leri
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from app.services.recommender import get_engine

router = APIRouter()


# ─── Request / Response Modelleri ────────────────────────────

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


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    # Kayıt sırasında seçilen 3 film — rating YOK, sadece tercih sinyali
    initial_movie_ids: List[int]


class LoginRequest(BaseModel):
    username: str
    password: str


class RatingRequest(BaseModel):
    user_id: str
    movie_id: int
    rating: float


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def ensure_tables():
    """users ve ratings tablolarını oluşturur."""
    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                movie_id INTEGER NOT NULL,
                -- rating NULL olabilir: kayıt sırasındaki "tercih" kayıtları
                -- yıldız göstermez ama profil vektörüne katkı sağlar
                rating FLOAT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, movie_id)
            );
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()


# Uygulama başlarken tabloları oluştur
try:
    ensure_tables()
except Exception as e:
    print(f"Tablo oluşturma hatası: {e}")


@router.post("/auth/check-availability")
def check_availability(req: dict):
    username = req.get("username")
    email = req.get("email")
    
    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        # Kullanıcı adı kontrolü
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            raise HTTPException(409, "Bu kullanıcı adı zaten alınmış.")
            
        # Email kontrolü
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            raise HTTPException(409, "Bu e-posta adresi zaten kullanımda.")
            
        return {"status": "available"}
    finally:
        cur.close()
        conn.close()
        
# ─── Auth Endpoint'leri ───────────────────────────────────────

@router.post("/auth/register")
def register(req: RegisterRequest):
    """
    Yeni kullanıcı kaydı.
    initial_movie_ids: Kayıt ekranında seçilen 3 film.
    Bu filmler rating=NULL olarak kaydedilir — kullanıcı arayüzde
    yıldız görmez ama profil vektörü oluşturmak için kullanılır.
    """
    if len(req.username) < 3:
        raise HTTPException(400, "Kullanıcı adı en az 3 karakter olmalı.")
    if len(req.password) < 6:
        raise HTTPException(400, "Şifre en az 6 karakter olmalı.")
    if len(req.initial_movie_ids) < 3:
        raise HTTPException(400, "Kayıt için tam olarak 3 film seçmelisiniz.")
    if "@" not in req.email:
        raise HTTPException(400, "Geçerli bir e-posta adresi giriniz.")

    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
            (user_id, req.username, req.email, hash_password(req.password))
        )

        # 3 filmi rating=NULL ile kaydet (cold start)
        for movie_id in req.initial_movie_ids:
            cur.execute("""
                INSERT INTO ratings (user_id, movie_id, rating)
                VALUES (%s, %s, NULL)
                ON CONFLICT (user_id, movie_id) DO NOTHING
            """, (user_id, movie_id))

        conn.commit()
    except Exception as e:
        conn.rollback()
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            raise HTTPException(409, "Bu kullanıcı adı veya e-posta zaten alınmış.")
        raise HTTPException(500, f"Kayıt sırasında hata: {err}")
    finally:
        cur.close()
        conn.close()

    # Pinecone'a profil vektörü yaz
    engine = get_engine()
    engine.update_user_profile(user_id)

    return {"user_id": user_id, "username": req.username}


@router.post("/auth/login")
def login(req: LoginRequest):
    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, username, role FROM users WHERE username = %s AND password_hash = %s",
            (req.username, hash_password(req.password))
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(401, "Hatalı giriş.")
        return {"user_id": row[0], "username": row[1], "role": row[2]} # Rolü ekledik
    finally:
        cur.close()
        conn.close()

@router.post("/ratings")
def add_rating(req: RatingRequest):
    """
    Kullanıcı bir filme gerçek puan verir (1-5).
    - ratings tablosuna kaydedilir / güncellenir
    - movies tablosundaki avg_rating ve vote_count yeniden hesaplanır
      (sadece NULL olmayan puanlar sayılır)
    - Kullanıcının Pinecone profil vektörü güncellenir
    """
    if not (1 <= req.rating <= 5):
        raise HTTPException(400, "Puan 1-5 arasında olmalı.")

    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        # puanı kaydet veya güncelle
        cur.execute("""
            INSERT INTO ratings (user_id, movie_id, rating)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, movie_id) DO UPDATE SET rating = EXCLUDED.rating
        """, (req.user_id, req.movie_id, req.rating))

        # avg_rating ve vote_count'u sadece gerçek puanlardan (rating IS NOT NULL) hesapla
        cur.execute("""
            UPDATE movies SET
                avg_rating = (
                    SELECT ROUND(AVG(rating)::numeric, 2)
                    FROM ratings
                    WHERE movie_id = %s AND rating IS NOT NULL
                ),
                vote_count = (
                    SELECT COUNT(*)
                    FROM ratings
                    WHERE movie_id = %s AND rating IS NOT NULL
                )
            WHERE id = %s
        """, (req.movie_id, req.movie_id, req.movie_id))

        conn.commit()

        cur.execute(
            "SELECT avg_rating, vote_count FROM movies WHERE id = %s",
            (req.movie_id,)
        )
        row = cur.fetchone()
        result = {
            "success":    True,
            "movie_id":   req.movie_id,
            "avg_rating": float(row[0]) if row and row[0] else None,
            "vote_count": int(row[1])   if row and row[1] else None,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Puan kaydedilemedi: {e}")
    finally:
        cur.close()
        conn.close()

    # kullanıcı profilini güncelle 
    get_engine().update_user_profile(req.user_id)

    return result


@router.get("/ratings/{user_id}")
def get_user_ratings(user_id: str):
    """
    Kullanıcının gerçek puan verdiği filmleri döndürür.
    rating=NULL olan kayıt sırasındaki tercihler dahil edilmez.
    """
    conn = _get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT r.movie_id, r.rating, m.title, m.poster_path, m.genres
            FROM ratings r
            JOIN movies m ON m.id = r.movie_id
            WHERE r.user_id = %s AND r.rating IS NOT NULL
            ORDER BY r.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [
            {
                "movie_id":  row[0],
                "rating":    row[1],
                "title":     row[2],
                "poster_url": f"https://image.tmdb.org/t/p/w342{row[3]}" if row[3] else None,
                "genres":    [g.strip() for g in row[4].split("|")] if row[4] else [],
            }
            for row in rows
        ]
    finally:
        cur.close()
        conn.close()


# ─── Endpoint'ler ─────────────────────────────────────────────

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


@router.post("/recommend/search", response_model=List[RecommendationResponse])
def recommend_by_text(request: TextQueryRequest):
    """
    Serbest metin sorgusu ile öneri üretir.
    Örn: "space adventure with heroes" → benzer filmler
    """
    engine = get_engine()
    if not engine.is_ready:
        raise HTTPException(503, "Öneri motoru hazır değil.")

    if not request.query.strip():
        raise HTTPException(400, "Sorgu metni boş olamaz.")

    results = engine.recommend_by_text_query(
        query_text=request.query,
        top_n=request.top_n
    )

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