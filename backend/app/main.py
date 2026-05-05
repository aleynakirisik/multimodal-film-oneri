"""
Multimodal Film Öneri Sistemi - FastAPI Ana Uygulama
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.services.visual_extractor import get_visual_extractor
from app.services.text_extractor import get_text_extractor

app = FastAPI(
    title="Multimodal Film Öneri Sistemi",
    description="VGG16 + Sentence-BERT tabanlı film öneri API'si",
    version="1.0.0"
)

# React frontend için CORS izni
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Uygulama başladığında ağır modelleri (VGG16 ve BERT) bir kez yükler."""
    print("🚀 Sistem başlatılıyor...")
    
    print("📸 VGG16 (Görsel Modül) yükleniyor...")
    get_visual_extractor() # Görsel model hafızaya
    
    print("🧠 Sentence-BERT (Metin Modülü) yükleniyor...")
    get_text_extractor()   # Metin modeli hafızaya
    
    print("✅ Tüm modeller başarıyla yüklendi ve sistem hazır.")

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Film Öneri API çalışıyor. /docs adresine gidin."}