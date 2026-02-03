# Evaluation Suite

- Install evaluation dependencies:
  - `python -m pip install -r requirements_eval.txt`

- Comprehensive evaluation report:
  - `python evaluation.py --model app/model/model.json --test-dir data --output-dir results`

- English-only training and model write:
  - `python train_english_only.py --base-dir data --language english --output app/model/model.json --val-split 0.2`
  - `python evaluation.py --model app/model/model.json --test-dir data --output-dir results`

- Verify API integration with trained model:
  - `python verify_api.py --model app/model/model.json`

- End-to-end testing on samples:
  - `python test_inference.py --model app/model/model.json --test-dir data --output results/test_results.json`

- Dataset quality report:
  - `python dataset_stats.py --base-dir data --output results/dataset_report.json`

- Performance benchmark:
  - `python benchmark_speed.py --model app/model/model.json --samples 100 --output results/benchmark_results.json`

 - Deployment readiness:
   - `python check_deployment_ready.py --model app/model/model.json --output DEPLOYMENT_READY.md`

Outputs are saved under `results/` with metrics and plots.
