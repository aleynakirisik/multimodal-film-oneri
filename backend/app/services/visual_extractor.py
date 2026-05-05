import io
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from typing import Optional

# 1. Donanım Ayarı: GPU (Ekran Kartı) varsa kullan, yoksa CPU kullan[cite: 2]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 2. Resim Ön İşleme: VGG16 modelinin beklediği standart boyut ve renk ayarları
TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406], # ImageNet standartları
        std=[0.229, 0.224, 0.225]
    )
])

class VGG16FeatureExtractor:
    """
    Tezinizde belirtilen önceden eğitilmiş VGG16 modelini kullanarak 
    posterlerden 4096 boyutlu öznitelik vektörü çıkarır.
    """

    def __init__(self):
        print(f"VGG16 yükleniyor... (Cihaz: {DEVICE})")
        # ImageNet üzerinde eğitilmiş hazır ağırlıkları yükler[cite: 1]
        vgg = models.vgg16(weights=models.VGG16_Weights.IMAGENET1K_V1)

        # Modelin en sonundaki 1000'lik sınıflandırma katmanını devre dışı bırakıyoruz
        self._vgg = vgg
        self._vgg.eval() # Modeli tahmin moduna al
        self._vgg.to(DEVICE)

        self._feature_vector = None
        self._register_hook()
        print("VGG16 hazır.")

    def _register_hook(self):
        """VGG16 içindeki 'fc2' (4096-d) katmanındaki veriyi yakalamak için hook kurar[cite: 2]."""
        def hook_fn(module, input, output):
            self._feature_vector = output.detach().cpu().numpy()

        # 4. indis, sınıflandırmadan önceki son 4096'lık katmanı temsil eder[cite: 2]
        self._vgg.classifier[4].register_forward_hook(hook_fn)

    def extract(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Binary (ham veri) resimden 4096 boyutlu vektör çıkarır[cite: 2]."""
        try:
            # Resmi aç ve modele uygun hale getir
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            tensor = TRANSFORM(img).unsqueeze(0).to(DEVICE)

            # Modeli çalıştır (Gradyan hesaplamaya gerek yok, sadece okuma yapıyoruz)
            with torch.no_grad():
                self._vgg(tensor)

            vec = self._feature_vector[0]
            
            # L2 Normalizasyonu: Vektörü standartlaştırarak benzerlik hesaplamasını iyileştirir[cite: 1]
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.astype(np.float32)

        except Exception as e:
            print(f"Görsel özellik çıkarma hatası: {e}")
            return None

    def get_zero_vector(self) -> np.ndarray:
        """Poster bulunamazsa sistemin çökmemesi için boş vektör döner[cite: 2]."""
        return np.zeros(4096, dtype=np.float32)

# 3. Singleton Yapısı: Modeli hafızaya sadece 1 kere yükler, performansı artırır[cite: 2]
_extractor_instance = None

def get_visual_extractor() -> VGG16FeatureExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = VGG16FeatureExtractor()
    return _extractor_instance