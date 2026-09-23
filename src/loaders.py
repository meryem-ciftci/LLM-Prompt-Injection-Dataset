import json
from typing import List, Dict
from schema import RawMaliciousPrompt

class DataLoader:
    @staticmethod
    def load_malicious_prompts(filepath: str) -> List[RawMaliciousPrompt]:
        """
        Zararlı komut havuzunu (JSONL formatında) okur ve Pydantic şemasından geçirir.
        """
        valid_prompts = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            # Tüm dosyayı tek bir string olarak okuyup, jsonl mantığına uyarlıyoruz
            content = f.read()
            # Dosyandaki virgülleri ve süslü parantezleri güvenli bir şekilde ayırmak için
            # (Eğer dosyan tam standart tek satır jsonl değilse diye ufak bir temizlik)
            raw_blocks = content.split('},')
            
            for index, block in enumerate(raw_blocks, 1):
                block = block.strip()
                if not block:
                    continue
                    
                if not block.endswith('}'):
                    block += '}'
                    
                try:
                    data = json.loads(block)
                    # Veriyi şemadan geçirerek doğrula
                    validated_prompt = RawMaliciousPrompt(**data)
                    valid_prompts.append(validated_prompt)
                except ValueError as ve:
                    # Şemadaki model_validator'dan dönen hatalar (örneğin boş sample_00x)
                    print(f"Blok {index} atlandı (Doğrulama): {ve}")
                except Exception as e:
                    print(f"Blok {index} atlandı (Parse Hatası): {e}")
                    
        return valid_prompts

    @staticmethod
    def load_clean_squad_data(sample_size: int = 100) -> List[Dict]:
        """
        SQuAD veri setinden temiz bağlam(d), soru(p) ve cevap(a) üçlülerini çeker.
        Not: Bu metodun çalışması için terminalden 'pip install datasets' yapılmalıdır.
        """
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("HuggingFace datasets kütüphanesi bulunamadı. Lütfen 'pip install datasets' komutunu çalıştırın.")

        print("SQuAD veri seti indiriliyor/yükleniyor...")
        # Makaledeki yaklaşıma uygun olarak SQuAD validation setini kullanıyoruz
        dataset = load_dataset("squad", split="validation")
        
        clean_data = []
        for item in dataset.select(range(sample_size)):
            clean_data.append({
                "p": item["question"],       # Orijinal soru
                "d": item["context"],        # Temiz belge (bağlam)
                "a": item["answers"]["text"][0] if item["answers"]["text"] else "" # Cevap
            })
            
        return clean_data