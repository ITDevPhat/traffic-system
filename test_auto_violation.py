#!/usr/bin/env python3
"""
Test script để kiểm tra API auto-create violation cho video8.mp4
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_auto_create_violation():
    """Test tạo vi phạm tự động"""
    
    # Test CAR_RED_LIGHT
    car_data = {
        "violation_type": "CAR_RED_LIGHT",
        "track_id": 123,
        "frame": 1500,
        "confidence": 0.85,
        "plate": "30A-12345"
    }
    
    print("🚗 Testing CAR_RED_LIGHT violation...")
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=car_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success: {result['message']}")
        print(f"📋 Violation ID: {result['violation_id']}")
        print(f"🖼️ Plate image: {result['images']['plate']}")
        print(f"🖼️ Evidence image: {result['images']['evidence']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Test BIKE_RED_LIGHT
    bike_data = {
        "violation_type": "BIKE_RED_LIGHT",
        "track_id": 456,
        "frame": 2000,
        "confidence": 0.90,
        "plate": "59X1-98765"
    }
    
    print("🏍️ Testing BIKE_RED_LIGHT violation...")
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=bike_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success: {result['message']}")
        print(f"📋 Violation ID: {result['violation_id']}")
        print(f"🖼️ Plate image: {result['images']['plate']}")
        print(f"🖼️ Evidence image: {result['images']['evidence']}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def test_get_violations():
    """Test lấy danh sách vi phạm"""
    print("\n📋 Getting violations list...")
    response = requests.get(f"{API_URL}/api/violations")
    
    if response.status_code == 200:
        violations = response.json()
        print(f"✅ Found {len(violations)} violations")
        for v in violations[:3]:  # Show first 3
            print(f"  - ID: {v['violation_id']}, Type: {v.get('violation_type_code', 'N/A')}, Plate: {v.get('plate', 'N/A')}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("🧪 Testing Auto Violation Creation API\n")
    
    try:
        test_auto_create_violation()
        test_get_violations()
        
        print("\n🎉 Test completed!")
        print("👀 Check http://localhost:3000/violations/management to see the violations")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")