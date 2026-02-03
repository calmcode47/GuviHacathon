import os
import json
import time
import argparse


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_ready_md(path):
    res = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines()]
        for l in lines:
            if l.startswith("- "):
                k = l[2:].split(":")[0].strip()
                v = "PASS" in l
                res[k] = v
    except Exception:
        pass
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--ready-md", default="DEPLOYMENT_READY.md")
    args = ap.parse_args()
    train = read_json(os.path.join(args.results_dir, "training_report.json"))
    verify = read_json(os.path.join(args.results_dir, "verify_api.json"))
    bench = read_json(os.path.join(args.results_dir, "benchmark_results.json"))
    dsum = read_json(os.path.join(args.results_dir, "dataset_report.json"))
    ready = parse_ready_md(args.ready_md)
    report = {
        "generated_at": int(time.time()),
        "focus_language": "English",
        "training": train or {},
        "api_verification": verify or {},
        "performance": bench or {},
        "dataset_summary": dsum or {},
        "deployment_readiness": ready,
        "limitations": [
            "Model optimized for English only",
            "Non-English requests have confidence down-weighted",
            "Human data currently limited to English; others have AI-only"
        ],
        "recommendations": [
            "Add human samples for Hindi, Malayalam, Tamil, Telugu",
            "Retrain and re-calibrate multi-language model",
            "Remove confidence down-weight for languages passing validation"
        ],
    }
    os.makedirs(args.results_dir, exist_ok=True)
    with open(os.path.join(args.results_dir, "english_model_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    md = []
    md.append("# Final Report: English-Only Model")
    md.append("")
    md.append("## Overview")
    md.append("- Focus language: English")
    md.append(f"- Generated at: {report['generated_at']}")
    md.append("")
    md.append("## Training Metrics")
    if train:
        md.append(f"- Accuracy (train/val/test): {train.get('accuracy_train', 'NA')}, {train.get('accuracy_val', 'NA')}, {train.get('accuracy_test', 'NA')}")
        md.append(f"- ROC-AUC (test): {train.get('roc_auc_test', 'NA')}")
        md.append(f"- ECE (test): {train.get('ece_test', 'NA')}")
        md.append(f"- Confusion Matrix (test): {train.get('confusion_matrix_test', 'NA')}")
    else:
        md.append("- Training report not found")
    md.append("")
    md.append("## API Verification")
    if verify:
        pred = verify.get("prediction", {})
        md.append(f"- Status: {verify.get('status', 'NA')}")
        md.append(f"- Sample label: {pred.get('label', 'NA')}")
        md.append(f"- Confidence: {pred.get('confidence', 'NA')}")
        md.append(f"- p_ai: {pred.get('p_ai', 'NA')}")
    else:
        md.append("- Verification report not found")
    md.append("")
    md.append("## Performance Benchmarks")
    if bench:
        md.append(f"- Mean latency ms: {bench.get('mean_latency_ms', 'NA')}")
        md.append(f"- Median latency ms: {bench.get('median_latency_ms', 'NA')}")
        md.append(f"- p95 latency ms: {bench.get('p95_latency_ms', 'NA')}")
        md.append(f"- p99 latency ms: {bench.get('p99_latency_ms', 'NA')}")
        md.append(f"- Memory RSS MB mean: {bench.get('memory_rss_mb_mean', 'NA')}")
        md.append(f"- Samples: {bench.get('count', 'NA')}")
    else:
        md.append("- Benchmark report not found")
    md.append("")
    md.append("## Dataset Summary")
    if dsum:
        langs = dsum.get("per_language", {})
        md.append(f"- Total hours: {dsum.get('total_hours', 'NA')}")
        for lang, d in langs.items():
            md.append(f"- {lang}: human {d.get('human_samples', 0)}, ai {d.get('ai_samples', 0)}, avg dur {d.get('avg_duration_sec', 0)}s")
    else:
        md.append("- Dataset report not found")
    md.append("")
    md.append("## Deployment Readiness")
    if ready:
        for k, v in ready.items():
            md.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    else:
        md.append("- Deployment readiness checklist not found")
    md.append("")
    md.append("## Known Limitations")
    for l in report["limitations"]:
        md.append(f"- {l}")
    md.append("")
    md.append("## Recommendations")
    for r in report["recommendations"]:
        md.append(f"- {r}")
    with open("FINAL_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("OK")


if __name__ == "__main__":
    main()
