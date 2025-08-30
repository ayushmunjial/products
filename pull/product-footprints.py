import requests, json, csv, logging, multiprocessing, yaml, time, os
from functools import partial
from myconfig import email, password

states = ['US-GA', 'US-ME', 'US-OR']
# states = [
#     'US-AL', 'US-AK', 'US-AZ', 'US-AR', 'US-CA', 'US-CO', 'US-CT', 'US-DE', 'US-FL', 'US-GA',
#     'US-HI', 'US-ID', 'US-IL', 'US-IN', 'US-IA', 'US-KS', 'US-KY', 'US-LA', 'US-ME', 'US-MD',
#     'US-MA', 'US-MI', 'US-MN', 'US-MS', 'US-MO', 'US-MT', 'US-NE', 'US-NV', 'US-NH', 'US-NJ',
#     'US-NM', 'US-NY', 'US-NC', 'US-ND', 'US-OH', 'US-OK', 'US-OR', 'US-PA', 'US-RI', 'US-SC',
#     'US-SD', 'US-TN', 'US-TX', 'US-UT', 'US-VT', 'US-VA', 'US-WA', 'US-WV', 'US-WI', 'US-WY'
# ]

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
    #url_auth = "https://etl-api.cqd.io/api/rest-auth/login"
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
        print("Response body:" + response_auth.json())
        return None

def fetch_a_page(page: int, headers, state: str) -> list:
    logging.info(f'Fetching state: {state}, page: {page}')
    params = {"plant_geography": state, "page_size": page_size, "page_number": page}

    for attempt in range(5):  # Retry up to 5 times
        response = requests.get(epds_url, headers=headers, params=params)
        if response.status_code == 200:
            return json.loads(response.text)
        elif response.status_code == 429:
            log_error(response.status_code, "Rate limit exceeded. Retrying...")
            time.sleep(2 ** attempt + 5)  # Increased delay and added a base delay of 5 seconds
        else:
            log_error(response.status_code, str(response.json()))
            return []

    return []  # Return empty list if all attempts fail

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
        time.sleep(1)  # Small delay to avoid rate limiting

    time.sleep(10)  # Added delay between state fetches to avoid rate limiting
    return full_response

def remove_null_values(data):
    """Recursively remove keys with None values from a dictionary."""
    if isinstance(data, list):
        # Recursively clean each item in the list.
        return [remove_null_values(item) for item in data if item is not None]
    elif isinstance(data, dict):
        # Recursively clean each key-value pair in the dictionary.
        return {k: remove_null_values(v) for k, v in data.items() if v is not None}
    return data

def get_zipcode_from_epd(epd):
    """Extract the ZIP code, prioritizing manufacturer/postal_code, then plant_or_group/postal_code."""
    zipcode = epd.get('manufacturer', {}).get('postal_code') # get the ZIP code from the manufacturer details.
    if not zipcode:
        zipcode = epd.get('plant_or_group', {}).get('postal_code')
    return zipcode

def create_folder_path(state, zipcode, display_name):
    """Create a folder path based on the ZIP code and category display name."""
    if len(zipcode) >= 5:
        return os.path.join("US", state, zipcode[:2], zipcode[2:], display_name)
    else:
        return os.path.join("US", state, "unknown", display_name)

'''Function to save JSON data to a YAML file in the corresponding folder path'''
def save_json_to_yaml(state: str, json_data: list):
    # Clean the JSON data by removing any null values.
    filtered_data = remove_null_values(json_data)

    # Loop through each EPD record in the filtered data.
    for epd in filtered_data:
        # Get the Display Name from Category
        display_name = epd['category']['display_name'].replace(" ", "_")
        # Extract the material ID from the EPD record.
        material_id = epd['material_id']

        zipcode = get_zipcode_from_epd(epd)
        if zipcode: # If a valid ZIP code is found:
            # Create the folder path based on the state, ZIP code, and display name.
            folder_path = create_folder_path(state, zipcode, display_name)
        else:
            # If no valid ZIP code is found, use a default folder path.
            folder_path = os.path.join("US", state, "unknown", display_name)

        # Create the folder path if it doesn't exist.
        os.makedirs(folder_path, exist_ok=True)
        # Create a file path for the YAML file.
        file_path = os.path.join(folder_path, f"{material_id}.yaml")

        with open(file_path, "w") as yaml_file:
            yaml.dump(epd, yaml_file, default_flow_style=False)

def map_response(epd: dict) -> dict:
    dict_attributes = {
        'Category_epd_name': epd['category']['openepd_name'],
        'Name': epd['name'],
        'ID': epd['open_xpd_uuid'],
        'Zip': epd['plant_or_group'].get('postal_code', None),
        'County': epd['plant_or_group'].get('admin_district2', None),
        'Address': epd['plant_or_group'].get('address', None),
        'Latitude': epd['plant_or_group'].get('latitude', None),
        'Longitude': epd['plant_or_group'].get('longitude', None)
    }
    return dict_attributes

def write_csv_others(title: str, epds: list):
    with open(f"{title}.csv", "w") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Name", "ID", "Zip", "County", "Address", "Latitude", "Longitude"])
        for epd in epds:
            writer.writerow([epd['Name'], epd['ID'], epd['Zip'], epd['County'], epd['Address'], epd['Latitude'], epd['Longitude']])

def write_csv_cement(epds: list):
    with open("Cement.csv", "a") as csv_file:
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

if __name__ == "__main__":
    authorization = get_auth()
    if authorization:
        for state in states:
            results = fetch_epds(state, authorization)
            save_json_to_yaml(state, results)  # Save full JSON response to YAML
            mapped_results = [map_response(epd) for epd in results]
            write_epd_to_csv(mapped_results, state)  # Write the mapped response to CSV