"""
RecommendationEngine
  - Film metadata  →  Supabase (PostgreSQL)
  - Vektör sorgusu →  Pinecone
  - Metin encode   →  Sentence-BERT (all-MiniLM-L6-v2)
"""

import numpy as np
import pandas as pd
import requests
import time
from typing import List, Optional

from app.core.config import (
    SUPABASE_DB_URL,
    PINECONE_API_KEY,
    PINECONE_INDEX,
    TEXT_WEIGHT,
    TMDB_API_KEY
)

def _get_db_conn():
    import psycopg2
    return psycopg2.connect(SUPABASE_DB_URL)

def _fetch_movies_from_supabase() -> pd.DataFrame:
    """movies tablosundaki tüm filmleri çeker."""
    conn = _get_db_conn()
    try:
        # Puan ve yıl sütunlarını da çekiyoruz
        df = pd.read_sql(
            "SELECT id AS movie_id, title, overview, poster_path, genres, release_year, avg_rating, vote_count FROM movies;",
            conn
        )
    finally:
        conn.close()
    return df

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
    """Pinecone match + Supabase verisini birleştirir."""
    movie_id = int(match["id"])
    score    = float(match.get("score", 0.0))
    
    row = meta_df[meta_df["movie_id"] == movie_id]
    if row.empty: return None
    res = row.iloc[0]

    return {
        "movie_id":        movie_id,
        "title":           res["title"],
        "release_year":    int(res["release_year"]) if res["release_year"] else None,
        "genres":          [g.strip() for g in str(res["genres"]).split(",")] if res["genres"] else [],
        "poster_url":      f"https://image.tmdb.org/t/p/w342{res['poster_path']}" if res["poster_path"] else None,
        "avg_rating":      res["avg_rating"],
        "overview":        (res["overview"] or "")[:300],
        "similarity_score": score,
    }

class RecommendationEngine:
    def __init__(self):
        self.is_ready = False
        self.meta_df  = pd.DataFrame() 
        # Modeli bir kez yükle
        from sentence_transformers import SentenceTransformer
        self.sbert = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

    def load(self):
        """Metadata yükler ve Pinecone kontrol eder."""
        print("⏳ Supabase'den film metadata yükleniyor...")
        self.meta_df = _fetch_movies_from_supabase()
        print(f"✅ {len(self.meta_df)} film yüklendi (Supabase)")
        self.is_ready = True

    def recommend_by_movie(self, movie_id: int, top_n: int = 10) -> List[dict]:
        index = _get_pinecone_index()
        fetch_result = index.fetch(ids=[str(movie_id)])
        vectors = fetch_result.get("vectors", {})
        if str(movie_id) not in vectors:
            return []
        query_vector = np.array(vectors[str(movie_id)]["values"], dtype=np.float32)
        matches = _pinecone_query(query_vector, top_k=top_n, exclude_ids=[str(movie_id)])
        return [r for m in matches if (r := _build_result(m, self.meta_df))]

    def recommend_by_user_history(self, liked_movie_ids: List[int], ratings: Optional[List[float]] = None, top_n: int = 10) -> List[dict]:
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
        if not vectors: return []
        profile = np.sum(np.array(vectors) * np.array(weights).reshape(-1, 1), axis=0)
        profile /= (np.linalg.norm(profile) + 1e-10)
        matches = _pinecone_query(profile, top_k=top_n, exclude_ids=[str(mid) for mid in liked_movie_ids])
        return [r for m in matches if (r := _build_result(m, self.meta_df))]

    def get_movie_by_id(self, movie_id: int) -> Optional[dict]:
        row = _fetch_movie_by_id_supabase(movie_id)
        if not row: return None
        return {
            "movie_id":     movie_id,
            "title":        row["title"],
            "release_year": row["release_year"],
            "genres":       [g.strip() for g in str(row["genres"]).split(",")] if row["genres"] else [],
            "poster_url":   f"https://image.tmdb.org/t/p/w342{row['poster_path']}" if row['poster_path'] else None,
            "avg_rating":   row["avg_rating"],
            "vote_count":   row["vote_count"],
            "overview":     (row["overview"] or "")[:300],
        }

    def get_all_movies(self) -> List[dict]:
        if not self.is_ready or self.meta_df.empty: return []
        result = []
        for _, r in self.meta_df.iterrows():
            result.append({
                "movie_id":     int(r["movie_id"]),
                "title":        str(r["title"]),
                "release_year": int(r["release_year"]) if r["release_year"] else None,
                "genres":       [g.strip() for g in str(r["genres"]).split(",")] if r["genres"] else [],
                "poster_url":   f"https://image.tmdb.org/t/p/w342{r['poster_path']}" if r['poster_path'] else None,
                "avg_rating":   r["avg_rating"],
            })
        return result

    def process_new_movie_logic(self, title: str, year: int):
        import requests
        from app.core.config import TMDB_API_KEY

        """Admin panelinden yeni film ekleme hattı."""
        print(f"🚀 {title} ({year}) işleniyor...")
        print(f"1. TMDB Araması Başladı...")
        # 1. TMDB Arama 
        print(f"1. TMDB Araması Başladı... (Aranan: {title}, Yıl: {year})")
        
        try:
            # TMDB Araması
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}&year={year}"
            search_response = requests.get(search_url, timeout=10) # Zaman aşımı ekledik
            search_res = search_response.json()
            
            if not search_res.get('results'):
                print("❌ Hata: Film TMDB'de bulunamadı!")
                raise Exception("Film TMDB'de bulunamadı!")
            
            movie_id = search_res['results'][0]['id']
            print(f"2. TMDB Verisi Alındı: ID {movie_id}") # Burayı görmemiz lazım!
            
            # Detayları Çek
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
            res = requests.get(detail_url, timeout=10).json()
            
        except Exception as e:
            print(f"❌ TMDB İsteği Sırasında Hata: {str(e)}")
            raise e
        
        # 2. Metin Vektörü ve Normalizasyon
        genres_str = ", ".join([g['name'] for g in res.get('genres', [])])
        text_content = f"{res['title']}. Genres: {genres_str}. Overview: {res['overview']}"
        
        # SBERT zaten normalize edebiliyor, bunu kullanalım
        text_vec = self.sbert.encode([text_content], normalize_embeddings=True)[0]
        
        # 3. Hibrit Vektör Oluşturma ve L2 Normalizasyon
        # Pinecone 4480 beklediği için yapıyı koruyoruz
        visual_part = np.zeros(4096, dtype=np.float32)
        text_part = (text_vec * 0.8).astype(np.float32)
        
        combined_vec = np.concatenate([visual_part, text_part])
        
        # KRİTİK ADIM: Vektörü normalize ediyoruz (L2 Norm)
        norm = np.linalg.norm(combined_vec)
        if norm > 0:
            combined_vec = combined_vec / norm
        
        final_vec = combined_vec.astype(np.float32).tolist()
        print("3. Vektörleme Tamamlandı, Pinecone'a gönderiliyor...")

        # 4. Pinecone'a Gönder (Hata almamak için liste formatında)
        index = _get_pinecone_index()
        index.upsert(vectors=[{
            "id": str(movie_id),
            "values": final_vec,
            "metadata": {
                "title": str(res['title']), 
                "genre": str(genres_str)[:100] # Uzunluğu kısıtla
            }
        }])
        print("4. Pinecone Başarılı, Supabase'e yazılıyor...")
        
        # 4. Supabase Kayıt (Aynı kalıyor)
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO movies (id, title, overview, poster_path, genres, release_year, avg_rating, vote_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET 
                avg_rating=EXCLUDED.avg_rating, vote_count=EXCLUDED.vote_count,
                poster_path=EXCLUDED.poster_path, genres=EXCLUDED.genres
        """, (movie_id, res['title'], res['overview'], res['poster_path'], 
              genres_str, year, res['vote_average'], res['vote_count']))
        conn.commit()
        conn.close()
        print("5. Her şey tamam!")

        # Hafızayı tazele ve basit cevap dön
        self.load()
        return {"status": "success", "title": res.get('title')}

_engine_instance = None

def get_engine() -> RecommendationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
        _engine_instance.load()
    return _engine_instance