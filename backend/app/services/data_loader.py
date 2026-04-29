"""
MovieLens 100K veri setini okur.
Veri seti: https://grouplens.org/datasets/movielens/100k/
u.item dosyasından film bilgilerini, u.data dosyasından puanları okur.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from app.core.config import MOVIELENS_DATA_PATH, MAX_MOVIES


# MovieLens tür kategorileri (u.item dosyasındaki sırayla)
GENRE_COLUMNS = [
    "unknown", "Action", "Adventure", "Animation", "Children",
    "Comedy", "Crime", "Documentary", "Drama", "Fantasy",
    "Film-Noir", "Horror", "Musical", "Mystery", "Romance",
    "Sci-Fi", "Thriller", "War", "Western"
]


def load_movies() -> pd.DataFrame:
    """
    u.item dosyasından film bilgilerini yükler.
    Döndürür: movie_id, title, release_year, genres (liste), imdb_url
    """
    item_file = MOVIELENS_DATA_PATH / "u.item"
    if not item_file.exists():
        raise FileNotFoundError(
            f"MovieLens verisi bulunamadı: {item_file}\n"
            "Lütfen https://grouplens.org/datasets/movielens/100k/ adresinden indirin."
        )

    columns = ["movie_id", "title", "release_date", "video_release_date",
               "imdb_url"] + GENRE_COLUMNS

    df = pd.read_csv(
        item_file,
        sep="|",
        encoding="latin-1",
        names=columns,
        usecols=["movie_id", "title", "release_date", "imdb_url"] + GENRE_COLUMNS
    )

    # Yıl çıkar
    df["release_year"] = df["release_date"].str.extract(r"(\d{4})").astype("Int64")

    # Türleri liste olarak birleştir
    df["genres"] = df[GENRE_COLUMNS].apply(
        lambda row: [g for g, v in zip(GENRE_COLUMNS, row) if v == 1], axis=1
    )

    # Temizlik
    df = df.dropna(subset=["title"])
    df = df[df["movie_id"] > 0]
    df = df.head(MAX_MOVIES)

    return df[["movie_id", "title", "release_year", "genres", "imdb_url"]].reset_index(drop=True)


def load_ratings() -> pd.DataFrame:
    """
    u.data dosyasından kullanıcı-film puanlarını yükler.
    Döndürür: user_id, movie_id, rating, timestamp
    """
    data_file = MOVIELENS_DATA_PATH / "u.data"
    if not data_file.exists():
        raise FileNotFoundError(f"u.data bulunamadı: {data_file}")

    df = pd.read_csv(
        data_file,
        sep="\t",
        names=["user_id", "movie_id", "rating", "timestamp"]
    )
    return df


def build_user_movie_matrix(ratings: pd.DataFrame, movie_ids: list) -> pd.DataFrame:
    """
    Kullanıcı-film puanlama matrisini oluşturur (satır=user, sütun=movie).
    Eksik değerler NaN olarak bırakılır.
    """
    filtered = ratings[ratings["movie_id"].isin(movie_ids)]
    matrix = filtered.pivot_table(
        index="user_id",
        columns="movie_id",
        values="rating",
        aggfunc="mean"
    )
    return matrix


def get_movie_stats(ratings: pd.DataFrame, movie_ids: list) -> pd.DataFrame:
    """
    Her film için ortalama puan ve oy sayısını döndürür.
    """
    filtered = ratings[ratings["movie_id"].isin(movie_ids)]
    stats = filtered.groupby("movie_id")["rating"].agg(
        avg_rating="mean",
        vote_count="count"
    ).round(2)
    return stats