import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── TMDB ──────────────────────────────────────────────────────
TMDB_API_KEY        = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL       = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"

# ── Supabase ──────────────────────────────────────────────────
# .env'e ekleyin:
#   SUPABASE_URL=https://xxxx.supabase.co
#   SUPABASE_KEY=eyJ...  (anon/public key)
#   SUPABASE_DB_URL=postgresql://postgres.xxxx:SIFRE@aws-...supabase.com:6543/postgres
SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY    = os.getenv("SUPABASE_KEY", "")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

# ── Pinecone ──────────────────────────────────────────────────
# .env'e ekleyin:
#   PINECONE_API_KEY=pcsk_...
#   PINECONE_INDEX=film-oneri
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX   = os.getenv("PINECONE_INDEX", "film-oneri")

# ── Lokal feature dosyaları (fallback) ────────────────────────
FEATURES_PATH = Path(os.getenv("FEATURES_PATH", str(BASE_DIR / "data" / "features")))
FEATURES_PATH.mkdir(parents=True, exist_ok=True)

COMBINED_FEATURES_FILE = FEATURES_PATH / "combined_features.npy"
MOVIE_IDS_FILE         = FEATURES_PATH / "movie_ids.npy"
MOVIES_META_FILE       = FEATURES_PATH / "movies_meta.pkl"

VISUAL_WEIGHT = 0.2
TEXT_WEIGHT   = 0.8
