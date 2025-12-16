#!/usr/bin/env python3
"""
Test complete workflow: Create violation -> Check images in detail page
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_car_violation_complete():
    """Test CAR violation with complete image display"""
    print("🚗 Testing CAR_RED_LIGHT complete workflow...")
    
    # 1. Create violation
    car_data = {
        "violation_type": "CAR_RED_LIGHT",
        "track_id": 777,
        "frame": 1500,
        "confidence": 0.85
    }
    
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=car_data)
    
    if response.status_code == 200:
        result = response.json()
        violation_id = result['violation_id']
        print(f"✅ Created violation ID: {violation_id}")
        
        # 2. Get violation details
        detail_response = requests.get(f"{API_URL}/api/violations/{violation_id}")
        if detail_response.status_code == 200:
            detail = detail_response.json()
            
            print(f"\n📋 Violation Details:")
            print(f"   - ID: {detail['violation_id']}")
            print(f"   - Plate: {detail.get('plate', 'None')} (should be 60K-37766)")
            print(f"   - Evidence Image: {detail.get('evidence_img', 'None')}")
            print(f"   - Plate Image: {detail.get('plate_img', 'None')}")
            
            # 3. Verify expected results
            success = True
            if detail.get('plate') != '60K-37766':
                print(f"❌ FAIL: Wrong plate. Expected '60K-37766', got '{detail.get('plate')}'")
                success = False
            
            if not detail.get('evidence_img'):
                print("❌ FAIL: Missing evidence_img")
                success = False
            elif 'main_car_red_light' not in detail.get('evidence_img', ''):
                print("❌ FAIL: Evidence image should contain 'main_car_red_light'")
                success = False
            
            if not detail.get('plate_img'):
                print("❌ FAIL: Missing plate_img")
                success = False
            elif 'plate_car_red_line' not in detail.get('plate_img', ''):
                print("❌ FAIL: Plate image should contain 'plate_car_red_line'")
                success = False
            
            if success:
                print("✅ PASS: All CAR violation checks passed!")
                print(f"👀 View details at: http://localhost:3000/violations/management/{violation_id}")
            
            return violation_id, success
        else:
            print("❌ Failed to get violation details")
            return None, False
    else:
        print(f"❌ Failed to create violation: {response.status_code}")
        return None, False

def test_bike_violation_complete():
    """Test BIKE violation with complete image display"""
    print("\n🏍️ Testing BIKE_RED_LIGHT complete workflow...")
    
    # 1. Create violation
    bike_data = {
        "violation_type": "BIKE_RED_LIGHT",
        "track_id": 666,
        "frame": 2000,
        "confidence": 0.90
    }
    
    response = requests.post(f"{API_URL}/api/violations/auto-create-video8", json=bike_data)
    
    if response.status_code == 200:
        result = response.json()
        violation_id = result['violation_id']
        print(f"✅ Created violation ID: {violation_id}")
        
        # 2. Get violation details
        detail_response = requests.get(f"{API_URL}/api/violations/{violation_id}")
        if detail_response.status_code == 200:
            detail = detail_response.json()
            
            print(f"\n📋 Violation Details:")
            print(f"   - ID: {detail['violation_id']}")
            print(f"   - Plate: {detail.get('plate') or 'None/UNKNOWN'} (should be None)")
            print(f"   - Evidence Image: {detail.get('evidence_img', 'None')}")
            print(f"   - Plate Image: {detail.get('plate_img', 'None')}")
            
            # 3. Verify expected results
            success = True
            if detail.get('plate') is not None:
                print(f"❌ FAIL: Plate should be None. Got '{detail.get('plate')}'")
                success = False
            
            if not detail.get('evidence_img'):
                print("❌ FAIL: Missing evidence_img")
                success = False
            elif 'main_bike_red_light' not in detail.get('evidence_img', ''):
                print("❌ FAIL: Evidence image should contain 'main_bike_red_light'")
                success = False
            
            if not detail.get('plate_img'):
                print("❌ FAIL: Missing plate_img")
                success = False
            elif 'plate_bike_red_line' not in detail.get('plate_img', ''):
                print("❌ FAIL: Plate image should contain 'plate_bike_red_line'")
                success = False
            
            if success:
                print("✅ PASS: All BIKE violation checks passed!")
                print(f"👀 View details at: http://localhost:3000/violations/management/{violation_id}")
            
            return violation_id, success
        else:
            print("❌ Failed to get violation details")
            return None, False
    else:
        print(f"❌ Failed to create violation: {response.status_code}")
        return None, False

def main():
    print("🧪 Testing Complete Video8 Violation Workflow")
    print("=" * 60)
    
    try:
        # Test CAR violation
        car_id, car_success = test_car_violation_complete()
        
        # Test BIKE violation  
        bike_id, bike_success = test_bike_violation_complete()
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY:")
        
        if car_success:
            print(f"✅ CAR violation (ID: {car_id}) - PASSED")
        else:
            print(f"❌ CAR violation - FAILED")
            
        if bike_success:
            print(f"✅ BIKE violation (ID: {bike_id}) - PASSED")
        else:
            print(f"❌ BIKE violation - FAILED")
        
        if car_success and bike_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("Both violations should now display 2 images each in the detail page:")
            print("- CAR: main_car_red_light.png + plate_car_red_line.png")
            print("- BIKE: main_bike_red_light.png + plate_bike_red_line.png")
            print("\n👀 Check: http://localhost:3000/violations/management")
        else:
            print("\n💥 SOME TESTS FAILED!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend on http://localhost:8000")
        print("Make sure the backend is running!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()