from src.pipeline import run_pipeline

if __name__ == "__main__":
    print("LLM Prompt Injection Dataset Oluşturucu Başlatılıyor...\n")
    
    run_pipeline(
        raw_jsonl_path="dataset.jsonl",
        output_path="processed_dataset.jsonl",
        num_samples=15  # Şimdilik test amaçlı 15 örnek üretelim
    )