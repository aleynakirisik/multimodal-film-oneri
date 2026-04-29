import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
import torch

TEXT_MODEL_NAME = "all-MiniLM-L6-v2"


class SentenceBERTExtractor:

    def __init__(self, model_name: str = TEXT_MODEL_NAME):
        print(f"Sentence-BERT yükleniyor: {model_name}")
        # device_map kullanmadan yükle, CPU'ya zorla
        self.model = SentenceTransformer(model_name, device="cpu")
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"Sentence-BERT hazır. Vektör boyutu: {self.dim}")

    def _build_text(self, overview: str, genres: List[str], title: str = "") -> str:
        genre_str = ", ".join(genres) if genres else "Unknown"
        parts = []
        if title:
            parts.append(f"Movie: {title}.")
        parts.append(f"Genres: {genre_str}.")
        if overview and len(overview.strip()) > 10:
            parts.append(overview.strip())
        return " ".join(parts)

    def extract(self, overview: str, genres: List[str], title: str = "") -> np.ndarray:
        text = self._build_text(overview, genres, title)
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.astype(np.float32)

    def extract_batch(self, records: List[dict], batch_size: int = 32) -> np.ndarray:
        texts = [
            self._build_text(r.get("overview", ""), r.get("genres", []), r.get("title", ""))
            for r in records
        ]
        vectors = self.model.encode(
            texts, batch_size=batch_size,
            normalize_embeddings=True, show_progress_bar=True
        )
        return vectors.astype(np.float32)

    def get_zero_vector(self) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)


_text_extractor_instance = None


def get_text_extractor() -> SentenceBERTExtractor:
    global _text_extractor_instance
    if _text_extractor_instance is None:
        _text_extractor_instance = SentenceBERTExtractor()
    return _text_extractor_instance