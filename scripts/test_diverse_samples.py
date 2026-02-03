#!/usr/bin/env python3
"""
Test script to validate the API with diverse audio samples.
Tests various languages, audio qualities, and edge cases.
"""
import os
import base64
import json
import argparse
import requests
from pathlib import Path
from typing import List, Dict


def test_audio_file(
    url: str,
    api_key: str,
    audio_file: str,
    language: str
) -> Dict:
    """Test a single audio file."""
    audio_path = Path(audio_file)
    if not audio_path.exists():
        return {
            "success": False,
            "error": f"File not found: {audio_file}"
        }
    
    with open(audio_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    try:
        response = requests.post(
            url,
            json={
                "language": language,
                "audioFormat": "mp3",
                "audioBase64": audio_base64
            },
            headers={"x-api-key": api_key},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "file": str(audio_path.name),
                "language": language,
                "classification": data.get("classification"),
                "confidence": data.get("confidenceScore"),
                "confidenceCategory": data.get("confidenceCategory"),
                "qualityScore": data.get("audioQuality", {}).get("qualityScore") if data.get("audioQuality") else None,
                "explanation": data.get("explanation")
            }
        else:
            return {
                "success": False,
                "file": str(audio_path.name),
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "file": str(audio_path.name),
            "error": str(e)
        }


def test_directory(
    url: str,
    api_key: str,
    directory: str,
    language: str
) -> List[Dict]:
    """Test all MP3 files in a directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"❌ Directory not found: {directory}")
        return []
    
    mp3_files = list(dir_path.glob("*.mp3"))
    if not mp3_files:
        print(f"⚠️  No MP3 files found in {directory}")
        return []
    
    results = []
    print(f"📁 Testing {len(mp3_files)} files from {directory} ({language})...")
    
    for mp3_file in mp3_files:
        result = test_audio_file(url, api_key, str(mp3_file), language)
        results.append(result)
        
        if result["success"]:
            print(f"   ✅ {mp3_file.name}: {result['classification']} "
                  f"(confidence: {result['confidence']:.2f}, "
                  f"quality: {result['qualityScore']:.2f if result['qualityScore'] else 'N/A'})")
        else:
            print(f"   ❌ {mp3_file.name}: {result.get('error', 'Unknown error')}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Test API with diverse audio samples")
    parser.add_argument("--url", default="http://localhost:8000/api/voice-detection",
                       help="API endpoint URL")
    parser.add_argument("--api-key", default="sk_test_123456789",
                       help="API key")
    parser.add_argument("--data-dir", default="data",
                       help="Base data directory")
    
    args = parser.parse_args()
    
    languages = ["english", "tamil", "hindi", "malayalam", "telugu"]
    sources = ["human", "ai"]
    
    print("🧪 Testing API with diverse audio samples\n")
    print(f"URL: {args.url}")
    print(f"Data directory: {args.data_dir}\n")
    
    all_results = []
    
    for source in sources:
        for lang in languages:
            lang_dir = Path(args.data_dir) / source / lang
            if lang_dir.exists():
                lang_name = lang.capitalize()
                results = test_directory(args.url, args.api_key, str(lang_dir), lang_name)
                all_results.extend(results)
                print()
    
    # Summary
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    successful = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]
    
    print(f"Total tests: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Success rate: {len(successful)/len(all_results)*100:.1f}%")
    
    if successful:
        classifications = {}
        for r in successful:
            cls = r.get("classification", "UNKNOWN")
            classifications[cls] = classifications.get(cls, 0) + 1
        
        print(f"\nClassifications:")
        for cls, count in classifications.items():
            print(f"  {cls}: {count}")
        
        confidences = [r.get("confidence", 0) for r in successful]
        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            print(f"\nAverage confidence: {avg_conf:.2f}")
        
        quality_scores = [r.get("qualityScore") for r in successful if r.get("qualityScore")]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"Average quality score: {avg_quality:.2f}")
    
    if failed:
        print(f"\n❌ Failed tests:")
        for r in failed[:10]:  # Show first 10 failures
            print(f"  {r.get('file', 'unknown')}: {r.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
