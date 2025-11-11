import requests, json, csv, logging, yaml, time, os
from functools import partial
from myconfig import email, password

# ✅ Pull only for Maine (US-ME) and India (IN)
states = ['US-ME', 'IN']

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
        print("Fetched the new token successfully")
        return authorization
    else:
        print(f"Failed to login. Status code: {response_auth.status_code}")
        print("Response body:" + str(response_auth.json()))
        return None

def fetch_a_page(page: int, headers, state: str) -> list:
    logging.info(f'Fetching state: {state}, page: {page}')
    params = {"plant_geography": state, "page_size": page_size, "page_number": page}
    for attempt in range(5):
        response = requests.get(epds_url, headers=headers, params=params)
        if response.status_code == 200:
            return json.loads(response.text)
        elif response.status_code == 429:
            log_error(response.status_code, "Rate limit exceeded. Retrying...")
            time.sleep(2 ** attempt + 5)
        else:
            log_error(response.status_code, str(response.json()))
            return []
    return []

def fetch_epds(state: str, authorization) -> list:
    params = {"plant_geography": state, "page_size": page_size}
    headers = {"accept": "application/json", "Authorization": authorization}
    response = requests.get(epds_url, headers=headers, params=params)
    if response.status_code != 200:
        log_error(response.status_code, str(response.json()))
        return []
    total_pages = int(response.headers['X-Total-Pages'])
    full_response = []
    for page in range(1, total_pages + 1):
        page_data = fetch_a_page(page, headers, state)
        full_response.extend(page_data)
        time.sleep(1)
    time.sleep(10)
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
    # For India, organize strictly by category under 'IN/<category>'
    if state == 'IN':
        return os.path.join(base_root, 'IN', display_name)
    # Default (e.g., US states): organize by state and zipcode buckets
    base_path = os.path.join(base_root, state)
    if zipcode and len(zipcode) >= 5:
        return os.path.join(base_path, zipcode[:2], zipcode[2:], display_name)
    else:
        return os.path.join(base_path, "unknown", display_name)

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

# Tariff highlights for India: feature specific categories and annotate tariff rates
def write_tariff_highlights(raw_epds: list, state: str):
    if state != 'IN' or not raw_epds:
        # Ensure directory and empty CSV exist for downstream expectations
        try:
            os.makedirs(os.path.join("../../products-data", 'IN'), exist_ok=True)
            out_path = os.path.join("../../products-data", 'IN', 'tariff_highlights.csv')
            if not os.path.exists(out_path):
                with open(out_path, 'w') as f:
                    writer = csv.DictWriter(f, fieldnames=['Category','Name','ID','TariffPercent','Zip','Address','Latitude','Longitude'])
                    writer.writeheader()
        except Exception:
            pass
        return
    try:
        highlights = []
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
                
                # Search in category name, product name, and description
                search_text = f"{display_name} {product_name} {product_description}".lower()
                
                matched_tariff = None
                matched_keyword = None
                for kw, rate in keyword_to_tariff.items():
                    if kw in search_text:
                        matched_tariff = rate
                        matched_keyword = kw
                        break
                
                if matched_tariff is None:
                    continue
                    
                plant = epd.get('plant_or_group', {}) if isinstance(epd, dict) else {}
                highlights.append({
                    'Category': f"{display_name} (matched: {matched_keyword})",
                    'Name': product_name,
                    'ID': epd.get('open_xpd_uuid', ''),
                    'TariffPercent': matched_tariff,
                    'Zip': plant.get('postal_code', ''),
                    'Address': plant.get('address', ''),
                    'Latitude': plant.get('latitude', ''),
                    'Longitude': plant.get('longitude', ''),
                })
            except Exception:
                continue
        os.makedirs(os.path.join("../../products-data", 'IN'), exist_ok=True)
        out_path = os.path.join("../../products-data", 'IN', 'tariff_highlights.csv')
        with open(out_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['Category','Name','ID','TariffPercent','Zip','Address','Latitude','Longitude'])
            writer.writeheader()
            for row in highlights:
                writer.writerow(row)
    except Exception:
        pass

# ✅ MAIN SCRIPT
if __name__ == "__main__":
    authorization = get_auth()
    if authorization:
        for state in states:
            print(f"Fetching and processing: {state}")
            results = fetch_epds(state, authorization)
            save_json_to_yaml(state, results)
            # Create a tariff highlights CSV for IN based on specified categories
            write_tariff_highlights(results, state)
            mapped_results = [map_response(epd) for epd in results]
            write_epd_to_csv(mapped_results, state)
