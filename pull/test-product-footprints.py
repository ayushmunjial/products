"""
Test script for product-footprints.py
Tests with a small subset of regions before running the full script.
"""
import requests, json, csv, logging, multiprocessing, yaml, time, os
from functools import partial
from myconfig import email, password

# ✅ TEST: Use only a few regions for quick testing
# Test with: US-ME (known to have data), US-CA (large state), IN (India), GB (Great Britain)
states = ['US-ME', 'US-CA', 'IN', 'GB']

epds_url = "https://buildingtransparency.org/api/epds"
page_size = 250

logging.basicConfig(
    level=logging.DEBUG,
    filename="test_output.log",
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
                    print(f"  Progress: {page}/{total_pages} pages fetched for {state}")
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
    response = requests.get(epds_url, headers=headers, params=params)
    if response.status_code != 200:
        log_error(response.status_code, str(response.json()))
        print(f"No data found for {state} (status: {response.status_code})")
        return []
    # Handle case where X-Total-Pages header might be missing
    total_pages = int(response.headers.get('X-Total-Pages', 0))
    if total_pages == 0:
        print(f"No data found for {state}")
        return []
    print(f"Found {total_pages} pages for {state}")
    full_response = []
    start_time = time.time()
    for page in range(1, total_pages + 1):
        page_data = fetch_a_page(page, headers, state, total_pages)
        if page_data:
            full_response.extend(page_data)
        else:
            print(f"  Warning: No data returned for page {page}, continuing...")
        # Only sleep if not the last page
        if page < total_pages:
            time.sleep(1)
    elapsed_time = time.time() - start_time
    time.sleep(10)
    print(f"Fetched {len(full_response)} EPDs for {state} in {elapsed_time:.1f} seconds")
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
    os.makedirs("../../products-data", exist_ok=True)
    with open("../../products-data/Cement.csv", "a") as csv_file:
        writer = csv.writer(csv_file)
        for epd in epds:
            writer.writerow([epd['Name'], epd['ID'], epd['Zip'], epd['County'], epd['Address'], epd['Latitude'], epd['Longitude']])

def write_epd_to_csv(epds: list, state: str):
    cement_list = []
    others_list = []
    for epd in epds:
        if epd is None:
            continue
        category_name = epd['Category_epd_name'].lower()
        if 'cement' in category_name:
            cement_list.append(epd)
        else:
            others_list.append(epd)
    write_csv_cement(cement_list)
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

# ✅ TEST SCRIPT MAIN
if __name__ == "__main__":
    print("=" * 60)
    print("TEST MODE: Running with limited regions")
    print(f"Testing regions: {states}")
    print("=" * 60)
    
    authorization = get_auth()
    if authorization:
        total_regions = len(states)
        for idx, state in enumerate(states, 1):
            print(f"\n[{idx}/{total_regions}] Fetching and processing: {state}")
            results = fetch_epds(state, authorization)
            if results:
                save_json_to_yaml(state, results)
                # Create products CSV for IN with region mapping and tariff rates
                write_products_csv(results, state)
                mapped_results = [map_response(epd) for epd in results]
                write_epd_to_csv(mapped_results, state)
                print(f"✓ Completed {state}: {len(results)} EPDs saved")
            else:
                print(f"⚠ Skipped {state}: No data available")
        print(f"\n✓ All test regions processed!")
        print("\nNext step: Check the output in products-data/ folder")
    else:
        print("Failed to authenticate. Please check credentials in myconfig.py")

