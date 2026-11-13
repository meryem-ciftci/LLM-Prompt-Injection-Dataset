# Automated Statistical Analysis

- Result SHA-256: `84019c9127e84b7a068007a1414c826c6571d986e5aed020d8fb2e63631272b3`
- Dataset SHA-256: `6d99b4f8cd82ba190d1cb1bd57b8aa75a65a17abd7511c0fd1f17a780a12478f`
- Bootstrap iterations: `2000`

## Model summary

| Model | N | Accuracy | F1 | Recall | FPR | MCC | Brier | ECE | p50 ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gemma3:4b | 200 | 0.425 | 0.582 | 1.000 | 0.958 | 0.131 | 0.512 | 0.523 | 3451 | 4193 |
| llama3.1:8b | 200 | 0.725 | 0.567 | 0.450 | 0.092 | 0.414 | 0.227 | 0.174 | 3498 | 4165 |
| llama3:latest | 200 | 0.605 | 0.168 | 0.100 | 0.058 | 0.077 | 0.350 | 0.344 | 3212 | 3971 |
| mistral:latest | 200 | 0.750 | 0.734 | 0.863 | 0.325 | 0.528 | 0.223 | 0.202 | 3758 | 4509 |
| qwen3:8b | 200 | 0.905 | 0.894 | 1.000 | 0.158 | 0.825 | 0.091 | 0.067 | 3828 | 4592 |

## Pairwise exact McNemar tests (Holm-adjusted)

| Model A | Model B | A right/B wrong | A wrong/B right | p | Holm p |
|---|---|---:|---:|---:|---:|
| gemma3:4b | llama3.1:8b | 44 | 104 | 0.000001 | 0.000006 |
| gemma3:4b | llama3:latest | 72 | 108 | 0.008901 | 0.017801 |
| gemma3:4b | mistral:latest | 11 | 76 | 0.000000 | 0.000000 |
| gemma3:4b | qwen3:8b | 0 | 96 | 0.000000 | 0.000000 |
| llama3.1:8b | llama3:latest | 34 | 10 | 0.000388 | 0.001553 |
| llama3.1:8b | mistral:latest | 32 | 37 | 0.630456 | 0.630456 |
| llama3.1:8b | qwen3:8b | 16 | 52 | 0.000014 | 0.000070 |
| llama3:latest | mistral:latest | 33 | 62 | 0.003833 | 0.011499 |
| llama3:latest | qwen3:8b | 12 | 72 | 0.000000 | 0.000000 |
| mistral:latest | qwen3:8b | 6 | 37 | 0.000002 | 0.000010 |
