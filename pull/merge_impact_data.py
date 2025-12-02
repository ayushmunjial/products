"""
Utility functions for merging impact and resource data from EC3 and openEPD APIs.
Handles matching EPDs between APIs and merging impact/resource data.
"""
import time
import requests

def match_epd_ids(ec3_epd, openepd_epd):
    """
    Match EPDs between EC3 and openEPD APIs using various ID fields.
    Returns True if they match, False otherwise.
    """
    # Try multiple matching strategies
    ec3_id = ec3_epd.get('id')
    ec3_material_id = ec3_epd.get('material_id')
    ec3_open_xpd_uuid = ec3_epd.get('open_xpd_uuid')
    
    openepd_id = openepd_epd.get('id')
    openepd_material_id = openepd_epd.get('material_id')
    openepd_open_xpd_uuid = openepd_epd.get('open_xpd_uuid')
    
    # Match by ID
    if ec3_id and openepd_id and ec3_id == openepd_id:
        return True
    
    # Match by material_id
    if ec3_material_id and openepd_material_id and ec3_material_id == openepd_material_id:
        return True
    
    # Match by open_xpd_uuid
    if ec3_open_xpd_uuid and openepd_open_xpd_uuid and ec3_open_xpd_uuid == openepd_open_xpd_uuid:
        return True
    
    return False

def merge_impact_data(ec3_epd, openepd_epd=None):
    """
    Merge impact data from EC3 and openEPD APIs.
    EC3 data takes precedence, but openEPD data fills in gaps.
    
    Args:
        ec3_epd: EPD data from EC3 API
        openepd_epd: Optional EPD data from openEPD API
    
    Returns:
        Merged EPD with combined impact and resource data
    """
    merged_epd = ec3_epd.copy()
    
    if not openepd_epd:
        return merged_epd
    
    # Merge impacts field
    ec3_impacts = ec3_epd.get('impacts', {}) or {}
    openepd_impacts = openepd_epd.get('impacts', {}) or {}
    
    # Start with EC3 impacts, add openEPD impacts that don't exist in EC3
    merged_impacts = ec3_impacts.copy()
    for key, value in openepd_impacts.items():
        if key not in merged_impacts or not merged_impacts[key]:
            merged_impacts[key] = value
    
    merged_epd['impacts'] = merged_impacts if merged_impacts else {}
    
    # Merge resource_uses field
    ec3_resources = ec3_epd.get('resource_uses', {}) or {}
    openepd_resources = openepd_epd.get('resource_uses', {}) or {}
    
    # Start with EC3 resources, add openEPD resources that don't exist in EC3
    merged_resources = ec3_resources.copy()
    for key, value in openepd_resources.items():
        if key not in merged_resources or not merged_resources[key]:
            merged_resources[key] = value
    
    merged_epd['resource_uses'] = merged_resources if merged_resources else {}
    
    # Add metadata about data sources
    merged_epd['_data_sources'] = {
        'ec3': True,
        'openepd': openepd_epd is not None,
        'merged_impacts': len(merged_impacts) > len(ec3_impacts),
        'merged_resources': len(merged_resources) > len(ec3_resources)
    }
    
    return merged_epd

def fetch_from_openepd_by_id(epd_id, authorization, max_retries=3):
    """
    Fetch a specific EPD from openEPD API by ID.
    
    Args:
        epd_id: EPD ID to fetch
        authorization: Bearer token
        max_retries: Maximum number of retry attempts
    
    Returns:
        EPD data dict or None if not found
    """
    openepd_url = "https://openepd.buildingtransparency.org/api/epds"
    headers = {
        "accept": "application/json",
        "Authorization": authorization
    }
    
    # Try to fetch by searching through pages
    # Note: openEPD API may not support direct ID lookup, so we search
    for page in range(1, 11):  # Search first 10 pages
        params = {"page_size": 100, "page_number": page}
        
        for attempt in range(max_retries):
            try:
                response = requests.get(openepd_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    epds = response.json()
                    
                    # Search for matching ID
                    for epd in epds:
                        if (epd.get('id') == epd_id or 
                            epd.get('material_id') == epd_id or
                            epd.get('open_xpd_uuid') == epd_id):
                            return epd
                    
                    # If no matches and we got fewer results than page_size, we've reached the end
                    if len(epds) < params['page_size']:
                        return None
                    
                    break  # Success, move to next page
                    
                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    wait_time = 2 ** attempt + 5
                    time.sleep(wait_time)
                else:
                    break  # Other error, move to next page
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + 5)
                else:
                    break
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt + 5)
                else:
                    break
        
        # Small delay between pages
        time.sleep(0.5)
    
    return None

def extract_lcia_categories(epd):
    """
    Extract LCIA impact categories from an EPD.
    Returns a dict with standardized category names.
    """
    impacts = epd.get('impacts', {}) or {}
    
    lcia_data = {}
    
    # Map various possible field names to standardized names
    category_mappings = {
        'ozone_depletion': ['ozone_depletion', 'ozone_depletion_potential', 'odp', 'ODP'],
        'acidification': ['acidification', 'acidification_potential', 'ap', 'AP'],
        'eutrophication': ['eutrophication', 'eutrophication_potential', 'ep', 'EP'],
        'photochemical_ozone': ['photochemical_ozone', 'photochemical_ozone_creation', 'pocp', 'POCP', 'smog'],
        'abiotic_resource_depletion': ['abiotic_resource', 'abiotic_resource_depletion', 'ard', 'ARD']
    }
    
    for standard_name, possible_names in category_mappings.items():
        for key in impacts.keys():
            if any(name.lower() in key.lower() for name in possible_names):
                lcia_data[standard_name] = impacts[key]
                break
    
    return lcia_data

def extract_resource_indicators(epd):
    """
    Extract resource use indicators from an EPD.
    Returns a dict with standardized indicator names.
    """
    resources = epd.get('resource_uses', {}) or {}
    
    resource_data = {}
    
    # Map various possible field names to standardized names
    indicator_mappings = {
        'primary_energy_renewable': ['renewable', 'primary_energy_renewable', 'energy_renewable'],
        'primary_energy_non_renewable': ['non_renewable', 'primary_energy_non_renewable', 'energy_non_renewable'],
        'water_use': ['water', 'water_use', 'water_consumption'],
        'waste_generation': ['waste', 'waste_generation', 'waste_output'],
        'output_flows': ['output_flows', 'output']
    }
    
    for standard_name, possible_names in indicator_mappings.items():
        for key in resources.keys():
            if any(name.lower() in key.lower() for name in possible_names):
                resource_data[standard_name] = resources[key]
                break
    
    return resource_data

def should_fetch_from_openepd(ec3_epd):
    """
    Determine if we should fetch additional data from openEPD API.
    Returns True if EC3 data is missing impact/resource data.
    """
    impacts = ec3_epd.get('impacts', {}) or {}
    resources = ec3_epd.get('resource_uses', {}) or {}
    
    # Fetch from openEPD if impacts or resources are empty
    return len(impacts) == 0 or len(resources) == 0

