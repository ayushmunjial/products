# Used by Github Action workflow
# But looks similar to product-footprints.py
# TO DO: Get workflow working, documet how to set secret in Github 
# Change from using a token (since it expires in 3 days) to using a BuildingTransparency.org accoun email and password.

import requests
import json
import csv
import logging
import multiprocessing
import pandas as pd
import yaml
import os
import time
from functools import partial

states = ['US-GA', 'US-ME', 'US-OR']
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
    # Updated API endpoint based on the README suggestion
    url_auth = "https://buildingtransparency.org/api/rest-auth/login"
    headers_auth = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Get credentials from environment variables
    email = os.environ.get('BT_EMAIL')
    password = os.environ.get('BT_PASSWORD')
    
    if not email or not password:
        logging.error("Missing email or password environment variables")
        return None
        
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
        if hasattr(response_auth, 'json'):
            try:
                print("Response body:", response_auth.json())
            except:
                print("Response body (text):", response_auth.text)
        return None

def fetch_a_page(page: int, headers, state: str) -> list:
    logging.info(f'Fetching state: {state}, page: {page}')
    params = {"plant_geography": state, "page_size": page_size, "page_number": page}
    
    # Add retry logic with backoff
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get(epds_url, headers=headers, params=params)
            if response.status_code == 200:
                data = json.loads(response.text)
                # Debug: Print first item structure
                if data and page == 1:
                    logging.debug(f"Sample data structure: {json.dumps(data[0], indent=2)}")
                return data
            elif response.status_code == 429:  # Rate limiting
                wait_time = min(2 ** attempt + 1, 30)  # Exponential backoff with 30s max
                logging.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log_error(response.status_code, str(response.text))
                return []
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")
            time.sleep(min(2 ** attempt + 1, 30))
    
    return []  # Return empty list if all attempts fail

def fetch_epds(state: str, authorization) -> list:
    params = {"plant_geography": state, "page_size": page_size}
    headers = {"accept": "application/json", "Authorization": authorization}

    try:
        response = requests.get(epds_url, headers=headers, params=params)
        if response.status_code != 200:
            log_error(response.status_code, str(response.text))
            return []
            
        total_pages = int(response.headers.get('X-Total-Pages', 1))
        print(f"Found {total_pages} pages for {state}")
        
        # For better reliability, use sequential fetching with delay instead of multiprocessing
        all_responses = []
        for page in range(1, total_pages + 1):
            page_data = fetch_a_page(page, headers, state)
            all_responses.extend(page_data)
            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)
            
        return all_responses
    except Exception as e:
        logging.error(f"Error fetching EPDs for {state}: {str(e)}")
        return []

def remove_null_values(data):
    """Recursively remove keys with None values from a dictionary."""
    if isinstance(data, list):
        return [remove_null_values(item) for item in data if item is not None]
    elif isinstance(data, dict):
        return {k: remove_null_values(v) for k, v in data.items() if v is not None}
    return data

def get_zipcode_from_epd(epd):
    """Extract the ZIP code, prioritizing plant_or_group/postal_code, then manufacturer/postal_code."""
    # Debug log to check the structure
    if 'plant_or_group' in epd:
        logging.debug(f"Plant or group data: {epd['plant_or_group']}")
    
    zipcode = None
    if epd.get('plant_or_group') and isinstance(epd['plant_or_group'], dict):
        zipcode = epd['plant_or_group'].get('postal_code')
    
    if not zipcode and epd.get('manufacturer') and isinstance(epd['manufacturer'], dict):
        zipcode = epd['manufacturer'].get('postal_code')
    
    # Log what we found
    logging.debug(f"Found zipcode: {zipcode}")
    return zipcode

def create_folder_path(state, zipcode, display_name):
    """Create a folder path based on the ZIP code and category display name."""
    state_code = state.split('-')[1]  # Extract state code from 'US-XX'
    
    # Default path if we don't have valid data
    default_path = os.path.join("US", state_code)
    
    # Handle display name
    if not display_name or display_name == 'unknown':
        display_name_path = "uncategorized"
    else:
        display_name_path = display_name.replace(" ", "_")
    
    # Handle zipcode
    if zipcode and isinstance(zipcode, str) and len(zipcode) >= 5:
        return os.path.join("US", state_code, zipcode[:2], zipcode[2:], display_name_path)
    else:
        return os.path.join(default_path, "no_zipcode", display_name_path)

def save_json_to_yaml(state: str, json_data: list):
    """Save JSON data to YAML files in the appropriate directory structure."""
    # Clean the JSON data by removing any null values
    filtered_data = remove_null_values(json_data)
    
    print(f"Processing {len(filtered_data)} records for {state}")
    
    # Debug - log first item structure
    if filtered_data:
        logging.debug(f"First record structure: {json.dumps(filtered_data[0], indent=2)}")
    
    for epd in filtered_data:
        try:
            # Extract the needed information from the EPD record
            category_info = epd.get('category', {})
            if not isinstance(category_info, dict):
                category_info = {}
                
            display_name = category_info.get('display_name')
            if display_name:
                display_name = display_name.replace(" ", "_")
            else:
                display_name = "uncategorized"
                
            material_id = epd.get('material_id')
            if not material_id:
                # Use open_xpd_uuid as fallback
                material_id = epd.get('open_xpd_uuid')
                
            if not material_id:
                logging.warning(f"No material_id or open_xpd_uuid found, using 'unknown': {epd}")
                material_id = "unknown"
            
            zipcode = get_zipcode_from_epd(epd)
            
            # Create the folder path based on state, zipcode, and display name
            folder_path = create_folder_path(state, zipcode, display_name)
            
            # Create the folder path if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)
            
            # Create a file path for the YAML file
            file_path = os.path.join(folder_path, f"{material_id}.yaml")
            
            # Save the EPD data to a YAML file
            with open(file_path, "w") as yaml_file:
                yaml.dump(epd, yaml_file, default_flow_style=False)
                
        except Exception as e:
            logging.error(f"Error saving YAML for EPD: {str(e)}")
            continue

def map_response(epd: dict) -> dict:
    try:
        # Debug log the structure
        if isinstance(epd, dict):
            category_info = epd.get('category', {})
            if not isinstance(category_info, dict):
                category_info = {}
                
            plant_info = epd.get('plant_or_group', {})
            if not isinstance(plant_info, dict):
                plant_info = {}
        
            dict_attributes = {
                'Category_epd_name': category_info.get('openepd_name', ''),
                'Name': epd.get('name', ''),
                'ID': epd.get('open_xpd_uuid', ''),
                'Zip': plant_info.get('postal_code', ''),
                'County': plant_info.get('admin_district2', ''),
                'Address': plant_info.get('address', ''),
                'Latitude': plant_info.get('latitude', ''),
                'Longitude': plant_info.get('longitude', '')
            }
            return dict_attributes
        else:
            logging.error(f"EPD is not a dictionary: {type(epd)}")
            return {}
    except Exception as e:
        logging.error(f"Error mapping EPD: {str(e)}")
        return {}

def write_csv_others(title: str, epds: list):
    if not epds:
        logging.warning(f"No data for {title}, skipping CSV creation")
        return
        
    try:
        # Create directory if it doesn't exist
        os.makedirs("US", exist_ok=True)
        
        file_path = os.path.join("US", f"{title}.csv")
        
        # Debug log the data
        logging.debug(f"Sample data for {title}: {epds[0] if epds else 'No data'}")
        
        new_data = pd.DataFrame(epds)
        
        try:
            if os.path.exists(file_path):
                existing_data = pd.read_csv(file_path)
                if new_data.equals(existing_data):
                    logging.info(f"No changes for {title}, skipping update")
                    return
        except Exception as e:
            logging.warning(f"Could not compare with existing file: {str(e)}")
        
        # Check if DataFrame is empty
        if new_data.empty:
            logging.warning(f"DataFrame for {title} is empty, not writing CSV")
            return
            
        # Write to CSV
        new_data.to_csv(file_path, index=False)
        logging.info(f"Updated {file_path} with {len(new_data)} records")
        
    except Exception as e:
        logging.error(f"Error writing CSV for {title}: {str(e)}")

def write_csv_cement(epds: list):
    if not epds:
        logging.warning("No cement data, skipping CSV creation")
        return
        
    try:
        # Create directory if it doesn't exist
        os.makedirs("US", exist_ok=True)
        
        file_path = os.path.join("US", "Cement.csv")
        
        # Debug log the data
        logging.debug(f"Sample cement data: {epds[0] if epds else 'No data'}")
        
        new_data = pd.DataFrame(epds)
        
        # Check if DataFrame is empty
        if new_data.empty:
            logging.warning(f"Cement DataFrame is empty, not writing CSV")
            return
        
        # Check if file exists and if there are changes
        if os.path.exists(file_path):
            try:
                existing_data = pd.read_csv(file_path)
                # Combine existing and new data, removing duplicates
                combined_data = pd.concat([existing_data, new_data]).drop_duplicates(subset=['ID']).reset_index(drop=True)
                combined_data.to_csv(file_path, index=False)
                logging.info(f"Updated {file_path} with {len(combined_data)} records")
            except Exception as e:
                logging.warning(f"Error with existing file, overwriting: {str(e)}")
                new_data.to_csv(file_path, index=False)
        else:
            new_data.to_csv(file_path, index=False)
            logging.info(f"Created {file_path} with {len(new_data)} records")
            
    except Exception as e:
        logging.error(f"Error writing cement CSV: {str(e)}")

def write_epd_to_csv(epds: list, state: str):
    state_code = state.split('-')[1]  # Extract state code from 'US-XX'
    
    cement_list = []
    others_list = []
    
    for epd in epds:
        if not epd or not isinstance(epd, dict):
            logging.warning(f"Skipping invalid EPD: {epd}")
            continue
            
        try:
            category_name = epd.get('Category_epd_name', '').lower()
            if category_name and 'cement' in category_name:
                cement_list.append(epd)
            else:
                others_list.append(epd)
        except Exception as e:
            logging.error(f"Error processing EPD for CSV: {str(e)}")
    
    write_csv_cement(cement_list)
    write_csv_others(state_code, others_list)

if __name__ == "__main__":
    print("Starting BuildingTransparency.org data update")
    authorization = get_auth()
    if authorization:
        for state in states:
            try:
                print(f"Processing state: {state}")
                raw_results = fetch_epds(state, authorization)
                if raw_results:
                    print(f"Got {len(raw_results)} results for {state}")
                    
                    # Debug log raw data structure
                    if raw_results:
                        logging.debug(f"Sample raw data: {json.dumps(raw_results[0], indent=2)}")
                    
                    # Save full response to YAML files with directory structure
                    save_json_to_yaml(state, raw_results)
                    
                    # Map response for CSV files
                    mapped_results = [map_response(epd) for epd in raw_results]
                    
                    # Remove empty dictionaries
                    mapped_results = [r for r in mapped_results if r]
                    
                    write_epd_to_csv(mapped_results, state)
                else:
                    print(f"No results for {state}")
            except Exception as e:
                logging.error(f"Error processing state {state}: {str(e)}")
    else:
        print("Authorization failed, exiting...")
        exit(1)
    
    print("Data update completed")