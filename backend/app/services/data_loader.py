import pandas as pd
import numpy as np
from pathlib import Path
import sqlite3
import psycopg2 # PostgreSQL için eklendi
from psycopg2.extras import execute_values
from app.core.config import MOVIELENS_DATA_PATH, MAX_MOVIES

# --- PostgreSQL Bağlantı Ayarları ---
POSTGRES_CONFIG = {
    "dbname": "film_oneri_db",
    "user": "postgres",
    "password": "123",
    "host": "localhost",
    "port": "5432"
}

GENRE_COLUMNS = [
    "unknown", "Action", "Adventure", "Animation", "Children",
    "Comedy", "Crime", "Documentary", "Drama", "Fantasy",
    "Film-Noir", "Horror", "Musical", "Mystery", "Romance",
    "Sci-Fi", "Thriller", "War", "Western"
]

def load_movies() -> pd.DataFrame:
    item_file = MOVIELENS_DATA_PATH / "u.item"
    if not item_file.exists():
        raise FileNotFoundError(f"MovieLens verisi bulunamadı: {item_file}")

    columns = ["movie_id", "title", "release_date", "video_release_date", "imdb_url"] + GENRE_COLUMNS
    df = pd.read_csv(item_file, sep="|", encoding="latin-1", names=columns)
    
    df["release_year"] = df["release_date"].str.extract(r"(\d{4})").astype("Int64")
    df["genres"] = df[GENRE_COLUMNS].apply(lambda row: ",".join([g for g, v in zip(GENRE_COLUMNS, row) if v == 1]), axis=1)
    
    df = df.dropna(subset=["title"])
    df = df[df["movie_id"] > 0].head(MAX_MOVIES)
    return df[["movie_id", "title", "release_year", "genres", "imdb_url"]].fillna(0)

def load_ratings() -> pd.DataFrame:
    data_file = MOVIELENS_DATA_PATH / "u.data"
    df = pd.read_csv(data_file, sep="\t", names=["user_id", "movie_id", "rating", "timestamp"])
    return df

def save_to_postgresql(movies_df, ratings_df):
    """Verileri PostgreSQL'e aktarır."""
    print("🐘 PostgreSQL'e aktarılıyor...")
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()

        # Film tablosu oluştur
        cur.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_id INTEGER PRIMARY KEY,
                title TEXT,
                release_year INTEGER,
                genres TEXT,
                imdb_url TEXT
            );
        """)

        # Filmleri yükle (Toplu insert)
        movie_values = [tuple(x) for x in movies_df.values]
        execute_values(cur, "INSERT INTO movies (movie_id, title, release_year, genres, imdb_url) VALUES %s ON CONFLICT (movie_id) DO NOTHING", movie_values)

        conn.commit()
        print("✅ PostgreSQL: Filmler hazır.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL Hatası: {e}")

def save_to_sqlite():
    print("⏳ Veriler yükleniyor ve Hibrit Yapı kuruluyor...")
    
    movies_df = load_movies()
    ratings_df = load_ratings()
    
    # 1. PostgreSQL'e Kaydet (Ana Veri Deposu)
    save_to_postgresql(movies_df, ratings_df)
    
    # 2. SQLite'a Kaydet (Hızlı Erişim/Vektör Deposu)
    db_path = MOVIELENS_DATA_PATH / "multimodal_recommendation.db"
    conn = sqlite3.connect(db_path)
    try:
        movies_df.to_sql('movies', conn, if_exists='replace', index=False)
        ratings_df.to_sql('ratings', conn, if_exists='replace', index=False)
        print(f"✅ SQLite: Başarılı! {db_path}")
    finally:
        conn.close()

if __name__ == "__main__":
    save_to_sqlite()