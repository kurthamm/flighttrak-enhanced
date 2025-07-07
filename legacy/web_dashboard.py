#!/usr/bin/env python3
"""
Web Dashboard for FlightTrak - Monitor aircraft data remotely
Connects to planes.hamm.me to fetch and display real-time flight data
"""

import json
import time
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify
import threading
from collections import deque
import math

app = Flask(__name__)

# Configuration
PLANES_URL = "https://planes.hamm.me/data/aircraft.json"
HOME_LAT = 34.1133171
HOME_LON = -80.9024019
UPDATE_INTERVAL = 2  # seconds

# Data storage
aircraft_history = {}
tracked_aircraft = set()
stats = {
    'total_seen': 0,
    'max_simultaneous': 0,
    'closest_approach': float('inf'),
    'closest_aircraft': None,
    'updates': deque(maxlen=100)
}

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

def fetch_aircraft_data():
    """Fetch aircraft data from planes.hamm.me"""
    try:
        response = requests.get(PLANES_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def update_aircraft_data():
    """Background thread to update aircraft data"""
    global stats
    
    while True:
        data = fetch_aircraft_data()
        if data:
            current_aircraft = {}
            
            for aircraft in data.get('aircraft', []):
                hex_code = aircraft.get('hex', '')
                if not hex_code:
                    continue
                
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
                if hex_code not in aircraft_history:
                    aircraft_history[hex_code] = {
                        'first_seen': time.time(),
                        'positions': deque(maxlen=50),
                        'data': aircraft
                    }
                    stats['total_seen'] += 1
                
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
            
            # Update stats
            stats['max_simultaneous'] = max(stats['max_simultaneous'], 
                                           len(current_aircraft))
            stats['current_count'] = len(current_aircraft)
            stats['last_update'] = time.time()
            
            # Add to update history
            stats['updates'].append({
                'time': time.time(),
                'count': len(current_aircraft)
            })
        
        time.sleep(UPDATE_INTERVAL)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

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
            active_aircraft.append(aircraft)
    
    # Sort by distance
    active_aircraft.sort(key=lambda x: x.get('distance', float('inf')))
    
    return jsonify({
        'aircraft': active_aircraft,
        'stats': {
            'current': stats['current_count'],
            'total_seen': stats['total_seen'],
            'max_simultaneous': stats['max_simultaneous'],
            'closest_approach': round(stats['closest_approach'], 1),
            'closest_aircraft': stats['closest_aircraft']
        },
        'timestamp': current_time
    })

@app.route('/api/history/<hex_code>')
def api_history(hex_code):
    """Get history for specific aircraft"""
    if hex_code in aircraft_history:
        history = aircraft_history[hex_code]
        return jsonify({
            'hex': hex_code,
            'first_seen': history['first_seen'],
            'last_seen': history['last_seen'],
            'positions': list(history['positions']),
            'current_data': history['data']
        })
    return jsonify({'error': 'Aircraft not found'}), 404

@app.route('/api/stats')
def api_stats():
    """Get statistics"""
    return jsonify(stats)

if __name__ == '__main__':
    # Start background data fetcher
    thread = threading.Thread(target=update_aircraft_data, daemon=True)
    thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)