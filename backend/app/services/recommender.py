"""
Multimodal Film Öneri Motoru

Görsel (VGG16) + Metin (Sentence-BERT) vektörlerini birleştirerek
kosinüs benzerliği ile öneri üretir.

Mimari (rapordan):
  combined_vector = [visual_weight * visual_vec | text_weight * text_vec]
  similarity = cosine(user_profile_vec, movie_vec)
"""
import numpy as np
import pickle
import pandas as pd
from pathlib import Path
from typing import List, Optional
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import (
    VISUAL_FEATURES_FILE, TEXT_FEATURES_FILE,
    COMBINED_FEATURES_FILE, MOVIE_IDS_FILE, MOVIES_META_FILE,
    VISUAL_WEIGHT, TEXT_WEIGHT
)


class RecommendationEngine:
    """
    Yüklenen özellik vektörlerinden öneri üretir.
    build_index.py çalıştırıldıktan sonra kullanılabilir.
    """

    def __init__(self):
        self.combined_features: Optional[np.ndarray] = None
        self.movie_ids: Optional[np.ndarray] = None
        self.movies_meta: Optional[pd.DataFrame] = None
        self.is_ready = False

    def load(self) -> bool:
        """
        Daha önce hesaplanmış özellik vektörlerini diskten yükler.
        """
        try:
            if not COMBINED_FEATURES_FILE.exists():
                print("Özellik dosyaları bulunamadı. Önce build_index.py çalıştırın.")
                return False

            self.combined_features = np.load(COMBINED_FEATURES_FILE)
            self.movie_ids = np.load(MOVIE_IDS_FILE)

            with open(MOVIES_META_FILE, "rb") as f:
                self.movies_meta = pickle.load(f)

            self.is_ready = True
            print(f"Öneri motoru hazır. {len(self.movie_ids)} film yüklendi.")
            return True

        except Exception as e:
            print(f"Yükleme hatası: {e}")
            return False

    def _get_movie_vector(self, movie_id: int) -> Optional[np.ndarray]:
        """Verilen film ID'si için birleşik vektörü döndürür."""
        idx = np.where(self.movie_ids == movie_id)[0]
        if len(idx) == 0:
            return None
        return self.combined_features[idx[0]]

    def recommend_by_movie(
        self,
        movie_id: int,
        top_n: int = 10,
        exclude_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Belirli bir filme benzer filmleri önerir (içerik tabanlı).
        Soğuk başlangıç için uygundur.
        """
        if not self.is_ready:
            return []

        query_vec = self._get_movie_vector(movie_id)
        if query_vec is None:
            return []

        return self._rank_by_vector(query_vec, top_n, exclude_ids=[movie_id] + (exclude_ids or []))

    def recommend_by_user_history(
        self,
        liked_movie_ids: List[int],
        top_n: int = 10,
        ratings: Optional[List[float]] = None
    ) -> List[dict]:
        """
        Kullanıcının beğendiği filmlerden profil vektörü oluşturarak öneri üretir.
        
        liked_movie_ids: Kullanıcının izlediği/beğendiği film ID'leri
        ratings: Her film için puan (1-5). Varsa ağırlıklı ortalama kullanılır.
        """
        if not self.is_ready or not liked_movie_ids:
            return []

        vectors = []
        weights = []

        for i, mid in enumerate(liked_movie_ids):
            vec = self._get_movie_vector(mid)
            if vec is not None:
                vectors.append(vec)
                w = ratings[i] if ratings and i < len(ratings) else 1.0
                # Puan normalize: 1-5 → 0.2-1.0
                weights.append(max(0.2, w / 5.0))

        if not vectors:
            return []

        # Ağırlıklı kullanıcı profil vektörü
        vectors = np.array(vectors)
        weights = np.array(weights).reshape(-1, 1)
        user_vec = np.sum(vectors * weights, axis=0)
        norm = np.linalg.norm(user_vec)
        if norm > 0:
            user_vec = user_vec / norm

        return self._rank_by_vector(user_vec, top_n, exclude_ids=liked_movie_ids)

    def recommend_by_text_query(
        self,
        query_text: str,
        top_n: int = 10
    ) -> List[dict]:
        """
        Serbest metin sorgusu ile öneri üretir.
        Örn: "action movies with heroes" → benzer filmler
        """
        if not self.is_ready:
            return []

        from app.services.text_extractor import get_text_extractor
        extractor = get_text_extractor()

        # Yalnızca metin vektörü çıkar, sıfır görsel vektörle birleştir
        text_vec = extractor.extract(overview=query_text, genres=[], title="")
        visual_zero = np.zeros(4096, dtype=np.float32)

        query_vec = np.concatenate([
            VISUAL_WEIGHT * visual_zero,
            TEXT_WEIGHT * text_vec
        ])
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        return self._rank_by_vector(query_vec, top_n)

    def _rank_by_vector(
        self,
        query_vec: np.ndarray,
        top_n: int,
        exclude_ids: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Tüm filmler ile kosinüs benzerliği hesaplar, en yakın top_n'i döndürür.
        """
        query_vec = query_vec.reshape(1, -1)
        similarities = cosine_similarity(query_vec, self.combined_features)[0]

        # Dışlanacak filmleri -1 yap
        if exclude_ids:
            for mid in exclude_ids:
                idx = np.where(self.movie_ids == mid)[0]
                if len(idx) > 0:
                    similarities[idx[0]] = -1.0

        top_indices = np.argsort(similarities)[::-1][:top_n]

        results = []
        for idx in top_indices:
            mid = int(self.movie_ids[idx])
            score = float(similarities[idx])
            if score < 0:
                continue

            meta = self._get_meta(mid)
            results.append({
                "movie_id": mid,
                "similarity_score": round(score, 4),
                **meta
            })

        return results

    def _get_meta(self, movie_id: int) -> dict:
        """Film meta verisini döndürür."""
        if self.movies_meta is None:
            return {}
        row = self.movies_meta[self.movies_meta["movie_id"] == movie_id]
        if row.empty:
            return {}
        r = row.iloc[0]
        return {
            "title": str(r.get("title", "")),
            "release_year": int(r.get("release_year", 0)) if pd.notna(r.get("release_year")) else None,
            "genres": list(r.get("genres", [])),
            "poster_url": r.get("poster_url") if pd.notna(r.get("poster_url", None)) else None,
            "overview": str(r.get("overview", ""))[:300],
            "avg_rating": float(r.get("avg_rating", 0)) if pd.notna(r.get("avg_rating", None)) else None,
            "vote_count": int(r.get("vote_count", 0)) if pd.notna(r.get("vote_count", None)) else None,
        }

    def get_all_movies(self) -> List[dict]:
        """Tüm filmlerin listesini döndürür (arama için)."""
        if not self.is_ready or self.movies_meta is None:
            return []
        result = []
        for _, r in self.movies_meta.iterrows():
            result.append({
                "movie_id": int(r["movie_id"]),
                "title": str(r.get("title", "")),
                "release_year": int(r.get("release_year", 0)) if pd.notna(r.get("release_year", None)) else None,
                "genres": list(r.get("genres", [])),
                "poster_url": r.get("poster_url") if pd.notna(r.get("poster_url", None)) else None,
                "avg_rating": float(r.get("avg_rating", 0)) if pd.notna(r.get("avg_rating", None)) else None,
            })
        return result


# Singleton
_engine_instance = None


def get_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
        _engine_instance.load()
    return _engine_instance