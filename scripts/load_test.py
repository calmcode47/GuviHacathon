#!/usr/bin/env python3
"""
Load testing script for the AI Voice Detection API.
Tests the API with concurrent requests to measure performance.
"""
import asyncio
import aiohttp
import time
import base64
import json
import argparse
from pathlib import Path
from typing import List, Dict
import statistics


async def send_request(
    session: aiohttp.ClientSession,
    url: str,
    api_key: str,
    audio_base64: str,
    language: str = "English"
) -> Dict:
    """Send a single request to the API."""
    start_time = time.time()
    try:
        async with session.post(
            url,
            json={
                "language": language,
                "audioFormat": "mp3",
                "audioBase64": audio_base64
            },
            headers={"x-api-key": api_key}
        ) as response:
            elapsed = time.time() - start_time
            data = await response.json()
            return {
                "status": response.status,
                "elapsed": elapsed,
                "success": response.status == 200,
                "data": data
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": 0,
            "elapsed": elapsed,
            "success": False,
            "error": str(e)
        }


async def run_load_test(
    url: str,
    api_key: str,
    audio_file: str,
    num_requests: int,
    concurrency: int,
    language: str = "English"
):
    """Run load test with specified parameters."""
    # Load audio file and convert to base64
    audio_path = Path(audio_file)
    if not audio_path.exists():
        print(f"❌ Error: Audio file not found: {audio_file}")
        return
    
    with open(audio_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    print(f"📊 Load Test Configuration:")
    print(f"   URL: {url}")
    print(f"   Total Requests: {num_requests}")
    print(f"   Concurrency: {concurrency}")
    print(f"   Language: {language}")
    print(f"   Audio File: {audio_file}")
    print()
    
    # Create semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_request(session, idx):
        async with semaphore:
            return await send_request(session, url, api_key, audio_base64, language)
    
    # Run requests
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [
            bounded_request(session, i)
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if successful:
        elapsed_times = [r["elapsed"] for r in successful]
        avg_time = statistics.mean(elapsed_times)
        median_time = statistics.median(elapsed_times)
        min_time = min(elapsed_times)
        max_time = max(elapsed_times)
        p95_time = statistics.quantiles(elapsed_times, n=20)[18] if len(elapsed_times) > 1 else avg_time
        p99_time = statistics.quantiles(elapsed_times, n=100)[98] if len(elapsed_times) > 1 else avg_time
        
        print("📈 Results:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Successful: {len(successful)}/{num_requests}")
        print(f"   Failed: {len(failed)}/{num_requests}")
        print(f"   Success Rate: {len(successful)/num_requests*100:.1f}%")
        print()
        print("⏱️  Response Times:")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   Median: {median_time:.3f}s")
        print(f"   Min: {min_time:.3f}s")
        print(f"   Max: {max_time:.3f}s")
        print(f"   P95: {p95_time:.3f}s")
        print(f"   P99: {p99_time:.3f}s")
        print(f"   Requests/sec: {len(successful)/total_time:.2f}")
        
        # Check if response time meets target (< 2 seconds)
        if avg_time < 2.0:
            print(f"   ✅ Average response time meets target (< 2s)")
        else:
            print(f"   ⚠️  Average response time exceeds target (>= 2s)")
        
        if p95_time < 2.0:
            print(f"   ✅ P95 response time meets target (< 2s)")
        else:
            print(f"   ⚠️  P95 response time exceeds target (>= 2s)")
    else:
        print("❌ All requests failed!")
        if failed:
            print(f"   First error: {failed[0].get('error', 'Unknown error')}")


def main():
    parser = argparse.ArgumentParser(description="Load test the AI Voice Detection API")
    parser.add_argument("--url", default="http://localhost:8000/api/voice-detection",
                       help="API endpoint URL")
    parser.add_argument("--api-key", default="sk_test_123456789",
                       help="API key")
    parser.add_argument("--audio-file", required=True,
                       help="Path to MP3 audio file for testing")
    parser.add_argument("--requests", type=int, default=50,
                       help="Number of requests to send")
    parser.add_argument("--concurrency", type=int, default=10,
                       help="Number of concurrent requests")
    parser.add_argument("--language", default="English",
                       choices=["English", "Tamil", "Hindi", "Malayalam", "Telugu"],
                       help="Language for testing")
    
    args = parser.parse_args()
    
    asyncio.run(run_load_test(
        args.url,
        args.api_key,
        args.audio_file,
        args.requests,
        args.concurrency,
        args.language
    ))


if __name__ == "__main__":
    main()
