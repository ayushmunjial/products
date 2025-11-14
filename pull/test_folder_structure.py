#!/usr/bin/env python3
"""
Quick test script to verify folder structure changes without running full API pull
"""
import sys
import os
import importlib.util

# Load the module with hyphen in filename
spec = importlib.util.spec_from_file_location("product_footprints", "product-footprints.py")
product_footprints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product_footprints)

# Import the function we want to test
create_folder_path = product_footprints.create_folder_path

def test_folder_structure():
    print("=" * 60)
    print("Testing Folder Structure Logic")
    print("=" * 60)
    
    # Test 1: US-ME state (should create US/Category)
    print("\n1. Testing US-ME state:")
    result = create_folder_path('US-ME', '04073', 'Brick')
    print(f"   Input: state='US-ME', zipcode='04073', category='Brick'")
    print(f"   Output: {result}")
    assert 'US/Brick' in result, "❌ Should create US/Brick folder"
    assert 'US-ME' not in result, "❌ Should not include US-ME in path"
    assert '04' not in result, "❌ Should not include zipcode prefix"
    assert '073' not in result, "❌ Should not include zipcode suffix"
    print("   ✅ PASS: US-ME creates US/Brick structure")
    
    # Test 2: Another US state
    print("\n2. Testing US-CA state:")
    result = create_folder_path('US-CA', '90210', 'Cement')
    print(f"   Input: state='US-CA', zipcode='90210', category='Cement'")
    print(f"   Output: {result}")
    assert 'US/Cement' in result, "❌ Should create US/Cement folder"
    assert 'US-CA' not in result, "❌ Should not include US-CA in path"
    print("   ✅ PASS: US-CA creates US/Cement structure")
    
    # Test 3: IN state (should remain unchanged)
    print("\n3. Testing IN state:")
    result = create_folder_path('IN', None, 'Cement')
    print(f"   Input: state='IN', zipcode=None, category='Cement'")
    print(f"   Output: {result}")
    assert 'IN/Cement' in result, "❌ Should create IN/Cement folder"
    assert 'US' not in result, "❌ Should not include US in path"
    print("   ✅ PASS: IN creates IN/Cement structure (unchanged)")
    
    # Test 4: IN with different category
    print("\n4. Testing IN with different category:")
    result = create_folder_path('IN', '122001', 'Steel')
    print(f"   Input: state='IN', zipcode='122001', category='Steel'")
    print(f"   Output: {result}")
    assert 'IN/Steel' in result, "❌ Should create IN/Steel folder"
    print("   ✅ PASS: IN creates IN/Steel structure")
    
    print("\n" + "=" * 60)
    print("✅ All folder structure tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_folder_structure()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

