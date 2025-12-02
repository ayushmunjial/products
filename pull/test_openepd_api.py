"""
Script to test openEPD API access and inspect response structure.
Uses the same authentication as EC3 API.
"""
import requests
import json
import yaml
from myconfig import email, password

def get_auth():
    """Get authentication token (same as product-footprints.py)"""
    url_auth = "https://buildingtransparency.org/api/rest-auth/login"
    headers_auth = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload_auth = {
        "username": email,
        "password": password
    }
    response_auth = requests.post(url_auth, headers=headers_auth, json=payload_auth)
    if response_auth.status_code == 200:
        authorization = 'Bearer ' + response_auth.json()['key']
        print("✓ Authentication successful", flush=True)
        return authorization
    else:
        print(f"✗ Failed to login. Status code: {response_auth.status_code}")
        print("Response body:" + str(response_auth.json()))
        return None

def test_openepd_api_basic(authorization):
    """Test basic openEPD API access"""
    openepd_url = "https://openepd.buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    # Get a sample EPD
    params = {"page_size": 1, "page_number": 1}
    
    print("\n" + "="*70)
    print("Testing openEPD API Basic Access")
    print("="*70)
    print(f"URL: {openepd_url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(openepd_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Received {len(data)} EPD(s)")
            
            if data:
                epd = data[0]
                print(f"\nSample EPD ID: {epd.get('id', 'N/A')}")
                print(f"Sample EPD Name: {epd.get('name', 'N/A')[:50]}...")
                
                # Check for key fields
                print("\n" + "-"*70)
                print("Key Fields Present:")
                print("-"*70)
                key_fields = ['id', 'name', 'gwp', 'impacts', 'resource_uses', 'category']
                for field in key_fields:
                    present = field in epd
                    value = epd.get(field)
                    if isinstance(value, dict):
                        value_str = f"dict with {len(value)} keys" if value else "empty dict"
                    elif isinstance(value, list):
                        value_str = f"list with {len(value)} items"
                    else:
                        value_str = str(value)[:50] if value else "None"
                    print(f"  {'✓' if present else '✗'} {field}: {value_str}")
                
                return epd
            else:
                print("⚠ No EPDs returned")
                return None
        else:
            print(f"✗ Error: Status code {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print("✗ Request timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {str(e)}")
        return None

def inspect_epd_structure(epd):
    """Inspect detailed structure of an EPD"""
    if not epd:
        return
    
    print("\n" + "="*70)
    print("Detailed EPD Structure Inspection")
    print("="*70)
    
    # Check impacts field
    print("\n" + "-"*70)
    print("Impacts Field:")
    print("-"*70)
    impacts = epd.get('impacts', {})
    if impacts:
        print(f"✓ Impacts field is populated with {len(impacts)} categories:")
        for key, value in impacts.items():
            print(f"  - {key}: {value}")
    else:
        print("✗ Impacts field is empty or missing")
    
    # Check resource_uses field
    print("\n" + "-"*70)
    print("Resource Uses Field:")
    print("-"*70)
    resource_uses = epd.get('resource_uses', {})
    if resource_uses:
        print(f"✓ Resource uses field is populated with {len(resource_uses)} types:")
        for key, value in resource_uses.items():
            print(f"  - {key}: {value}")
    else:
        print("✗ Resource uses field is empty or missing")
    
    # Check for LCIA impact categories
    print("\n" + "-"*70)
    print("Looking for LCIA Impact Categories:")
    print("-"*70)
    lcia_categories = [
        'ozone_depletion', 'ozone_depletion_potential', 'odp',
        'acidification', 'acidification_potential', 'ap',
        'eutrophication', 'eutrophication_potential', 'ep',
        'photochemical_ozone', 'photochemical_ozone_creation', 'pocp', 'smog',
        'abiotic_resource', 'abiotic_resource_depletion', 'ard'
    ]
    
    found_lcia = []
    if impacts:
        for category in lcia_categories:
            for key in impacts.keys():
                if category.lower() in key.lower():
                    found_lcia.append(key)
    
    if found_lcia:
        print(f"✓ Found {len(found_lcia)} LCIA-related categories:")
        for cat in found_lcia:
            print(f"  - {cat}: {impacts.get(cat)}")
    else:
        print("✗ No LCIA impact categories found in impacts field")
    
    # Check for resource use indicators
    print("\n" + "-"*70)
    print("Looking for Resource Use Indicators:")
    print("-"*70)
    resource_indicators = [
        'energy', 'primary_energy', 'renewable', 'non_renewable',
        'water', 'waste', 'output_flows'
    ]
    
    found_resources = []
    if resource_uses:
        for indicator in resource_indicators:
            for key in resource_uses.keys():
                if indicator.lower() in key.lower():
                    found_resources.append(key)
    
    if found_resources:
        print(f"✓ Found {len(found_resources)} resource use indicators:")
        for res in found_resources:
            print(f"  - {res}: {resource_uses.get(res)}")
    else:
        print("✗ No resource use indicators found in resource_uses field")
    
    # Print full structure for reference
    print("\n" + "-"*70)
    print("Full EPD Structure (first level keys):")
    print("-"*70)
    for key in sorted(epd.keys()):
        value = epd[key]
        if isinstance(value, dict):
            print(f"  {key}: dict with {len(value)} keys")
        elif isinstance(value, list):
            print(f"  {key}: list with {len(value)} items")
        else:
            value_str = str(value)[:50] if value else "None"
            print(f"  {key}: {value_str}")

def fetch_multiple_epds(authorization, count=5):
    """Fetch multiple EPDs to check if any have impact/resource data"""
    openepd_url = "https://openepd.buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    params = {"page_size": count, "page_number": 1}
    
    print("\n" + "="*70)
    print(f"Fetching {count} EPDs to Check for Impact/Resource Data")
    print("="*70)
    
    try:
        response = requests.get(openepd_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            epds = response.json()
            print(f"✓ Fetched {len(epds)} EPDs")
            
            with_impacts = 0
            with_resources = 0
            
            for i, epd in enumerate(epds, 1):
                has_impacts = epd.get('impacts', {}) != {}
                has_resources = epd.get('resource_uses', {}) != {}
                
                if has_impacts:
                    with_impacts += 1
                    print(f"\n  EPD {i} ({epd.get('id', 'N/A')[:20]}...):")
                    print(f"    ✓ Has impacts: {list(epd.get('impacts', {}).keys())}")
                
                if has_resources:
                    with_resources += 1
                    if not has_impacts:  # Only print if we haven't already
                        print(f"\n  EPD {i} ({epd.get('id', 'N/A')[:20]}...):")
                    print(f"    ✓ Has resource_uses: {list(epd.get('resource_uses', {}).keys())}")
            
            print(f"\nSummary: {with_impacts}/{len(epds)} EPDs have impacts, {with_resources}/{len(epds)} have resource_uses")
            
            return epds
        else:
            print(f"✗ Error: Status code {response.status_code}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return []

def save_sample_response(epd, filename="openepd_sample_response.yaml"):
    """Save sample response to YAML file for inspection"""
    if epd:
        with open(filename, 'w') as f:
            yaml.dump(epd, f, default_flow_style=False, sort_keys=False)
        print(f"\n✓ Sample response saved to: {filename}")

if __name__ == "__main__":
    print("="*70)
    print("openEPD API Testing Script")
    print("="*70)
    
    # Authenticate
    auth = get_auth()
    if not auth:
        print("\n✗ Cannot proceed without authentication")
        exit(1)
    
    # Test basic access
    sample_epd = test_openepd_api_basic(auth)
    
    if sample_epd:
        # Inspect structure
        inspect_epd_structure(sample_epd)
        
        # Save sample for reference
        save_sample_response(sample_epd)
        
        # Fetch multiple EPDs to check coverage
        fetch_multiple_epds(auth, count=10)
    
    print("\n" + "="*70)
    print("Testing Complete")
    print("="*70)

