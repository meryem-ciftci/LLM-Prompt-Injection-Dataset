# Literatür Haritası v2 — Generator 3 tasarım dayanakları

**Durum:** Taslak · 2026-11-16 · Henüz hiçbir G3 sonucu ölçülmedi.

## Kanıt düzeyleri

- **Uygulandı:** Kod bu commit'te var ve test ediliyor.
- **Tasarlandı:** Şemada veya planda var, kodu yok.
- **Yalnızca literatür:** Gerekçe olarak anılıyor; yöntemi uygulamıyoruz.

> SQuAD bir **temiz görev verisidir** (bağlam, soru ve cevap). Saldırı veri seti değildir. G3'te yalnızca carrier metni ve utility oracle'ı için kullanılması planlanıyor.
>
> PromptLocate'tan esinlenerek **span ground-truth** etiketliyoruz. PromptLocate'ın lokalizasyon algoritmasını **uygulamıyoruz**.

## Özellik → dayanak tablosu

| Özellik | Dosya / fonksiyon | Ne yapar | Neden | Kaynak (bölüm) | Kanıt |
|---|---|---|---|---|---|
| Güven sınırına dayalı etiket | `src/dg2/generator.py` `make_record` | Aynı metni untrusted→injection, trusted→benign olarak etiketler | Etiket anahtar kelimeye değil, yetki kanalına bağlı | Greshake 2023 §3; Yi 2023 BIPIA §2 | Uygulandı (G2.2) |
| Kod noktası span'leri | `generator.py` `validate` | Enjeksiyon konumunu round-trip doğrular | Lokalizasyon değerlendirmesi | Jia PromptLocate (görev tanımı) | Uygulandı (G2.2); algoritma yalnızca literatür |
| Konum / uzunluk / gizleme faktörleri | `generator.py` `transform`, `obfuscate_instruction` | head/middle/tail, 256/1024/3072 kelime, base64/char_split/leetspeak | H3–H4 hipotezleri | Liu 2024 §4; Duarte 2026 taksonomi | Uygulandı (G2.2) |
| Dedektör değerlendirme ve istatistik | `src/dg2/evaluator.py`, `analysis.py` | Ollama sınıflandırması, McNemar/Holm, Wilson, ECE | Tespit metrikleri | Duarte 2026 (metrikler) | Uygulandı; yalnızca EXP-001 keşifsel olarak koşuldu |
| Saldırı amacı enum'u | `src/dg3/taxonomy.py` `ATTACK_GOALS` | 7 amaç kategorisi | Oyuncak hedeflerden gerçek tehdit modeline geçiş | Greshake 2023; Zhan 2024 InjecAgent; Liu 2024 | Tasarlandı |
| Saldırı tekniği enum'u | `taxonomy.py` `ATTACK_TECHNIQUES` | naive … multilingual_switch | Tekniğe göre kırılım analizi | Liu 2024 (5 teknik); Duarte 2026; LLMail-Inject | Tasarlandı |
| Witness/canary oracle | `schemas/generated-record-v3.schema.json` `attack.witness` | Deterministik başarı ölçümü için iz | "Üretilmiş" ile "başarılı" saldırıyı ayırmak | Zverev 2024 SEP; Debenedetti 2024 AgentDojo | Tasarlandı |
| Dörtlü aile (clean / injected / twin / trigger-benign) | `taxonomy.py` `FAMILY_ROLES` | Aynı ailede utility, ASR, FPR ve over-defense ölçümü | Eşli kontrol ve aşırı savunma ölçümü | AgentDojo (utility vs ASR); Li 2024 InjecGuard/NotInject | Tasarlandı |
| Utility görevi | şema `task` | Referans cevap ve kontrol yöntemi | Saldırı altında görev başarısı | Yi 2023 BIPIA; Rajpurkar 2016 SQuAD | Tasarlandı |
| Carrier kaynak kaydı | şema `carrier_source` | Lisans, snapshot hash, kaynak ID | Tekrar üretilebilirlik ve lisans uyumu | Gebru 2021 Datasheets | Tasarlandı |
| Hedef-model ASR koşusu | planlanan `src/dg3/target_eval.py` | utility_clean, utility_under_attack, ASR, MR | Deneysel saldırı başarısı | Liu 2024 (ASR/MR); AgentDojo | Tasarlandı |
| Adaptif saldırı alt kümesi | — | Statik setin sınırını belgelemek | Statik değerlendirme savunmayı abartabilir | Zhan 2025 (Adaptive Attacks) | Yalnızca literatür |
| TR/EN dil etkisi | `experimental_factors.language` | Dil kırılımı | H2 | Yong 2023 | Uygulandı (alan); hipotez test edilmedi |

## Kaynaklar

Künyeler bilgi tabanından yazıldı. **Yayına girmeden önce her birinin DOI veya arXiv kaydıyla tek tek doğrulanması gerekiyor** ("✓" sütunu).

| # | Künye | Bağlantı | ✓ |
|---|---|---|---|
| 1 | Rajpurkar et al. 2016, *SQuAD: 100,000+ Questions for Machine Comprehension of Text*, EMNLP | https://aclanthology.org/D16-1264/ | ☐ |
| 2 | Greshake et al. 2023, *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*, AISec | https://arxiv.org/abs/2302.12173 | ☐ |
| 3 | Liu et al. 2024, *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*, USENIX Security | https://www.usenix.org/conference/usenixsecurity24/presentation/liu-yupei | ☐ |
| 4 | Yi et al. 2023, *Benchmarking and Defending Against Indirect Prompt Injection Attacks on LLMs* (BIPIA) | https://arxiv.org/abs/2312.14197 | ☐ |
| 5 | Zhan et al. 2024, *InjecAgent*, Findings of ACL | https://aclanthology.org/2024.findings-acl.624/ | ☐ |
| 6 | Debenedetti et al. 2024, *AgentDojo*, NeurIPS D&B | https://arxiv.org/abs/2406.13352 | ☐ |
| 7 | Zverev et al. 2024, *Can LLMs Separate Instructions From Data? And What Do We Even Mean By That?* (SEP) | https://arxiv.org/abs/2403.06833 | ☐ |
| 8 | Toyer et al. 2023, *Tensor Trust: Interpretable Prompt Injection Attacks from an Online Game* | https://arxiv.org/abs/2311.01011 | ☐ |
| 9 | Schulhoff et al. 2023, *Ignore This Title and HackAPrompt*, EMNLP | https://arxiv.org/abs/2311.16119 | ☐ |
| 10 | Abdelnabi et al., *LLMail-Inject* | https://huggingface.co/datasets/microsoft/llmail-inject-challenge | ☐ |
| 11 | Li et al. 2024, *InjecGuard: Benchmarking and Mitigating Over-defense in Prompt Injection Guardrail Models* | https://arxiv.org/abs/2410.22770 | ☐ |
| 12 | Zhan et al. 2025, *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents*, Findings of NAACL | https://arxiv.org/abs/2503.00061 | ☐ |
| 13 | Yong et al. 2023, *Low-Resource Languages Jailbreak GPT-4* | https://arxiv.org/abs/2310.02446 | ☐ |
| 14 | Jia et al. 2026, *PromptLocate: Localizing Prompt Injection Attacks*, IEEE S&P | https://doi.org/10.1109/SP63933.2026.00105 | ☐ |
| 15 | Duarte et al. 2026, *A Systematic Review of Prompt Injection Attacks on LLMs*, IEEE Access | https://doi.org/10.1109/ACCESS.2026.3656849 | ☐ |
| 16 | Gebru et al. 2021, *Datasheets for Datasets*, CACM | https://doi.org/10.1145/3458723 | ☐ |
