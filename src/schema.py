from pydantic import BaseModel, model_validator
from typing import Optional

# 1. Elinizdeki mevcut dataset.jsonl dosyasını okumak için şema
class RawMaliciousPrompt(BaseModel):
    id: str
    text: str
    label: int
    attack_type: str
    source: str

    @model_validator(mode='before')
    @classmethod
    def standardize_fields(cls, data: dict) -> dict:
        # Boş şablonları (sample_00x) filtrele
        if data.get("id") == "sample_00x" or (not data.get("prompt") and not data.get("text")):
            raise ValueError("Boş veya geçersiz veri tespit edildi, atlanıyor.")
            
        # "prompt" anahtar kelimesini "text" olarak standartlaştır
        if "prompt" in data:
            data["text"] = data.pop("prompt")
            
        # Label değerini integer'a çevir (Örn: "1" -> 1)
        if "label" in data and isinstance(data["label"], str):
            data["label"] = int(data["label"])
            
        return data

# 2. Makaleye uygun olarak üreteceğimiz nihai veri setinin şeması
class InjectionDatasetRow(BaseModel):
    p: str  # Orijinal kullanıcı talimatı (örn: "Aşağıdaki metni özetle")
    d: str  # Temiz belge (örn: SQuAD veya Wikipedia'dan çekilen metin)
    a: str  # Beklenen temiz cevap
    x: str  # Enjekte edilen zararlı talimat (RawMaliciousPrompt'tan gelecek)
    y: str  # Zafiyeti ölçeceğimiz probe / hedef çıktı (örn: www.phishing.com)
    
    separator: str # Kullanılan ayırıcı (örn: "Ignore previous instructions")
    position: str  # Enjeksiyonun yapıldığı konum (head, middle, tail)