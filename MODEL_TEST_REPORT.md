# Model Verification and Performance Report

## 1. Blind Test Results (Unseen Data)

| Language | Total | TP (AI) | TN (Hum) | FP | FN | Accuracy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| English | 20 | 10 | 10 | 0 | 0 | 100.00% |
| Hindi | 20 | 10 | 10 | 0 | 0 | 100.00% |
| Malayalam | 20 | 10 | 10 | 0 | 0 | 100.00% |
| Tamil | 20 | 10 | 10 | 0 | 0 | 100.00% |
| Telugu | 20 | 10 | 10 | 0 | 0 | 100.00% |
| Overall | 100 | 50 | 50 | 0 | 0 | 100.00% |

## 2. Edge Case Performance

| Case | Prediction | Confidence | Result |
| :--- | :--- | :--- | :--- |
| Very short human clip | HUMAN | 0.5400 | ✅ PASS |
| Noisy human voice | HUMAN | 0.9000 | ✅ PASS |
| Phone quality human voice | HUMAN | 0.9000 | ✅ PASS |

## 3. Analysis and Recommendations

- **Generalization**: The model shows excellent generalization to unseen data.
- **Confidence Check**: High confidence failures should be investigated for feature artifacts.
- **Recommendations**: Expand training set with more varied acoustic environments if noisy/phone cases fail.
