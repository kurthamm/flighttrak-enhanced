#!/usr/bin/env python3
"""Debug script to check what the monitor is seeing"""

import requests
import json
from config_manager import config
from utils import load_json_config

# Get aircraft data
planes_url = config.get('monitoring.planes_url')
print(f"Fetching from: {planes_url}")

try:
    response = requests.get(planes_url, timeout=10)
    response.raise_for_status()
    data = response.json()
    aircraft_list = data.get('aircraft', [])
    print(f"\n✓ Successfully fetched {len(aircraft_list)} aircraft")
except Exception as e:
    print(f"\n✗ Error fetching data: {e}")
    exit(1)

# Load tracked aircraft
aircraft_file = config.get('files.aircraft_list')
aircraft_data = load_json_config(str(aircraft_file))
tracked_aircraft = {
    aircraft['icao'].upper(): aircraft
    for aircraft in aircraft_data.get('aircraft_to_detect', [])
}
print(f"✓ Loaded {len(tracked_aircraft)} tracked aircraft")

# Check for matches
print("\n=== Checking for tracked aircraft ===")
matches = []
for aircraft in aircraft_list:
    icao = aircraft.get('hex', '').upper()
    if icao in tracked_aircraft:
        matches.append((icao, aircraft, tracked_aircraft[icao]))
        print(f"\n✓ MATCH FOUND: {icao}")
        print(f"  Tail: {tracked_aircraft[icao].get('tail_number')}")
        print(f"  Owner: {tracked_aircraft[icao].get('owner')}")
        print(f"  Flight: {aircraft.get('flight', 'N/A')}")
        print(f"  Alt: {aircraft.get('alt_baro', 'N/A')} ft")
        print(f"  Lat/Lon: {aircraft.get('lat')}, {aircraft.get('lon')}")

if not matches:
    print("✗ No tracked aircraft currently visible")
    # Show a sample of what we ARE seeing
    print("\n=== Sample of visible aircraft (first 5) ===")
    for ac in aircraft_list[:5]:
        print(f"  {ac.get('hex', 'unknown').upper()}: flight={ac.get('flight', 'N/A')}")
else:
    print(f"\n✓ Found {len(matches)} tracked aircraft!")

# Check alert configuration
print("\n=== Alert Configuration ===")
print(f"Tracked alerts enabled: {config.is_alert_enabled('tracked_aircraft')}")
recipients = config.get_alert_recipients('tracked_aircraft')
print(f"Recipients: {recipients} ({len(recipients)} total)")
