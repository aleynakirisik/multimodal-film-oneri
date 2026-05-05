import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "d77629dc33fc59febdd280f89da58160")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"

MOVIELENS_DATA_PATH = Path(os.getenv("MOVIELENS_DATA_PATH", str(BASE_DIR / "data" / "ml-latest-small")))
FEATURES_PATH = Path(os.getenv("FEATURES_PATH", str(BASE_DIR / "data" / "features")))
FEATURES_PATH.mkdir(parents=True, exist_ok=True)

MAX_MOVIES = int(os.getenv("MAX_MOVIES", 500))

# Özellik vektörü dosya yolları
VISUAL_FEATURES_FILE = FEATURES_PATH / "visual_features.npy"
TEXT_FEATURES_FILE = FEATURES_PATH / "text_features.npy"
COMBINED_FEATURES_FILE = FEATURES_PATH / "combined_features.npy"
MOVIE_IDS_FILE = FEATURES_PATH / "movie_ids.npy"
MOVIES_META_FILE = FEATURES_PATH / "movies_meta.pkl"

# Model ağırlıkları
VISUAL_WEIGHT = 0.2   # Poster özelliklerinin ağırlığı
TEXT_WEIGHT = 0.8     # Metin özelliklerinin ağırlığı