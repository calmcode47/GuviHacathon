import os
import json
import shutil
from pathlib import Path


def safe_copy(src, dst):
    if os.path.isfile(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    root = Path(".").resolve()
    sub = root / "submission"
    if sub.exists():
        shutil.rmtree(sub)
    (sub / "code").mkdir(parents=True, exist_ok=True)
    (sub / "results").mkdir(parents=True, exist_ok=True)
    (sub / "docs").mkdir(parents=True, exist_ok=True)
    safe_copy(str(root / "FINAL_REPORT.md"), str(sub / "FINAL_REPORT.md"))
    safe_copy(str(root / "results" / "english_model_report.json"), str(sub / "english_model_report.json"))
    safe_copy(str(root / "results" / "training_report.json"), str(sub / "results" / "training_report.json"))
    cm_src = root / "results" / "cm_test.png"
    roc_src = root / "results" / "roc_test.png"
    cal_src = root / "results" / "calibration_test.png"
    imp_src = root / "results" / "feature_importance.png"
    safe_copy(str(cm_src), str(sub / "results" / "confusion_matrix.png"))
    safe_copy(str(roc_src), str(sub / "results" / "roc_curve.png"))
    safe_copy(str(cal_src), str(sub / "results" / "calibration_curve.png"))
    safe_copy(str(imp_src), str(sub / "results" / "feature_importance.png"))
    safe_copy(str(root / "results" / "benchmark_results.json"), str(sub / "results" / "benchmark_results.json"))
    safe_copy(str(root / "results" / "dataset_report.json"), str(sub / "results" / "dataset_report.json"))
    safe_copy(str(root / "DEPLOYMENT_READY.md"), str(sub / "docs" / "DEPLOYMENT_READY.md"))
    safe_copy(str(root / "ENGLISH_ONLY_APPROACH.md"), str(sub / "docs" / "ENGLISH_ONLY_APPROACH.md"))
    safe_copy(str(root / "RUN_EVALUATION.md"), str(sub / "docs" / "RUN_EVALUATION.md"))
    safe_copy(str(root / "API.md"), str(sub / "API.md"))
    if (root / "app").exists():
        shutil.copytree(str(root / "app"), str(sub / "code" / "app"))
    if (root / "dataset").exists():
        shutil.copytree(str(root / "dataset"), str(sub / "code" / "dataset"))
    req_src = root / "requirements_production.txt"
    if req_src.exists():
        shutil.copy2(str(req_src), str(sub / "code" / "requirements.txt"))
    readme_code = "How to run locally\n\npython -m pip install -r code/requirements.txt\nuvicorn app.main:app --host 0.0.0.0 --port 8000\n"
    write_text(str(sub / "code" / "README_CODE.md"), readme_code)
    readme = "AI-Generated Voice Detection\n\nOverview\n\nEnglish-only model with calibrated confidence and sub-second latency.\n\nQuick Start\n\nSee code/README_CODE.md and docs/DEPLOYMENT_READY.md.\n\nDeployed API\n\nAdd URL in DEPLOYMENT_URL.txt.\n\nTeam\n\nYour Name\n"
    write_text(str(sub / "README.md"), readme)
    approach = "Approach\n\nProblem Analysis\n\nEnglish-only focus due to data completeness.\n\nSolution Design\n\nLogistic regression with calibrated probabilities.\n\nFeatures\n\nNine acoustic features.\n\nModel Selection\n\nL2 logistic with grid search.\n\nEvaluation\n\nAccuracy, ROC-AUC, ECE, latency.\n"
    write_text(str(sub / "APPROACH.md"), approach)
    write_text(str(sub / "DEPLOYMENT_URL.txt"), "")
    checklist = {"files": []}
    required = [
        "README.md",
        "APPROACH.md",
        "API.md",
        "FINAL_REPORT.md",
        "english_model_report.json",
        "code/app",
        "code/dataset",
        "code/requirements.txt",
        "code/README_CODE.md",
        "results/training_report.json",
        "results/confusion_matrix.png",
        "results/roc_curve.png",
        "results/calibration_curve.png",
        "results/feature_importance.png",
        "results/benchmark_results.json",
        "results/dataset_report.json",
        "docs/API.md",
        "docs/DEPLOYMENT_READY.md",
        "docs/ENGLISH_ONLY_APPROACH.md",
        "docs/RUN_EVALUATION.md",
        "DEPLOYMENT_URL.txt",
    ]
    for p in required:
        present = (sub / p).exists()
        checklist["files"].append({"path": p, "present": present})
    with open(str(sub / "submission_checklist.json"), "w", encoding="utf-8") as f:
        json.dump(checklist, f, indent=2)
    print("OK")


if __name__ == "__main__":
    main()
