import numpy as np
import pickle
import pandas as pd
from typing import List, Optional

from app.core.config import (
    SUPABASE_DB_URL,
    PINECONE_API_KEY,
    PINECONE_INDEX,
    TMDB_API_KEY
)

def _get_db_conn():
    import psycopg2
    return psycopg2.connect(SUPABASE_DB_URL)

def _fetch_movies_from_supabase() -> pd.DataFrame:
    conn = _get_db_conn()
    try:
        # Puan ve yıl sütunlarını da çekiyoruz
        df = pd.read_sql(
            "SELECT id AS movie_id, title, overview, poster_path, genres, release_year, avg_rating, vote_count FROM movies;",
            conn
        )
        return df 
    finally:
        conn.close()

def _fetch_movie_by_id_supabase(movie_id: int) -> Optional[dict]:
    """Tek film satırını detaylı çeker."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, overview, poster_path, genres, release_year, avg_rating, vote_count FROM movies WHERE id = %s;",
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
            "genres":      row[4],
            "release_year": row[5],
            "avg_rating":  row[6],
            "vote_count":  row[7]
        }
    finally:
        conn.close()

def _get_pinecone_index():
    from pinecone import Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    return pc.Index(PINECONE_INDEX)

def _pinecone_query(vector: np.ndarray, top_k: int, exclude_ids: List[str] = None):
    """Pinecone'a vektör sorgusu atar."""
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
    """Pinecone match + Supabase verisini birleştirir."""
    movie_id = int(match["id"])
    score    = float(match.get("score", 0.0))
    
    row = meta_df[meta_df["movie_id"] == movie_id]
    if row.empty: return None
    res = row.iloc[0]

    return {
        "movie_id":        movie_id,
        "title":           res["title"],
        "release_year": int(res["release_year"]) if res["release_year"] and not pd.isna(res["release_year"]) else None,
        "genres":          [g.strip() for g in str(res["genres"]).split(",")] if res["genres"] else [],
        "poster_url":      f"https://image.tmdb.org/t/p/w342{res['poster_path']}" if res["poster_path"] else None,
        "avg_rating":      res["avg_rating"],
        "overview":        (res["overview"] or "")[:300],
        "similarity_score": score,
    }


class RecommendationEngine:

    def __init__(self):
        self.features = None
        self.movie_ids = None
        self.movies_meta = None
        self.is_ready = False
        self.text_model = None  # lazy load

    def load(self):
        """Metadata yükler ve Pinecone kontrol eder."""
        print("⏳ Supabase'den film metadata yükleniyor...")
        self.meta_df = _fetch_movies_from_supabase()
        self.meta_df["release_year"] = self.meta_df["release_year"].where(
        self.meta_df["release_year"].notna(), None
    )
        print(f"✅ {len(self.meta_df)} film yüklendi (Supabase)")
        self.is_ready = True
        print("✅ Recommender hazır")

    def _get_idx(self, movie_id):
        idx = np.where(self.movie_ids == movie_id)[0]
        return idx[0] if len(idx) else None

    def recommend_by_movie(self, movie_id, top_n=10):
        idx = self._get_idx(movie_id)
        if idx is None:
            return []

        query = self.features[idx]

        # 🚀 DOT PRODUCT (FAST)
        scores = self.features @ query

        scores[idx] = -1

        top_idx = np.argsort(scores)[::-1][:top_n]

        return self._format(top_idx, scores)

    def recommend_by_text(self, text, top_n=10):
        if self.text_model is None:
            from sentence_transformers import SentenceTransformer
            self.text_model = SentenceTransformer("all-MiniLM-L6-v2")

        text_vec = self.text_model.encode(text, normalize_embeddings=True)

        total_dim = self.features.shape[1]
        text_dim = len(text_vec)
        visual_dim = total_dim - text_dim

        query = np.zeros(total_dim)
        query[visual_dim:] = TEXT_WEIGHT * text_vec

        query = query / (np.linalg.norm(query) + 1e-10)

        scores = self.features @ query

        top_idx = np.argsort(scores)[::-1][:top_n]

        return self._format(top_idx, scores)
    
    def get_movie_by_id(self, movie_id: int) -> Optional[dict]:
        if self.movies_meta is None:
            return None

        row = self.movies_meta[self.movies_meta["movie_id"] == movie_id]
        if row.empty:
            return None

        r = row.iloc[0]

        return {
            "movie_id":     movie_id,
            "title":        row["title"],
            "release_year": int(row["release_year"]) if row["release_year"] and not pd.isna(row["release_year"]) else None,
            "genres":       [g.strip() for g in str(row["genres"]).split(",")] if row["genres"] else [],
            "poster_url":   f"https://image.tmdb.org/t/p/w342{row['poster_path']}" if row['poster_path'] else None,
            "avg_rating":   row["avg_rating"],
            "vote_count":   row["vote_count"],
            "overview":     (row["overview"] or "")[:300],
        }
    def get_all_movies(self):
        if not self.is_ready or self.movies_meta is None:
            return []

        result = []

        for _, r in self.movies_meta.iterrows():
            result.append({
                "movie_id":     int(r["movie_id"]),
                "title":        str(r["title"]),
                "release_year": int(r["release_year"]) if r["release_year"] and not pd.isna(r["release_year"]) else None,
                "genres":       [g.strip() for g in str(r["genres"]).split(",")] if r["genres"] else [],
                "poster_url":   f"https://image.tmdb.org/t/p/w342{r['poster_path']}" if r['poster_path'] else None,
                "avg_rating":   r["avg_rating"],
            })

        return result

    def _format(self, indices, scores):
        results = []

        for i in indices:
            mid = int(self.movie_ids[i])
            row = self.movies_meta[self.movies_meta["movie_id"] == mid].iloc[0]

            results.append({
                "movie_id": mid,
                "title": row.get("title"),
                "release_year": int(row.get("release_year")) if pd.notna(row.get("release_year")) else None,
                "genres": list(row.get("genres", [])),
                "poster_url": row.get("poster_url"),
                "avg_rating": float(row.get("avg_rating")) if pd.notna(row.get("avg_rating")) else None,
                "overview": row.get("overview"),
                "similarity_score": float(scores[i])
            })

        return results

# Singleton instance
_engine_instance = None

def get_engine():
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
        _engine_instance.load()

    return _engine_instance