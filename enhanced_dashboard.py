#!/usr/bin/env python3
"""
FlightTrak Dashboard - Real-time aircraft tracking display
Simplified dashboard focusing on aircraft positions and basic tracking stats
"""

import json
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import threading
from collections import deque, defaultdict
import math
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Configuration
PLANES_URL = "https://planes.hamm.me/data/aircraft.json"
HOME_LAT = 34.1133171
HOME_LON = -80.9024019
UPDATE_INTERVAL = 2  # seconds

# Data storage
aircraft_history = {}
stats = {
    'total_seen': 0,
    'current_count': 0,
    'max_simultaneous': 0,
    'closest_approach': float('inf'),
    'closest_aircraft': None,
    'last_update': 0,
    'updates': deque(maxlen=100)
}

# Track aircraft seen in last 24 hours
aircraft_seen_24h = deque(maxlen=1000)  # Store (hex_code, timestamp) tuples

# Track emergency squawks
emergency_events = deque(maxlen=50)

def haversine_miles(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two points"""
    R_km = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist_km = R_km * c
    return dist_km * 0.621371

def load_tracked_aircraft():
    """Load list of tracked aircraft from aircraft_list.json"""
    try:
        with open('aircraft_list.json', 'r') as f:
            data = json.load(f)
            return {a['icao'].upper(): a for a in data.get('aircraft_to_detect', [])}
    except Exception as e:
        logging.error(f"Error loading tracked aircraft: {e}")
        return {}

# Load tracked aircraft on startup
tracked_aircraft = load_tracked_aircraft()

def check_emergency_squawk(aircraft):
    """Check for emergency squawk codes"""
    squawk = aircraft.get('squawk', '')
    if squawk in ['7500', '7600', '7700', '7777']:
        emergency_types = {
            '7500': 'HIJACK',
            '7600': 'RADIO FAILURE',
            '7700': 'EMERGENCY',
            '7777': 'MILITARY INTERCEPT'
        }

        event = {
            'time': datetime.now().isoformat(),
            'timestamp': time.time(),
            'type': emergency_types[squawk],
            'squawk': squawk,
            'aircraft': aircraft.copy(),
            'hex': aircraft.get('hex', '').upper()
        }

        # Only add if not duplicate (check last 5 events)
        recent_events = list(emergency_events)[-5:]
        is_duplicate = any(
            e.get('hex') == event['hex'] and
            e.get('squawk') == event['squawk'] and
            (event['timestamp'] - e.get('timestamp', 0)) < 300  # Within 5 minutes
            for e in recent_events
        )

        if not is_duplicate:
            emergency_events.append(event)
            logging.warning(f"Emergency detected: {emergency_types[squawk]} - {aircraft.get('hex', 'Unknown')} squawking {squawk}")

def fetch_aircraft_data():
    """Fetch aircraft data from planes.hamm.me"""
    try:
        response = requests.get(PLANES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None

def update_aircraft_data():
    """Background thread to update aircraft data"""
    global stats

    while True:
        data = fetch_aircraft_data()
        if data:
            current_aircraft = {}
            aircraft_list = data.get('aircraft', [])

            for aircraft in aircraft_list:
                hex_code = aircraft.get('hex', '')
                if not hex_code:
                    continue

                # Check for emergency squawks
                check_emergency_squawk(aircraft)

                # Calculate distance if position available
                if 'lat' in aircraft and 'lon' in aircraft:
                    distance = haversine_miles(
                        HOME_LAT, HOME_LON,
                        aircraft['lat'], aircraft['lon']
                    )
                    aircraft['distance'] = round(distance, 1)

                    # Track closest approach
                    if distance < stats['closest_approach']:
                        stats['closest_approach'] = distance
                        stats['closest_aircraft'] = aircraft.copy()

                # Store in current aircraft
                current_aircraft[hex_code] = aircraft

                # Update history
                current_time = time.time()
                is_new_aircraft = hex_code not in aircraft_history

                if is_new_aircraft:
                    aircraft_history[hex_code] = {
                        'first_seen': current_time,
                        'positions': deque(maxlen=50),
                        'data': aircraft
                    }

                # Update 24-hour tracking
                cutoff_time = current_time - 86400  # 24 hours ago

                # Add new aircraft to 24-hour tracking
                if is_new_aircraft:
                    aircraft_seen_24h.append((hex_code, current_time))

                # Clean up old entries from 24-hour tracking
                while aircraft_seen_24h and aircraft_seen_24h[0][1] < cutoff_time:
                    aircraft_seen_24h.popleft()

                # Update total seen to reflect unique aircraft in last 24 hours
                unique_aircraft_24h = set(entry[0] for entry in aircraft_seen_24h)
                stats['total_seen'] = len(unique_aircraft_24h)

                # Add position to history
                if 'lat' in aircraft and 'lon' in aircraft:
                    aircraft_history[hex_code]['positions'].append({
                        'lat': aircraft['lat'],
                        'lon': aircraft['lon'],
                        'alt': aircraft.get('alt_baro', 0),
                        'time': time.time()
                    })

                aircraft_history[hex_code]['data'] = aircraft
                aircraft_history[hex_code]['last_seen'] = time.time()

            # Clean up old aircraft from history (remove those not seen for >60 seconds)
            current_time = time.time()
            stale_aircraft = []
            for hex_code, info in aircraft_history.items():
                if current_time - info.get('last_seen', 0) > 60:
                    stale_aircraft.append(hex_code)

            for hex_code in stale_aircraft:
                del aircraft_history[hex_code]

            # Update stats
            stats['max_simultaneous'] = max(stats['max_simultaneous'], len(current_aircraft))
            stats['current_count'] = len(current_aircraft)
            stats['last_update'] = time.time()

            # Add to update history
            stats['updates'].append({
                'time': time.time(),
                'count': len(current_aircraft)
            })

        time.sleep(UPDATE_INTERVAL)

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    # Return airplane emoji as SVG favicon
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <text y=".9em" font-size="90">✈️</text>
    </svg>'''
    from flask import Response
    return Response(svg, mimetype='image/svg+xml')

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('enhanced_dashboard.html')

@app.route('/api/aircraft')
def api_aircraft():
    """Get current aircraft data"""
    current_time = time.time()
    active_aircraft = []

    for hex_code, info in aircraft_history.items():
        # Only include recently seen aircraft (within last 30 seconds)
        if current_time - info.get('last_seen', 0) < 30:
            aircraft = info['data'].copy()
            aircraft['hex'] = hex_code
            aircraft['age'] = round(current_time - info['last_seen'], 1)

            # Add tracked aircraft info if available
            hex_upper = hex_code.upper()
            if hex_upper in tracked_aircraft:
                tracked = tracked_aircraft[hex_upper]
                aircraft['tracked'] = True
                aircraft['owner'] = tracked.get('owner', 'Unknown')
                aircraft['model'] = tracked.get('model', 'Unknown')
                aircraft['tail_number'] = tracked.get('tail_number', 'Unknown')
                aircraft['description'] = tracked.get('description', '')
            else:
                aircraft['tracked'] = False

            # Set display name
            if aircraft.get('flight') and aircraft.get('flight').strip():
                aircraft['display_name'] = aircraft.get('flight').strip()
            elif aircraft.get('tracked'):
                aircraft['display_name'] = aircraft.get('tail_number', hex_code.upper())
            else:
                aircraft['display_name'] = hex_code.upper()

            active_aircraft.append(aircraft)

    # Sort by distance
    active_aircraft.sort(key=lambda x: x.get('distance', float('inf')))

    return jsonify({
        'aircraft': active_aircraft,
        'stats': {
            'current': stats['current_count'],
            'total_seen': stats['total_seen'],  # 24-hour unique count
            'max_simultaneous': stats['max_simultaneous'],
            'closest_approach': round(stats['closest_approach'], 1) if stats['closest_approach'] != float('inf') else None,
            'closest_aircraft': stats['closest_aircraft'],
            'tracked_aircraft_count': len(tracked_aircraft)
        },
        'timestamp': current_time
    })

@app.route('/api/stats')
def api_stats():
    """Get dashboard statistics"""
    return jsonify({
        'current_count': stats['current_count'],
        'total_seen_24h': stats['total_seen'],
        'max_simultaneous': stats['max_simultaneous'],
        'closest_approach': round(stats['closest_approach'], 1) if stats['closest_approach'] != float('inf') else None,
        'tracked_aircraft': len(tracked_aircraft),
        'emergency_events': len(emergency_events),
        'last_update': stats['last_update'],
        'timestamp': time.time()
    })

@app.route('/api/events')
def api_events():
    """Get recent emergency events"""
    return jsonify({
        'events': list(emergency_events)[-20:],  # Last 20 events
        'total_events': len(emergency_events)
    })

@app.route('/api/tracked')
def api_tracked():
    """Get list of tracked aircraft"""
    tracked_list = []
    for icao, info in tracked_aircraft.items():
        tracked_list.append({
            'icao': icao,
            'tail_number': info.get('tail_number', 'N/A'),
            'owner': info.get('owner', 'Unknown'),
            'model': info.get('model', 'Unknown'),
            'description': info.get('description', '')
        })

    # Sort by owner name
    tracked_list.sort(key=lambda x: x['owner'])

    return jsonify({
        'tracked_aircraft': tracked_list,
        'total_tracked': len(tracked_list)
    })

if __name__ == '__main__':
    logging.info(f"Starting FlightTrak Dashboard on port 5030")
    logging.info(f"Tracking {len(tracked_aircraft)} aircraft")
    logging.info(f"Data source: {PLANES_URL}")

    # Start background data fetcher
    thread = threading.Thread(target=update_aircraft_data, daemon=True)
    thread.start()

    # Run Flask app
    app.run(host='0.0.0.0', port=5030, debug=False)
