import numpy as np
import pickle
import pandas as pd
from typing import List, Optional

from app.core.config import (
    COMBINED_FEATURES_FILE,
    MOVIE_IDS_FILE,
    MOVIES_META_FILE,
    TEXT_WEIGHT
)

class RecommendationEngine:

    def __init__(self):
        self.features = None
        self.movie_ids = None
        self.movies_meta = None
        self.is_ready = False
        self.text_model = None  # lazy load

    def load(self):
        self.features = np.load(COMBINED_FEATURES_FILE)
        self.movie_ids = np.load(MOVIE_IDS_FILE)

        with open(MOVIES_META_FILE, "rb") as f:
            self.movies_meta = pickle.load(f)

        # normalize (çok önemli)
        norms = np.linalg.norm(self.features, axis=1, keepdims=True)
        self.features = self.features / (norms + 1e-10)

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
            "movie_id": int(r["movie_id"]),
            "title": str(r.get("title", "")),
            "release_year": int(r.get("release_year", 0)) if pd.notna(r.get("release_year")) else None,
            "genres": list(r.get("genres", [])),
            "poster_url": r.get("poster_url"),
            "avg_rating": float(r.get("avg_rating", 0)) if pd.notna(r.get("avg_rating")) else None,
            "overview": str(r.get("overview", ""))[:300],
            "vote_count": int(r.get("vote_count", 0)) if pd.notna(r.get("vote_count")) else None,
        }
    def get_all_movies(self):
        if not self.is_ready or self.movies_meta is None:
            return []

        result = []

        for _, r in self.movies_meta.iterrows():
            result.append({
                "movie_id": int(r["movie_id"]),
                "title": str(r.get("title", "")),
                "release_year": int(r.get("release_year", 0)) if pd.notna(r.get("release_year")) else None,
                "genres": list(r.get("genres", [])),
                "poster_url": r.get("poster_url"),
                "avg_rating": float(r.get("avg_rating", 0)) if pd.notna(r.get("avg_rating")) else None,
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