"""
VGG16 modeli ile film posterlerinden görsel özellik vektörü çıkarır.
ImageNet ağırlıkları kullanılır, son sınıflandırma katmanı kaldırılır.
Çıktı: 4096 boyutlu özellik vektörü
"""
import io
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from typing import Optional


# GPU varsa kullan, yoksa CPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ImageNet için standart normalizasyon
TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


class VGG16FeatureExtractor:
    """
    VGG16'nın classifier katmanının son FC'sinden önce
    4096 boyutlu özellik vektörü çıkarır.
    """

    def __init__(self):
        print(f"VGG16 yükleniyor... (device: {DEVICE})")
        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)

        # Son sınıflandırma katmanını kaldır (features + avgpool + classifier[:-1])
        self.features = vgg.features
        self.avgpool = vgg.avgpool
        self.classifier = nn.Sequential(*list(vgg.classifier.children())[:-1])

        self.model = nn.Sequential(
            self.features,
        )
        self._vgg = vgg

        self._vgg.eval()
        self._vgg.to(DEVICE)

        # Hook ile 4096-d vektörü yakala
        self._feature_vector = None
        self._register_hook()

        print("VGG16 hazır.")

    def _register_hook(self):
        """classifier[5] = ReLU(FC2) → 4096 boyutlu çıktı"""
        def hook_fn(module, input, output):
            self._feature_vector = output.detach().cpu().numpy()

        # classifier: Linear(25088,4096) -> ReLU -> Dropout -> Linear(4096,4096) -> ReLU[idx=4] -> Dropout -> Linear(4096,1000)
        # idx 4 = ikinci ReLU, 4096 boyutlu
        self._vgg.classifier[4].register_forward_hook(hook_fn)

    def extract(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Görüntü binary verisinden 4096 boyutlu vektör çıkarır.
        Hata durumunda None döner.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                self._vgg(tensor)

            vec = self._feature_vector[0]
            # L2 normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.astype(np.float32)

        except Exception as e:
            print(f"Görsel özellik çıkarma hatası: {e}")
            return None

    def extract_from_path(self, image_path: str) -> Optional[np.ndarray]:
        """Dosya yolundan özellik çıkarır."""
        with open(image_path, "rb") as f:
            return self.extract(f.read())

    def get_zero_vector(self) -> np.ndarray:
        """Poster bulunamayan filmler için sıfır vektör."""
        return np.zeros(4096, dtype=np.float32)


# Singleton - bir kez yükle
_extractor_instance = None


def get_visual_extractor() -> VGG16FeatureExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = VGG16FeatureExtractor()
    return _extractor_instance