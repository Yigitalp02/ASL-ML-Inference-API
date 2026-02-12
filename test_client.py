#!/usr/bin/env python3
"""
Simple test client for ASL ML API
Tests prediction endpoint with sample sensor data
"""
import requests
import json
import sys
import time
from typing import List

# API URL (change as needed)
API_URL = "http://192.168.50.100:8100"  # or "https://asl.ybilgin.com"

# Sample sensor data for different letters
SAMPLE_DATA = {
    "A": [512.3, 678.1, 345.9, 890.2, 234.5],
    "B": [723.4, 456.2, 234.1, 567.8, 890.3],
    "C": [345.1, 789.2, 456.3, 234.5, 678.9],
    "D": [456.7, 234.5, 890.1, 345.6, 567.2],
    "E": [789.3, 345.6, 567.8, 123.4, 456.7],
}

def test_health():
    """Test /health endpoint"""
    print("\n🏥 Testing Health Endpoint...")
    print("-" * 50)
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Status: {data['status']}")
        print(f"✓ Model: {data['model_name']}")
        print(f"✓ Database: {'Connected' if data['database_connected'] else 'Not connected'}")
        print(f"✓ Uptime: {data['uptime_seconds']:.1f}s")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_prediction(sensor_data: List[float], expected_letter: str = None):
    """Test /predict endpoint"""
    print(f"\n🤖 Testing Prediction...")
    if expected_letter:
        print(f"   Expected: {expected_letter}")
    print("-" * 50)
    
    try:
        payload = {
            "flex_sensors": sensor_data,
            "device_id": "test-client"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/predict",
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        latency = (time.time() - start_time) * 1000
        
        data = response.json()
        
        print(f"✓ Predicted Letter: {data['letter']}")
        print(f"✓ Confidence: {data['confidence']*100:.1f}%")
        print(f"✓ Processing Time: {data['processing_time_ms']:.2f}ms")
        print(f"✓ Network Latency: {latency:.2f}ms")
        print(f"✓ Total Time: {latency:.2f}ms")
        
        if expected_letter:
            if data['letter'] == expected_letter:
                print(f"✓ Prediction matches expected letter!")
            else:
                print(f"⚠ Prediction ({data['letter']}) differs from expected ({expected_letter})")
        
        # Show top 3 predictions
        probs = data['all_probabilities']
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
        print("\nTop 3 Predictions:")
        for letter, prob in sorted_probs:
            bar = "█" * int(prob * 20)
            print(f"  {letter}: {prob*100:5.1f}% {bar}")
        
        return True
    except Exception as e:
        print(f"✗ Prediction failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False

def test_stats():
    """Test /stats endpoint"""
    print("\n📊 Testing Statistics Endpoint...")
    print("-" * 50)
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Total Predictions: {data['total_predictions']}")
        print(f"✓ Avg Confidence (24h): {data['last_24h_avg_confidence']*100:.1f}%")
        print(f"✓ Avg Processing (1h): {data['last_1h_avg_processing_ms']:.2f}ms")
        
        if data['top_letters_24h']:
            print("\nTop Letters (Last 24h):")
            for item in data['top_letters_24h'][:5]:
                print(f"  {item['letter']}: {item['count']} predictions")
        
        return True
    except Exception as e:
        print(f"✗ Stats failed: {e}")
        return False

def load_test(iterations: int = 10):
    """Run multiple predictions to test performance"""
    print(f"\n⚡ Load Test ({iterations} requests)...")
    print("-" * 50)
    
    latencies = []
    letters = list(SAMPLE_DATA.keys())
    
    for i in range(iterations):
        letter = letters[i % len(letters)]
        sensor_data = SAMPLE_DATA[letter]
        
        try:
            start = time.time()
            response = requests.post(
                f"{API_URL}/predict",
                json={
                    "flex_sensors": sensor_data,
                    "device_id": "load-test"
                },
                timeout=5
            )
            response.raise_for_status()
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            
            print(f"  [{i+1}/{iterations}] {latency:.1f}ms", end="\r")
        except Exception as e:
            print(f"\n  ✗ Request {i+1} failed: {e}")
    
    print("\n")
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        print(f"✓ Completed {len(latencies)}/{iterations} requests")
        print(f"  Avg: {avg_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")
        print(f"  Throughput: {1000/avg_latency:.1f} req/s")

def main():
    """Main test runner"""
    print("=" * 50)
    print("ASL ML API Test Client")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--load":
            iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            if test_health():
                load_test(iterations)
            return
        elif sys.argv[1] == "--help":
            print("\nUsage:")
            print("  python test_client.py           # Run all tests")
            print("  python test_client.py --load N  # Load test with N requests")
            print("  python test_client.py --help    # Show this help")
            return
    
    # Run all tests
    success = True
    
    # Test 1: Health
    success &= test_health()
    
    # Test 2: Sample predictions
    for letter, sensor_data in SAMPLE_DATA.items():
        success &= test_prediction(sensor_data, letter)
    
    # Test 3: Statistics
    success &= test_stats()
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed!")
    else:
        print("⚠ Some tests failed")
    print("=" * 50)
    print("\nFor interactive testing, visit:")
    print(f"  {API_URL}/docs")
    print("")

if __name__ == "__main__":
    main()

