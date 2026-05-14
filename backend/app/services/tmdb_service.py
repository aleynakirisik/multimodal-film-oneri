import time
import requests
from typing import Optional
from app.core.config import TMDB_API_KEY, TMDB_BASE_URL, TMDB_IMAGE_BASE_URL


def search_movie_tmdb(title: str, year: Optional[int] = None) -> Optional[dict]:
    """
    Film adı ile TMDB'de arama yapar, ilk sonucu döndürür.
    """
    if not TMDB_API_KEY:
        return None

    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US",
        "page": 1
    }
    if year:
        params["year"] = year

    try:
        resp = requests.get(f"{TMDB_BASE_URL}/search/movie", params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except Exception as e:
        print(f"TMDB arama hatası ({title}): {e}")
        return None


def get_movie_details(tmdb_id: int) -> Optional[dict]:
    """
    TMDB film ID'si ile detaylı bilgi çeker (özet dahil).
    """
    if not TMDB_API_KEY:
        return None

    try:
        resp = requests.get(
            f"{TMDB_BASE_URL}/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"TMDB detay hatası (id={tmdb_id}): {e}")
        return None


def fetch_poster_image(poster_path: str) -> Optional[bytes]:
    """
    TMDB poster yolundan görüntü binary verisini indirir.
    """
    if not poster_path:
        return None
    url = f"{TMDB_IMAGE_BASE_URL}{poster_path}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"Poster indirme hatası: {e}")
        return None


def get_poster_url(poster_path: str) -> Optional[str]:
    """Poster URL'ini döndürür (frontend için)."""
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE_URL}{poster_path}"


def enrich_movies_with_tmdb(movies_df, delay: float = 0.25) -> list:
    """
    Film listesi için TMDB'den poster ve özet bilgisi çeker.
    delay: API rate limit için bekleme süresi (saniye)
    
    Döndürür: [{"movie_id", "tmdb_id", "poster_path", "overview", "poster_url"}, ...]
    """
    enriched = []
    total = len(movies_df)

    for i, row in movies_df.iterrows():
        print(f"TMDB: [{i+1}/{total}] {row['title']}")

        result = search_movie_tmdb(row["title"], row.get("release_year"))

        if result:
            tmdb_id = result.get("id")
            poster_path = result.get("poster_path", "")
            overview = result.get("overview", "")

            
            if len(overview) < 20 and tmdb_id:
                details = get_movie_details(tmdb_id)
                if details:
                    overview = details.get("overview", overview)

            enriched.append({
                "movie_id": row["movie_id"],
                "tmdb_id": tmdb_id,
                "poster_path": poster_path,
                "poster_url": get_poster_url(poster_path),
                "overview": overview or f"A film titled '{row['title']}'."
            })
        else:
            enriched.append({
                "movie_id": row["movie_id"],
                "tmdb_id": None,
                "poster_path": None,
                "poster_url": None,
                "overview": f"A film titled '{row['title']}'."
            })

        time.sleep(delay)

    return enriched