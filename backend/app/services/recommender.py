"""
RecommendationEngine
  - Film metadata  →  Supabase (PostgreSQL)
  - Vektör sorgusu →  Pinecone
  - Metin encode   →  Sentence-BERT (all-MiniLM-L6-v2)
"""

import numpy as np
import pandas as pd
from typing import List, Optional

from app.core.config import (
    SUPABASE_DB_URL,
    PINECONE_API_KEY,
    PINECONE_INDEX,
    TEXT_WEIGHT,
    COMBINED_FEATURES_FILE,
    MOVIE_IDS_FILE,
    MOVIES_META_FILE,
)


def _get_db_conn():
    import psycopg2
    return psycopg2.connect(SUPABASE_DB_URL)


def _fetch_movies_from_supabase() -> pd.DataFrame:
    """movies tablosundaki tüm filmleri çeker."""
    conn = _get_db_conn()
    try:
        df = pd.read_sql(
            "SELECT id AS movie_id, title, overview, poster_path FROM movies;",
            conn
        )
    finally:
        conn.close()
    return df


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
            "movie_id":   row[0],
            "title":      row[1],
            "overview":   row[2],
            "poster_path": row[3],
        }
    finally:
        conn.close()


def _get_pinecone_index():
    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)


def _pinecone_query(vector: np.ndarray, top_k: int, exclude_ids: List[str] = None):
    """
    Pinecone'a vektör sorgusu atar.
    Döndürülen matches listesini döner: [{id, score, metadata}, ...]
    """
    index = _get_pinecone_index()
    result = index.query(
        vector=vector.tolist(),
        top_k=top_k + (len(exclude_ids) if exclude_ids else 0) + 5,
        include_metadata=True
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
        "movie_id":        movie_id,
        "title":           pm.get("title", ""),
        "release_year":    None,   
        "genres":          genres,
        "poster_url":      poster_url,
        "avg_rating":      None,
        "overview":        (overview or "")[:300],
        "similarity_score": score,
    }

class RecommendationEngine:

    def __init__(self):
        self.is_ready    = False
        self.meta_df     = pd.DataFrame() 

    def load(self):
        """Supabase'den metadata çeker, Pinecone bağlantısını test eder."""
        print("⏳ Supabase'den film metadata yükleniyor...")
        self.meta_df = _fetch_movies_from_supabase()
        print(f"✅ {len(self.meta_df)} film yüklendi (Supabase)")

        print("⏳ Pinecone index kontrol ediliyor...")
        index = _get_pinecone_index()
        stats = index.describe_index_stats()
        total = stats.get("total_vector_count", 0)
        print(f"✅ Pinecone hazır — {total} vektör")

        self.is_ready = True

    def recommend_by_movie(self, movie_id: int, top_n: int = 10) -> List[dict]:
        """
        Pinecone'da movie_id'ye ait vektörü fetch edip
        en benzer filmleri sorgular.
        """
        index = _get_pinecone_index()

        # kendi vektörünü al
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
            result.append({
                "movie_id":     int(r["movie_id"]),
                "title":        str(r.get("title", "")),
                "release_year": None,
                "genres":       [],
                "poster_url":   f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None,
                "avg_rating":   None,
            })
        return result


_engine_instance = None

def get_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
        _engine_instance.load()
    return _engine_instance