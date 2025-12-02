"""
Script to compare EC3 API and openEPD API responses for the same EPD.
Helps determine which API has more complete impact and resource data.
"""
import requests
import json
import yaml
from myconfig import email, password

def get_auth():
    """Get authentication token"""
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
        return None

def fetch_from_ec3_api(epd_id, authorization):
    """Fetch EPD from EC3 API by ID"""
    ec3_url = "https://buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    # Try to fetch by ID - may need to search
    params = {"page_size": 1}
    
    try:
        # First, try to get a list and find the EPD
        response = requests.get(ec3_url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            epds = response.json()
            # Search for matching ID
            for epd in epds:
                if epd.get('id') == epd_id or epd.get('material_id') == epd_id:
                    return epd
    except Exception as e:
        print(f"Error fetching from EC3: {e}")
    
    return None

def fetch_from_openepd_api(epd_id, authorization):
    """Fetch EPD from openEPD API by ID"""
    openepd_url = "https://openepd.buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    # Try to fetch by ID
    params = {"page_size": 100}  # Get more to find matching ID
    
    try:
        response = requests.get(openepd_url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            epds = response.json()
            # Search for matching ID
            for epd in epds:
                if epd.get('id') == epd_id or epd.get('material_id') == epd_id:
                    return epd
    except Exception as e:
        print(f"Error fetching from openEPD: {e}")
    
    return None

def get_sample_epd_ids(authorization, count=5):
    """Get sample EPD IDs from EC3 API to compare"""
    ec3_url = "https://buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    params = {"page_size": count, "plant_geography": "US-ME"}
    
    try:
        response = requests.get(ec3_url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            epds = response.json()
            return [epd.get('id') for epd in epds if epd.get('id')]
    except Exception as e:
        print(f"Error getting sample EPDs: {e}")
    
    return []

def compare_epd_fields(ec3_epd, openepd_epd, epd_id):
    """Compare fields between EC3 and openEPD responses"""
    print("\n" + "="*70)
    print(f"Comparing EPD: {epd_id}")
    print("="*70)
    
    if not ec3_epd:
        print("✗ EC3 API: EPD not found")
        return None
    
    if not openepd_epd:
        print("✗ openEPD API: EPD not found")
        return None
    
    comparison = {
        'epd_id': epd_id,
        'ec3_has_impacts': bool(ec3_epd.get('impacts', {})),
        'openepd_has_impacts': bool(openepd_epd.get('impacts', {})),
        'ec3_has_resources': bool(ec3_epd.get('resource_uses', {})),
        'openepd_has_resources': bool(openepd_epd.get('resource_uses', {})),
        'ec3_impacts_keys': list(ec3_epd.get('impacts', {}).keys()),
        'openepd_impacts_keys': list(openepd_epd.get('impacts', {}).keys()),
        'ec3_resources_keys': list(ec3_epd.get('resource_uses', {}).keys()),
        'openepd_resources_keys': list(openepd_epd.get('resource_uses', {}).keys()),
    }
    
    print("\n" + "-"*70)
    print("Impacts Field Comparison:")
    print("-"*70)
    print(f"EC3 API:      {'✓' if comparison['ec3_has_impacts'] else '✗'} {len(comparison['ec3_impacts_keys'])} categories")
    if comparison['ec3_impacts_keys']:
        print(f"  Categories: {', '.join(comparison['ec3_impacts_keys'])}")
    
    print(f"openEPD API:   {'✓' if comparison['openepd_has_impacts'] else '✗'} {len(comparison['openepd_impacts_keys'])} categories")
    if comparison['openepd_impacts_keys']:
        print(f"  Categories: {', '.join(comparison['openepd_impacts_keys'])}")
    
    print("\n" + "-"*70)
    print("Resource Uses Field Comparison:")
    print("-"*70)
    print(f"EC3 API:      {'✓' if comparison['ec3_has_resources'] else '✗'} {len(comparison['ec3_resources_keys'])} types")
    if comparison['ec3_resources_keys']:
        print(f"  Types: {', '.join(comparison['ec3_resources_keys'])}")
    
    print(f"openEPD API:   {'✓' if comparison['openepd_has_resources'] else '✗'} {len(comparison['openepd_resources_keys'])} types")
    if comparison['openepd_resources_keys']:
        print(f"  Types: {', '.join(comparison['openepd_resources_keys'])}")
    
    # Compare specific LCIA categories
    print("\n" + "-"*70)
    print("LCIA Impact Categories Check:")
    print("-"*70)
    lcia_categories = {
        'ozone_depletion': ['ozone_depletion', 'ozone_depletion_potential', 'odp'],
        'acidification': ['acidification', 'acidification_potential', 'ap'],
        'eutrophication': ['eutrophication', 'eutrophication_potential', 'ep'],
        'photochemical_ozone': ['photochemical_ozone', 'photochemical_ozone_creation', 'pocp', 'smog'],
        'abiotic_resource': ['abiotic_resource', 'abiotic_resource_depletion', 'ard']
    }
    
    for category_name, search_terms in lcia_categories.items():
        ec3_found = False
        openepd_found = False
        
        for term in search_terms:
            if any(term.lower() in key.lower() for key in comparison['ec3_impacts_keys']):
                ec3_found = True
            if any(term.lower() in key.lower() for key in comparison['openepd_impacts_keys']):
                openepd_found = True
        
        print(f"  {category_name}:")
        print(f"    EC3:      {'✓' if ec3_found else '✗'}")
        print(f"    openEPD:  {'✓' if openepd_found else '✗'}")
    
    # Compare resource indicators
    print("\n" + "-"*70)
    print("Resource Use Indicators Check:")
    print("-"*70)
    resource_indicators = {
        'primary_energy_renewable': ['renewable', 'primary_energy_renewable'],
        'primary_energy_non_renewable': ['non_renewable', 'primary_energy_non_renewable'],
        'water_use': ['water'],
        'waste': ['waste', 'output_flows']
    }
    
    for indicator_name, search_terms in resource_indicators.items():
        ec3_found = False
        openepd_found = False
        
        for term in search_terms:
            if any(term.lower() in key.lower() for key in comparison['ec3_resources_keys']):
                ec3_found = True
            if any(term.lower() in key.lower() for key in comparison['openepd_resources_keys']):
                openepd_found = True
        
        print(f"  {indicator_name}:")
        print(f"    EC3:      {'✓' if ec3_found else '✗'}")
        print(f"    openEPD:  {'✓' if openepd_found else '✗'}")
    
    return comparison

def compare_multiple_epds(authorization, epd_ids):
    """Compare multiple EPDs from both APIs"""
    print("\n" + "="*70)
    print("Comparing Multiple EPDs")
    print("="*70)
    
    results = []
    
    for epd_id in epd_ids:
        print(f"\nFetching EPD {epd_id}...")
        
        # Fetch from both APIs
        ec3_epd = fetch_from_ec3_api(epd_id, authorization)
        openepd_epd = fetch_from_openepd_api(epd_id, authorization)
        
        if ec3_epd and openepd_epd:
            comparison = compare_epd_fields(ec3_epd, openepd_epd, epd_id)
            if comparison:
                results.append(comparison)
        else:
            print(f"  ⚠ Could not fetch EPD {epd_id} from one or both APIs")
    
    # Summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    
    if results:
        ec3_with_impacts = sum(1 for r in results if r['ec3_has_impacts'])
        openepd_with_impacts = sum(1 for r in results if r['openepd_has_impacts'])
        ec3_with_resources = sum(1 for r in results if r['ec3_has_resources'])
        openepd_with_resources = sum(1 for r in results if r['openepd_has_resources'])
        
        print(f"\nEPDs with Impact Categories:")
        print(f"  EC3 API:      {ec3_with_impacts}/{len(results)} ({ec3_with_impacts/len(results)*100:.1f}%)")
        print(f"  openEPD API:   {openepd_with_impacts}/{len(results)} ({openepd_with_impacts/len(results)*100:.1f}%)")
        
        print(f"\nEPDs with Resource Use Data:")
        print(f"  EC3 API:      {ec3_with_resources}/{len(results)} ({ec3_with_resources/len(results)*100:.1f}%)")
        print(f"  openEPD API:   {openepd_with_resources}/{len(results)} ({openepd_with_resources/len(results)*100:.1f}%)")
        
        # Determine which API is better
        print("\n" + "-"*70)
        print("Recommendation:")
        print("-"*70)
        if openepd_with_impacts > ec3_with_impacts or openepd_with_resources > ec3_with_resources:
            print("  → openEPD API appears to have more complete impact/resource data")
            print("  → Consider fetching from openEPD API to supplement EC3 data")
        elif ec3_with_impacts > openepd_with_impacts or ec3_with_resources > openepd_with_resources:
            print("  → EC3 API appears to have more complete impact/resource data")
            print("  → Current approach (EC3 only) may be sufficient")
        else:
            print("  → Both APIs have similar coverage")
            print("  → May need to check individual EPDs or use both APIs")
    
    return results

def save_comparison_results(results, filename="api_comparison_results.json"):
    """Save comparison results to file"""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Comparison results saved to: {filename}")

if __name__ == "__main__":
    print("="*70)
    print("EC3 API vs openEPD API Comparison")
    print("="*70)
    
    # Authenticate
    auth = get_auth()
    if not auth:
        print("\n✗ Cannot proceed without authentication")
        exit(1)
    
    # Get sample EPD IDs
    print("\nFetching sample EPD IDs from EC3 API...")
    epd_ids = get_sample_epd_ids(auth, count=5)
    
    if not epd_ids:
        print("✗ Could not get sample EPD IDs")
        exit(1)
    
    print(f"✓ Found {len(epd_ids)} sample EPD IDs")
    
    # Compare
    results = compare_multiple_epds(auth, epd_ids)
    
    # Save results
    if results:
        save_comparison_results(results)
    
    print("\n" + "="*70)
    print("Comparison Complete")
    print("="*70)

