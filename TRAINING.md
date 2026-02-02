# Training Pipeline

- Install training dependencies:
  - `pip install -r requirements_training.txt`

- Prepare cached features and splits:
  - `python dataset/data_loader.py --data-dir data --val-split 0.2 --test-split 0.0 --random-seed 42 --balance`

- Train logistic regression with calibration:
  - `python dataset/train.py --data-dir data --output-dir training_out --val-split 0.2 --random-seed 42`
  - Outputs: `training_out/weights.pkl`, `training_out/report.json`

- Evaluate on a held-out test split:
  - `python dataset/evaluate.py --data-dir data --weights training_out/weights.pkl --random-seed 42 --output-dir evaluation_out`
  - Outputs: `evaluation_out/metrics.json`, PDFs for confusion matrix, ROC, calibration, feature importance

- Update runtime classifier with trained weights:
  - `python dataset/update_classifier.py --weights training_out/weights.pkl --classifier-path app/services/classifier.py`
  - Creates backup: `app/services/classifier.py.bak`

## Notes
- Data directory must contain `data/human/{language}` and `data/ai/{language}` with MP3 files.
- Feature order used across training and runtime matches the dataset loader feature names.
- Reports include accuracy, per-language accuracy, ROC-AUC, confusion matrix.
