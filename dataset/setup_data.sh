#!/usr/bin/env bash
set -e
python dataset/data_setup.py --base-dir data
python dataset/download_open_datasets.py --base-dir data --max-per-language 100
python dataset/generate_ai_samples.py --base-dir data --corpus-dir dataset/corpus --samples-per-language 50 --target-sample-rate 22050
python dataset/validate_dataset.py --base-dir data --report-csv dataset/validation_report.csv --splits-csv dataset/split_recommendations.csv
# python dataset/normalize_human_samples.py --input-dir recordings/ --language tamil --speaker-id speaker001 --base-dir data
