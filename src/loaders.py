import json
from typing import List, Dict
from src.schema import RawMaliciousPrompt

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
        SQuAD veri setini HuggingFace datasets kullanmadan, doğrudan JSON olarak çeker.
        Bu sayede Windows DLL engelleme (pyarrow) hatalarının önüne geçilir.
        """
        import urllib.request
        import json

        print("SQuAD veri seti doğrudan indiriliyor...")
        url = "https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json"
        
        try:
            # Standart Python kütüphanesiyle web'den json dosyasını çekiyoruz
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
        except Exception as e:
            print(f"Veri indirilirken hata oluştu: {e}")
            return []

        clean_data = []
        
        # SQuAD JSON yapısı içinde gezinip soru ve bağlamları çıkarma[cite: 3]
        for article in data['data']:
            for paragraph in article['paragraphs']:
                context = paragraph['context']
                for qa in paragraph['qas']:
                    if not qa['is_impossible']: # Sadece geçerli cevabı olanları al
                        question = qa['question']
                        answer = qa['answers'][0]['text']
                        
                        clean_data.append({
                            "p": question,
                            "d": context,
                            "a": answer
                        })
                        
                        if len(clean_data) >= sample_size:
                            return clean_data
                            
        return clean_data