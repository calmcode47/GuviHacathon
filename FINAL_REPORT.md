# Final Report: English-Only Model

## Overview
- Focus language: English
- Generated at: 1770152677

## Training Metrics
- Accuracy (train/val/test): 1.0, 1.0, 1.0
- ROC-AUC (test): 1.0
- ECE (test): 0.0695071816444397
- Confusion Matrix (test): [[5, 0], [0, 5]]

## API Verification
- Status: ok
- Sample label: HUMAN
- Confidence: 0.7877756037383709
- p_ai: 0.21222439626162914

## Performance Benchmarks
- Mean latency ms: 962.3573166669909
- Median latency ms: 788.2276500004082
- p95 latency ms: 913.5680299998055
- p99 latency ms: 4459.091131999999
- Memory RSS MB mean: 241.15286458333333
- Samples: 30

## Dataset Summary
- Total hours: 0.43330666666666656
- english: human 50, ai 10, avg dur 14.2632s
- hindi: human 0, ai 10, avg dur 13.459200000000001s
- malayalam: human 0, ai 10, avg dur 17.318399999999997s
- tamil: human 0, ai 10, avg dur 21.3216s
- telugu: human 0, ai 10, avg dur 18.312s

## Deployment Readiness
- Model JSON present and valid: PASS
- API verification script: PASS
- Accuracy ≥ 70%: PASS
- ECE ≤ 0.15: PASS
- Latency p95 < 5s: PASS
- API imports without errors: PASS

## Known Limitations
- Model optimized for English only
- Non-English requests have confidence down-weighted
- Human data currently limited to English; others have AI-only

## Recommendations
- Add human samples for Hindi, Malayalam, Tamil, Telugu
- Retrain and re-calibrate multi-language model
- Remove confidence down-weight for languages passing validation
