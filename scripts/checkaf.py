import re
import json

# Define the regex pattern for tail numbers
tail_number_pattern = r'^[A-Z]-?\d{1,5}$|^N\d{1,5}[A-Z]{0,2}$'

# Load the aircraft list from the JSON file
def load_aircraft_list(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Function to identify tail numbers
def find_tail_numbers(aircraft_list):
    tail_numbers = []
    
    for aircraft in aircraft_list["aircraft_to_detect"]:
        icao = aircraft["icao"]
        if re.match(tail_number_pattern, icao):
            tail_numbers.append(icao)

    return tail_numbers

# Main function to validate aircraft list and print tail numbers
def main():
    # Path to your aircraft_list.json file
    aircraft_file_path = "aircraft_list.json"
    
    # Load the aircraft list
    aircraft_list = load_aircraft_list(aircraft_file_path)
    
    # Find tail numbers
    tail_numbers = find_tail_numbers(aircraft_list)
    
    # Print the tail numbers found
    if tail_numbers:
        print("The following entries are tail numbers:")
        for tail_number in tail_numbers:
            print(f"Tail number: {tail_number}")
    else:
        print("No tail numbers found. All entries seem to be ICAO hex codes.")

if __name__ == "__main__":
    main()

