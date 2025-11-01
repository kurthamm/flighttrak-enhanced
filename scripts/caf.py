import re
import json
import requests
import time

# Define patterns for tail numbers and ICAO hex codes
tail_number_pattern = r'^[A-Z]-?\d{1,5}$|^N\d{1,5}[A-Z]{0,2}$'
icao_hex_pattern = r'^[0-9A-F]{6}$'

# Load config from config.json
def load_config():
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
    return config

# Function to check if the aircraft is blocked from tracking
def check_blocked_status(tail_number, config):
    flightaware_config = config["flightaware_config"]
    api_key = flightaware_config["flightaware_api_key"]

    url = f"https://aeroapi.flightaware.com/aeroapi/aircraft/{tail_number}/blocked"
    headers = {'x-apikey': api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        is_blocked = data.get("blocked", False)
        print(f"Blocked status for {tail_number}: {is_blocked}")
        return is_blocked
    except requests.RequestException as e:
        print(f"Error fetching blocked status for {tail_number}: {e}")
        return None

# Function to get owner information
def lookup_owner(tail_number, config):
    flightaware_config = config["flightaware_config"]
    api_key = flightaware_config["flightaware_api_key"]

    url = f"https://aeroapi.flightaware.com/aeroapi/aircraft/{tail_number}/owner"
    headers = {'x-apikey': api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        data = response.json()
        owner_info = data.get("owner", {})
        print(f"Owner information for {tail_number}: {owner_info}")
        return owner_info
    except requests.RequestException as e:
        print(f"Error fetching owner information for {tail_number}: {e}")
        return None

# Function to perform the lookup of ICAO hex code based on the tail number using TailOwner API
def lookup_icao_hex(tail_number, config, retries=3, delay=10):
    flightaware_config = config["flightaware_config"]
    api_key = flightaware_config["flightaware_api_key"]

    print(f"Looking up ICAO hex code for tail number: {tail_number}")

    url = f"https://aeroapi.flightaware.com/aeroapi/aircraft/{tail_number}"

    headers = {
        'x-apikey': api_key
    }

    try:
        for attempt in range(retries):
            response = requests.get(url, headers=headers)

            print(f"API Response Status Code: {response.status_code}")
            if response.status_code == 429:
                print(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)  # Wait before retrying
                continue

            response.raise_for_status()  # Raise an error for other bad responses

            # Convert the response to JSON
            data = response.json()

            if "icao24" in data:
                icao_hex = data["icao24"]
                owner = data.get("registered_owner", "Unknown")
                print(f"Found ICAO hex: {icao_hex} for tail number: {tail_number}")
                return icao_hex, owner
            else:
                print(f"No ICAO hex code found for tail number: {tail_number}")
                return None, None
        else:
            print(f"Max retries hit for tail number {tail_number}.")
            return None, None
    except requests.RequestException as e:
        print(f"Error fetching ICAO hex code: {e}")
        return None, None

# Function to validate and correct the aircraft file
def validate_and_correct_aircraft_file(config):
    # Load the aircraft JSON file path from config
    aircraft_file_path = config["aircraft_file_path"]

    # Load the JSON file
    with open(aircraft_file_path, 'r') as file:
        aircraft_list = json.load(file)

    updated = False

    # Iterate through each aircraft entry
    for aircraft in aircraft_list["aircraft_to_detect"]:
        icao = aircraft["icao"]

        # Check if the ICAO field is actually a tail number by matching the tail number pattern
        if re.match(tail_number_pattern, icao):
            print(f"Detected tail number instead of ICAO hex code: {icao}")

            # Check if the aircraft is blocked
            is_blocked = check_blocked_status(icao, config)
            if is_blocked:
                print(f"Skipping {icao} as it is blocked.")
                continue

            # Lookup the correct ICAO hex code and owner
            icao_hex, owner = lookup_icao_hex(icao, config)

            # Replace the tail number with the ICAO hex code
            if icao_hex and re.match(icao_hex_pattern, icao_hex):
                print(f"Replacing tail number {icao} with ICAO hex code {icao_hex}")
                aircraft["icao"] = icao_hex
                if owner:
                    aircraft["owner"] = owner
                updated = True
            else:
                print(f"Failed to retrieve valid ICAO hex code for {icao}")

    # If any changes were made, overwrite the file
    if updated:
        with open(aircraft_file_path, 'w') as file:
            json.dump(aircraft_list, file, indent=4)
        print("Aircraft file has been updated.")
    else:
        print("No updates made to the aircraft file.")

# Main execution
def main():
    # Load config
    config = load_config()

    # Validate and correct the aircraft file
    validate_and_correct_aircraft_file(config)

if __name__ == "__main__":
    main()
