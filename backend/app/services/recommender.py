import numpy as np
import pandas as pd
from typing import List, Optional

from app.core.config import (
    SUPABASE_DB_URL,
    PINECONE_API_KEY,
    PINECONE_INDEX,
)


def _get_db_conn():
    import psycopg2
    return psycopg2.connect(SUPABASE_DB_URL)

def _fetch_movies_from_supabase() -> pd.DataFrame:
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title, overview, poster_path, genres, avg_rating, vote_count FROM movies;")
        rows = cur.fetchall()
        return pd.DataFrame(rows, columns=['movie_id','title','overview','poster_path','genres','avg_rating','vote_count'])
    except Exception as e:
        print(f" SQL Hatası: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def _fetch_movie_by_id_supabase(movie_id: int) -> Optional[dict]:
    """Tek film satırını çeker."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, overview, poster_path FROM movies WHERE id = %s;",
            (movie_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "movie_id":    row[0],
            "title":       row[1],
            "overview":    row[2],
            "poster_path": row[3],
        }
    finally:
        conn.close()


def _get_pinecone_index():
    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)


def _pinecone_query(vector: np.ndarray, top_k: int, exclude_ids: List[str] = None):
    index = _get_pinecone_index()
    
    # sadece filmleri getir
    filter_dict = {"type": {"$ne": "user_profile"}}
    
    result = index.query(
        vector=vector.tolist(),
        top_k=top_k + (len(exclude_ids) if exclude_ids else 0) + 5,
        include_metadata=True,
        filter=filter_dict 
    )
    matches = result.get("matches", [])

    if exclude_ids:
        exclude_set = set(str(i) for i in exclude_ids)
        matches = [m for m in matches if m["id"] not in exclude_set]

    return matches[:top_k]


def _build_result(match: dict, meta_df: pd.DataFrame) -> Optional[dict]:
    """
    Pinecone match + Supabase meta_df satırından birleşik sonuç üretir.
    Pinecone metadata'sında title ve genre var;
    Supabase'de overview ve poster_path var.
    """
    movie_id = int(match["id"])
    score    = float(match.get("score", 0.0))
    pm       = match.get("metadata", {})

    row = meta_df[meta_df["movie_id"] == movie_id]
    overview    = row.iloc[0]["overview"]    if not row.empty else None
    poster_path = row.iloc[0]["poster_path"] if not row.empty else None

    poster_url = (
        f"https://image.tmdb.org/t/p/w342{poster_path}"
        if poster_path else None
    )

    raw_genre = pm.get("genre", "")
    genres = [g.strip() for g in raw_genre.split(",") if g.strip()] if raw_genre else []

    return {
        "movie_id":         movie_id,
        "title":            pm.get("title", ""),
        "release_year":     None,
        "genres":           genres,
        "poster_url":       poster_url,
        "avg_rating":       None,
        "overview":         (overview or "")[:300],
        "similarity_score": score,
    }


class RecommendationEngine:

    def __init__(self):
        self.is_ready = False
        self.meta_df  = pd.DataFrame()

    def load(self):
        print("LOAD FONKSİYONU BAŞLADI") 
        
        print("Supabase'den film metadata yükleniyor...")
        self.meta_df = _fetch_movies_from_supabase()
        print(f" {len(self.meta_df)} film yüklendi (Supabase)")

        print(" Pinecone index kontrol ediliyor...")
        try:
            index = _get_pinecone_index()
            stats = index.describe_index_stats()
            total = stats.get("total_vector_count", 0)
            print(f"✅ Pinecone hazır — {total} vektör")
        except Exception as e:
            print(f" Pinecone Hatası: {e}")

        self.is_ready = True
        print(" MOTOR HAZIR")


    def recommend_by_movie(self, movie_id: int, top_n: int = 10) -> List[dict]:
        """
        Pinecone'da movie_id'ye ait vektörü fetch edip
        en benzer filmleri sorgular.
        """
        index = _get_pinecone_index()

        fetch_result = index.fetch(ids=[str(movie_id)])
        vectors = fetch_result.get("vectors", {})
        if str(movie_id) not in vectors:
            return []

        query_vector = np.array(vectors[str(movie_id)]["values"], dtype=np.float32)
        query_vector /= (np.linalg.norm(query_vector) + 1e-10)

        matches = _pinecone_query(query_vector, top_k=top_n, exclude_ids=[str(movie_id)])
        return [r for m in matches if (r := _build_result(m, self.meta_df))]

    def recommend_by_user_history(
        self,
        liked_movie_ids: List[int],
        ratings: Optional[List[float]] = None,
        top_n: int = 10
    ) -> List[dict]:
        """
        Beğenilen filmlerin Pinecone vektörlerini puan ağırlıklı
        ortalamayla birleştirir ve profil vektörüne en yakın filmleri önerir.
        """
        index = _get_pinecone_index()

        fetch_result = index.fetch(ids=[str(mid) for mid in liked_movie_ids])
        fetched = fetch_result.get("vectors", {})

        vectors, weights = [], []
        for i, mid in enumerate(liked_movie_ids):
            if str(mid) in fetched:
                vec = np.array(fetched[str(mid)]["values"], dtype=np.float32)
                vectors.append(vec)
                w = ratings[i] if ratings and i < len(ratings) else 3.0
                weights.append(max(0.2, w / 5.0))

        if not vectors:
            return []

        vectors = np.array(vectors)
        weights = np.array(weights).reshape(-1, 1)
        profile = np.sum(vectors * weights, axis=0)
        profile /= (np.linalg.norm(profile) + 1e-10)

        matches = _pinecone_query(
            profile, top_k=top_n,
            exclude_ids=[str(mid) for mid in liked_movie_ids]
        )
        return [r for m in matches if (r := _build_result(m, self.meta_df))]


    def update_user_profile(self, user_id: str) -> None:
        """
        Kullanıcının Supabase'deki tüm puanlarını çeker,
        puan ağırlıklı ortalama profil vektörü oluşturur ve
        Pinecone'a 'user:{user_id}' anahtarıyla yazar.

        Kayıtta filmler puansız (rating=None) eklenebilir;
        bu durumda o filmler vektör ortalamasına eşit ağırlıkla (0.6) katılır
        ama avg_rating güncellenmez — kullanıcı arayüzde yıldız görmez.
        """
        conn = _get_db_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT movie_id, rating FROM ratings WHERE user_id = %s;",
                (user_id,)
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            return

        index = _get_pinecone_index()
        movie_ids = [str(r[0]) for r in rows]
        # rating=None olan filmler için nötr ağırlık (0.6)
        raw_ratings = [r[1] for r in rows]

        fetch_result = index.fetch(ids=movie_ids)
        fetched = fetch_result.get("vectors", {})

        vectors, weights = [], []
        for mid, rating in zip(movie_ids, raw_ratings):
            if mid in fetched:
                vec = np.array(fetched[mid]["values"], dtype=np.float32)
                vectors.append(vec)
                if rating is not None:
                    weights.append(max(0.2, float(rating) / 5.0))
                else:
                    weights.append(0.6)  

        if not vectors:
            return

        vectors = np.array(vectors)
        weights = np.array(weights).reshape(-1, 1)
        profile = np.sum(vectors * weights, axis=0)
        profile /= (np.linalg.norm(profile) + 1e-10)

        index.upsert(vectors=[{
            "id":     f"user:{user_id}",
            "values": profile.tolist(),
            "metadata": {"type": "user_profile", "user_id": user_id}
        }])

    def recommend_for_user_id(self, user_id: str, top_n: int = 10) -> Optional[List[dict]]:
        """
        Pinecone'daki kullanıcı profil vektörüyle en yakın filmleri döndürür.
        İzlenen / seçilen filmler sonuçtan çıkarılır.
        Profil yoksa None döner (henüz hiç seçim yapılmamış).
        """
        index = _get_pinecone_index()

        fetch_result = index.fetch(ids=[f"user:{user_id}"])
        vectors = fetch_result.get("vectors", {})

        if f"user:{user_id}" not in vectors:
            return None

        profile = np.array(vectors[f"user:{user_id}"]["values"], dtype=np.float32)

        # daha önce seçilen/izlenen filmleri hariç tut
        conn = _get_db_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT movie_id FROM ratings WHERE user_id = %s;",
                (user_id,)
            )
            watched = [str(r[0]) for r in cur.fetchall()]
        finally:
            conn.close()

        matches = _pinecone_query(profile, top_k=top_n, exclude_ids=watched)
        return [r for m in matches if (r := _build_result(m, self.meta_df))]


    def get_movie_by_id(self, movie_id: int) -> Optional[dict]:
        row = _fetch_movie_by_id_supabase(movie_id)
        if not row:
            return None

        poster_path = row.get("poster_path")
        return {
            "movie_id":     movie_id,
            "title":        row.get("title", ""),
            "release_year": None,
            "genres":       [],
            "poster_url":   f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None,
            "avg_rating":   None,
            "vote_count":   None,
            "overview":     (row.get("overview") or "")[:300],
        }

    def get_all_movies(self) -> List[dict]:
        if not self.is_ready or self.meta_df.empty:
            return []
        result = []
        for _, r in self.meta_df.iterrows():
            poster_path = r.get("poster_path")
            raw_genres = r.get("genres", "")
            genres = [g.strip() for g in str(raw_genres).split("|") if g.strip()] if raw_genres else []
            result.append({
                "movie_id":     int(r["movie_id"]),
                "title":        str(r.get("title", "")),
                "release_year": None,
                "genres":       genres,  
                "poster_url":   f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None,
                "avg_rating":   float(r["avg_rating"]) if r.get("avg_rating") else None,
                "vote_count":   int(r["vote_count"]) if r.get("vote_count") else None,
            })
        return result


_engine_instance = None

def get_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
        _engine_instance.load()
    return _engine_instance