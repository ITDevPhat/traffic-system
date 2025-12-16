#!/usr/bin/env python3
"""
Test script to verify FK constraint fix
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_fixed_violation():
    """Test that FK constraint error is fixed"""
    print("🔧 Testing FK constraint fix...")
    
    # Test CAR_RED_LIGHT
    car_data = {
        "violation_type": "CAR_RED_LIGHT",
        "track_id": 999,  # This should NOT cause FK error anymore
        "frame": 1500,
        "confidence": 0.85
    }
    
    print("🚗 Testing CAR_RED_LIGHT with track_id 999...")
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=car_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS: Created violation ID {result['violation_id']}")
        print(f"📋 Plate should be: 60K-37766")
        print(f"🖼️ Images: {result['images']}")
        
        # Get details to verify
        detail_response = requests.get(f"{API_URL}/api/violations/{result['violation_id']}")
        if detail_response.status_code == 200:
            detail = detail_response.json()
            print(f"✅ Verified plate: {detail.get('plate', 'None')}")
            print(f"✅ Verified plate_img: {detail.get('plate_img', 'None')}")
        
    else:
        print(f"❌ FAILED: {response.status_code}")
        try:
            error = response.json()
            print(f"Error: {error}")
        except:
            print(f"Error text: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Test BIKE_RED_LIGHT
    bike_data = {
        "violation_type": "BIKE_RED_LIGHT",
        "track_id": 888,  # This should NOT cause FK error anymore
        "frame": 2000,
        "confidence": 0.90
    }
    
    print("🏍️ Testing BIKE_RED_LIGHT with track_id 888...")
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=bike_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS: Created violation ID {result['violation_id']}")
        print(f"📋 Plate should be: None/UNKNOWN")
        print(f"🖼️ Images: {result['images']}")
        
        # Get details to verify
        detail_response = requests.get(f"{API_URL}/api/violations/{result['violation_id']}")
        if detail_response.status_code == 200:
            detail = detail_response.json()
            plate = detail.get('plate')
            print(f"✅ Verified plate: {plate if plate else 'None/UNKNOWN'}")
            print(f"✅ Verified plate_img: {detail.get('plate_img', 'None')}")
        
    else:
        print(f"❌ FAILED: {response.status_code}")
        try:
            error = response.json()
            print(f"Error: {error}")
        except:
            print(f"Error text: {response.text}")

def main():
    print("🧪 Testing Foreign Key Constraint Fix")
    print("=" * 50)
    
    try:
        test_fixed_violation()
        
        print("\n🎉 Test completed!")
        print("If both tests passed, the FK constraint error is fixed!")
        print("👀 Check http://localhost:3000/violations/management")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend on http://localhost:8000")
        print("Make sure the backend is running!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()