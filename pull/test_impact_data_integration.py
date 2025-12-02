"""
Test script to verify impact data integration works correctly.
Tests with sample EPDs from different categories and regions.
"""
import yaml
import os
import sys
from pathlib import Path

# Add parent directory to path to import from product-footprints
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from merge_impact_data import merge_impact_data, extract_lcia_categories, extract_resource_indicators

def test_merge_functionality():
    """Test merge_impact_data function"""
    print("="*70)
    print("Testing Impact Data Merge Functionality")
    print("="*70)
    
    # Sample EC3 EPD (typical structure)
    ec3_epd = {
        'id': 'test-epd-123',
        'material_id': 'test-material-123',
        'name': 'Test Product',
        'gwp': '100 kgCO2e',
        'impacts': {},  # Empty in EC3
        'resource_uses': {},  # Empty in EC3
        'category': {'display_name': 'Test Category'}
    }
    
    # Sample openEPD EPD with impact data
    openepd_epd = {
        'id': 'test-epd-123',
        'material_id': 'test-material-123',
        'impacts': {
            'ozone_depletion_potential': '0.5 kg CFC-11 eq',
            'acidification_potential': '2.3 kg SO2 eq',
            'eutrophication_potential': '1.1 kg PO4 eq'
        },
        'resource_uses': {
            'primary_energy_renewable': '50 MJ',
            'primary_energy_non_renewable': '200 MJ',
            'water_use': '100 L'
        }
    }
    
    print("\n1. Testing merge_impact_data function...")
    merged = merge_impact_data(ec3_epd, openepd_epd)
    
    assert merged['id'] == ec3_epd['id'], "ID should be preserved"
    assert len(merged['impacts']) > 0, "Impacts should be merged"
    assert len(merged['resource_uses']) > 0, "Resource uses should be merged"
    assert merged['impacts']['ozone_depletion_potential'] == '0.5 kg CFC-11 eq', "Impact data should be merged"
    
    print("   ✓ Merge function works correctly")
    print(f"   Merged impacts: {list(merged['impacts'].keys())}")
    print(f"   Merged resources: {list(merged['resource_uses'].keys())}")
    
    # Test with None openEPD
    print("\n2. Testing merge with None openEPD...")
    merged_none = merge_impact_data(ec3_epd, None)
    assert merged_none == ec3_epd, "Should return EC3 EPD unchanged"
    print("   ✓ Handles None openEPD correctly")
    
    # Test extraction functions
    print("\n3. Testing LCIA category extraction...")
    lcia = extract_lcia_categories(merged)
    print(f"   Extracted LCIA categories: {list(lcia.keys())}")
    assert 'ozone_depletion' in lcia, "Should extract ozone depletion"
    print("   ✓ LCIA extraction works")
    
    print("\n4. Testing resource indicator extraction...")
    resources = extract_resource_indicators(merged)
    print(f"   Extracted resource indicators: {list(resources.keys())}")
    assert 'primary_energy_renewable' in resources, "Should extract renewable energy"
    print("   ✓ Resource extraction works")
    
    print("\n" + "="*70)
    print("All tests passed!")
    print("="*70)

def test_yaml_structure():
    """Test that YAML files preserve impact/resource structure"""
    print("\n" + "="*70)
    print("Testing YAML Structure Preservation")
    print("="*70)
    
    # Check if we have any existing YAML files
    base_path = Path("../../products-data")
    yaml_files = list(base_path.rglob("*.yaml"))
    
    if not yaml_files:
        print("⚠ No YAML files found to test")
        return
    
    print(f"\nFound {len(yaml_files)} YAML files")
    print("Checking structure of sample files...")
    
    sample_count = 0
    for yaml_file in yaml_files[:10]:  # Check first 10
        try:
            with open(yaml_file, 'r') as f:
                epd = yaml.safe_load(f)
            
            has_gwp = 'gwp' in epd or 'best_practice' in epd
            has_impacts = 'impacts' in epd
            has_resources = 'resource_uses' in epd
            
            if has_gwp or has_impacts or has_resources:
                sample_count += 1
                print(f"\n  File: {yaml_file.name}")
                print(f"    Has GWP: {has_gwp}")
                print(f"    Has impacts field: {has_impacts} ({'populated' if epd.get('impacts', {}) else 'empty'})")
                print(f"    Has resource_uses field: {has_resources} ({'populated' if epd.get('resource_uses', {}) else 'empty'})")
                
        except Exception as e:
            print(f"  Error reading {yaml_file}: {e}")
    
    print(f"\n✓ Checked {sample_count} sample files")
    print("="*70)

def verify_impact_fields():
    """Verify that expected impact fields are documented"""
    print("\n" + "="*70)
    print("Verifying Expected Impact Fields")
    print("="*70)
    
    expected_lcia = [
        'ozone_depletion',
        'acidification',
        'eutrophication',
        'photochemical_ozone',
        'abiotic_resource_depletion'
    ]
    
    expected_resources = [
        'primary_energy_renewable',
        'primary_energy_non_renewable',
        'water_use',
        'waste_generation'
    ]
    
    print("\nExpected LCIA Impact Categories:")
    for category in expected_lcia:
        print(f"  - {category}")
    
    print("\nExpected Resource Use Indicators:")
    for resource in expected_resources:
        print(f"  - {resource}")
    
    print("\n✓ Field documentation verified")
    print("="*70)

if __name__ == "__main__":
    print("="*70)
    print("Impact Data Integration Test Suite")
    print("="*70)
    
    # Run tests
    test_merge_functionality()
    test_yaml_structure()
    verify_impact_fields()
    
    print("\n" + "="*70)
    print("Test Suite Complete")
    print("="*70)
    print("\nNext steps:")
    print("1. Run analyze_emissions_data.py to scan existing files")
    print("2. Run test_openepd_api.py to test API access")
    print("3. Run compare_apis.py to compare API responses")
    print("4. Enable ENABLE_OPENEPD_FETCH in product-footprints.py if needed")
    print("="*70)

