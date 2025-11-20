import requests, json, csv, logging, yaml, time, os
from functools import partial
from myconfig import email, password

# ✅ Pull for all US states and selected countries
# All US states (50 states + DC)
us_states = [
    'US-AL', 'US-AK', 'US-AZ', 'US-AR', 'US-CA', 'US-CO', 'US-CT', 'US-DE', 'US-FL', 'US-GA',
    'US-HI', 'US-ID', 'US-IL', 'US-IN', 'US-IA', 'US-KS', 'US-KY', 'US-LA', 'US-ME', 'US-MD',
    'US-MA', 'US-MI', 'US-MN', 'US-MS', 'US-MO', 'US-MT', 'US-NE', 'US-NV', 'US-NH', 'US-NJ',
    'US-NM', 'US-NY', 'US-NC', 'US-ND', 'US-OH', 'US-OK', 'US-OR', 'US-PA', 'US-RI', 'US-SC',
    'US-SD', 'US-TN', 'US-TX', 'US-UT', 'US-VT', 'US-VA', 'US-WA', 'US-WV', 'US-WI', 'US-WY',
    'US-DC'
]

# Additional countries
countries = ['IN', 'GB', 'DE', 'NL', 'CA', 'MX', 'CN']

# Combine all regions
states = us_states + countries

epds_url = "https://buildingtransparency.org/api/epds"
page_size = 250

logging.basicConfig(
    level=logging.DEBUG,
    filename="output.log",
    datefmt="%Y/%m/%d %H:%M:%S",
    format="%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(module)s - %(message)s",
)
logger = logging.getLogger(__name__)

def log_error(status_code: int, response_body: str):
    logging.error(f"Request failed with status code: {status_code}")
    logging.debug("Response body:" + response_body)

def get_auth():
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
        print("Fetched the new token successfully", flush=True)
        return authorization
    else:
        print(f"Failed to login. Status code: {response_auth.status_code}")
        print("Response body:" + str(response_auth.json()))
        return None

def fetch_a_page(page: int, headers, state: str, total_pages: int = 0) -> list:
    logging.info(f'Fetching state: {state}, page: {page}')
    params = {"plant_geography": state, "page_size": page_size, "page_number": page}
    for attempt in range(5):
        try:
            # Add timeout to prevent hanging (30 seconds per request)
            response = requests.get(epds_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = json.loads(response.text)
                # Show progress for large datasets
                if total_pages > 10 and page % 10 == 0:
                    print(f"  Progress: {page}/{total_pages} pages fetched for {state}", flush=True)
                return data
            elif response.status_code == 429:
                log_error(response.status_code, "Rate limit exceeded. Retrying...")
                time.sleep(2 ** attempt + 5)
            else:
                log_error(response.status_code, str(response.json()))
                return []
        except requests.exceptions.Timeout:
            log_error(0, f"Request timeout for {state}, page {page}. Retrying...")
            time.sleep(2 ** attempt + 5)
        except requests.exceptions.RequestException as e:
            log_error(0, f"Request error for {state}, page {page}: {str(e)}. Retrying...")
            time.sleep(2 ** attempt + 5)
    return []

def fetch_epds(state: str, authorization) -> list:
    params = {"plant_geography": state, "page_size": page_size}
    headers = {"accept": "application/json", "Authorization": authorization}
    try:
        # Add timeout to initial request
        response = requests.get(epds_url, headers=headers, params=params, timeout=30)
    except requests.exceptions.Timeout:
        print(f"Timeout fetching initial data for {state}. Skipping...", flush=True)
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error for {state}: {str(e)}. Skipping...", flush=True)
        return []
    
    if response.status_code != 200:
        log_error(response.status_code, str(response.json()))
        print(f"No data found for {state} (status: {response.status_code})", flush=True)
        return []
    # Handle case where X-Total-Pages header might be missing
    total_pages = int(response.headers.get('X-Total-Pages', 0))
    if total_pages == 0:
        print(f"No data found for {state}", flush=True)
        return []
    print(f"Found {total_pages} pages for {state}", flush=True)
    full_response = []
    start_time = time.time()
    for page in range(1, total_pages + 1):
        page_data = fetch_a_page(page, headers, state, total_pages)
        if page_data:
            full_response.extend(page_data)
        else:
            print(f"  Warning: No data returned for page {page}, continuing...", flush=True)
        # Only sleep if not the last page
        if page < total_pages:
            time.sleep(1)
    elapsed_time = time.time() - start_time
    time.sleep(10)
    print(f"Fetched {len(full_response)} EPDs for {state} in {elapsed_time:.1f} seconds", flush=True)
    return full_response

def remove_null_values(data):
    if isinstance(data, list):
        return [remove_null_values(item) for item in data if item is not None]
    elif isinstance(data, dict):
        return {k: remove_null_values(v) for k, v in data.items() if v is not None}
    return data

def get_zipcode_from_epd(epd):
    zipcode = epd.get('manufacturer', {}).get('postal_code')
    if not zipcode:
        zipcode = epd.get('plant_or_group', {}).get('postal_code')
    return zipcode

# ✅ Output to products-data folder
def create_folder_path(state, zipcode, display_name):
    base_root = os.path.join("../../products-data")
    # For US states: organize by country and category (e.g., US/Cement, US/Brick)
    # Products might come from multiple states, so use category-based folders
    if state.startswith('US-'):
        return os.path.join(base_root, 'US', display_name)
    # For countries: organize by country code and category (e.g., GB/Cement, DE/Brick)
    # Countries: IN, GB, DE, NL, CA, MX, CN
    return os.path.join(base_root, state, display_name)

def save_json_to_yaml(state: str, json_data: list):
    filtered_data = remove_null_values(json_data)
    for epd in filtered_data:
        display_name = epd['category']['display_name'].replace(" ", "_")
        material_id = epd['material_id']
        zipcode = get_zipcode_from_epd(epd) or "unknown"
        folder_path = create_folder_path(state, zipcode, display_name)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"{material_id}.yaml")
        with open(file_path, "w") as yaml_file:
            yaml.dump(epd, yaml_file, default_flow_style=False)

def map_response(epd: dict) -> dict:
    return {
        'Category_epd_name': epd['category']['openepd_name'],
        'Name': epd['name'],
        'ID': epd['open_xpd_uuid'],
        'Zip': epd['plant_or_group'].get('postal_code', None),
        'County': epd['plant_or_group'].get('admin_district2', None),
        'Address': epd['plant_or_group'].get('address', None),
        'Latitude': epd['plant_or_group'].get('latitude', None),
        'Longitude': epd['plant_or_group'].get('longitude', None)
    }

def write_csv_others(title: str, epds: list):
    os.makedirs("../../products-data", exist_ok=True)
    with open(f"../../products-data/{title}.csv", "w") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Name", "ID", "Zip", "County", "Address", "Latitude", "Longitude"])
        for epd in epds:
            writer.writerow([epd['Name'], epd['ID'], epd['Zip'], epd['County'], epd['Address'], epd['Latitude'], epd['Longitude']])

def write_csv_cement(epds: list):
    """Write cement rows. Instead of a single central CSV, write per-state cement CSVs and
    save individual cement YAML files under profile/cement/US/<state>/. 

    epds: list of mapped epd dicts (output from map_response)
    """
    # Ensure base folders exist
    os.makedirs("../../products-data", exist_ok=True)
    profile_cement_base = os.path.join("..", "..", "profile", "cement", "US")
    os.makedirs(profile_cement_base, exist_ok=True)

    # Group by state (Zip field may be partial or None) - expect the caller to pass state separately
    # To support the existing call signature, if epds includes a 'State' key use that; otherwise
    # default to 'unknown'. However, product-footprints passes mapped epds and state separately
    # so higher-level caller will call write_cement_state_files per-state.
    # Here we provide a fallback append to central Cement.csv for unexpected calls.
    if not epds:
        return

    # Fallback: if a pseudo 'State' key exists on first epd, use it to write a per-state CSV
    first = epds[0]
    state = first.get('State') or first.get('Plant_State') or 'unknown'

    # Write per-state cement CSV in products-data and in profile/cement/US/<state>/Cement.csv
    state_products_data_dir = os.path.join("../../products-data", state)
    os.makedirs(state_products_data_dir, exist_ok=True)
    state_profile_dir = os.path.join(profile_cement_base, state)
    os.makedirs(state_profile_dir, exist_ok=True)

    products_data_csv = os.path.join(state_products_data_dir, 'Cement.csv')
    profile_cement_csv = os.path.join(state_profile_dir, 'Cement.csv')

    # Append rows to both CSV locations
    for csv_path in (products_data_csv, profile_cement_csv):
        write_header = not os.path.exists(csv_path)
        with open(csv_path, 'a') as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(["Name", "ID", "Zip", "County", "Address", "Latitude", "Longitude"])
            for epd in epds:
                writer.writerow([epd.get('Name',''), epd.get('ID',''), epd.get('Zip',''), epd.get('County',''), epd.get('Address',''), epd.get('Latitude',''), epd.get('Longitude','')])

    # Save individual YAMLs for each cement product under profile/cement/US/<state>/<material_id>.yaml
    try:
        # We need the original epd structured data to write YAML files. If caller passed mapped dicts only,
        # we cannot dump full EPD; in that case skip YAML save. We detect full EPD by presence of 'Category_epd_name'.
        # However our mapped epds are simple; product-footprints has access to full EPDs when calling save_json_to_yaml.
        # To keep behavior safe, attempt to write minimal YAML with available fields.
        for epd in epds:
            mat_id = epd.get('ID') or epd.get('material_id')
            if not mat_id:
                continue
            yaml_path = os.path.join(state_profile_dir, f"{mat_id}.yaml")
            # Only write if not present to avoid overwriting existing full data
            if not os.path.exists(yaml_path):
                with open(yaml_path, 'w') as yf:
                    # Dump the mapped dict as YAML (minimal)
                    yaml.dump(epd, yf, default_flow_style=False)
    except Exception:
        # Do not fail the entire process for YAML write issues
        pass

def write_epd_to_csv(epds: list, state: str):
    cement_list = []
    others_list = []
    for epd in epds:
        if epd is None:
            continue
        category_name = epd['Category_epd_name'].lower()
        if 'cement' in category_name:
            # tag with state for downstream per-state cement handling
            epd['State'] = state
            cement_list.append(epd)
        else:
            others_list.append(epd)
    # Write cement rows to per-state cement folders and CSVs
    write_csv_cement(cement_list)
    # Non-cement products remain written per-state under products-data
    write_csv_others(state, others_list)

# Products CSV for India: maps region1 (IN) to region2 (US) with category_id and tariff_percent
def write_products_csv(raw_epds: list, state: str):
    if state != 'IN' or not raw_epds:
        # Ensure directory and empty CSV exist for downstream expectations
        try:
            os.makedirs(os.path.join("../../products-data", 'IN'), exist_ok=True)
            out_path = os.path.join("../../products-data", 'IN', 'products.csv')
            if not os.path.exists(out_path):
                with open(out_path, 'w') as f:
                    writer = csv.DictWriter(f, fieldnames=['region1', 'region2', 'category_id', 'tariff_percent'])
                    writer.writeheader()
        except Exception:
            pass
        return
    try:
        products = []
        # Map keywords to tariff percentage - search in both category and product description
        keyword_to_tariff = {
            'kitchen cabinet': 50,
            'kitchen cabinets': 50,
            'bathroom vanity': 50,
            'bathroom vanities': 50,
            'upholstered furniture': 30,
            'furniture': 30,  # Broader match for furniture
            'tables': 30,     # Tables are furniture
            'wardrobes': 30,  # Found in descriptions
        }
        for epd in raw_epds:
            try:
                category_info = epd.get('category', {}) if isinstance(epd, dict) else {}
                display_name = (category_info.get('display_name') or '').strip()
                product_name = (epd.get('name') or '').strip()
                product_description = (epd.get('description') or '').strip()
                
                # Get category_id from category.id (to match EPD naming)
                category_id = category_info.get('id', '')
                
                # Search in category name, product name, and description
                search_text = f"{display_name} {product_name} {product_description}".lower()
                
                matched_tariff = None
                for kw, rate in keyword_to_tariff.items():
                    if kw in search_text:
                        matched_tariff = rate
                        break
                
                if matched_tariff is None:
                    continue
                    
                # Create product entry with new structure
                products.append({
                    'region1': 'IN',  # India
                    'region2': 'US',  # Placeholder - actual US state mapping TBD
                    'category_id': category_id,
                    'tariff_percent': matched_tariff,
                })
            except Exception:
                continue
        os.makedirs(os.path.join("../../products-data", 'IN'), exist_ok=True)
        out_path = os.path.join("../../products-data", 'IN', 'products.csv')
        with open(out_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['region1', 'region2', 'category_id', 'tariff_percent'])
            writer.writeheader()
            for row in products:
                writer.writerow(row)
    except Exception:
        pass

# ✅ MAIN SCRIPT
if __name__ == "__main__":
    authorization = get_auth()
    if authorization:
        total_regions = len(states)
        print(f"Starting processing of {total_regions} regions...", flush=True)
        for idx, state in enumerate(states, 1):
            print(f"\n[{idx}/{total_regions}] Fetching and processing: {state}", flush=True)
            results = fetch_epds(state, authorization)
            if results:
                save_json_to_yaml(state, results)
                # Create products CSV for IN with region mapping and tariff rates
                write_products_csv(results, state)
                mapped_results = [map_response(epd) for epd in results]
                write_epd_to_csv(mapped_results, state)
                print(f"✓ Completed {state}: {len(results)} EPDs saved", flush=True)
            else:
                print(f"⚠ Skipped {state}: No data available", flush=True)
        print(f"\n✓ All regions processed!", flush=True)
