#!/usr/bin/env python3
"""
Enhanced FlightTrak Dashboard with integrated flight analyzer and email alerts
"""

import json
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import threading
from collections import deque, defaultdict, Counter
import math
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import logging

app = Flask(__name__)

# Configuration
PLANES_URL = "https://planes.hamm.me/data/aircraft.json"
HOME_LAT = 34.1133171
HOME_LON = -80.9024019
UPDATE_INTERVAL = 2  # seconds

# Load config for email alerts
def load_config():
    try:
        with open('config.json') as f:
            return json.load(f)
    except:
        return None

config = load_config()

# Data storage
aircraft_history = {}
tracked_aircraft = set()
interesting_events = deque(maxlen=100)
stats = {
    'total_seen': 0,
    'max_simultaneous': 0,
    'closest_approach': float('inf'),
    'closest_aircraft': None,
    'updates': deque(maxlen=100),
    'patterns_detected': 0,
    'emergencies_detected': 0
}

# Flight analyzer data
flight_patterns = defaultdict(list)
aircraft_stats = defaultdict(lambda: {
    'total_messages': 0,
    'positions': deque(maxlen=50),
    'altitudes': deque(maxlen=20),
    'speeds': deque(maxlen=20),
    'first_seen': None,
    'last_seen': None,
    'callsigns': set(),
    'squawks': set(),
    'rapid_changes': 0
})

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

def send_pattern_alert(event_type, description, aircraft_data):
    """Send email alert for interesting patterns"""
    if not config or not config.get('email_config'):
        return
        
    email_cfg = config['email_config']
    
    # Create fancy HTML email
    html_content = f"""
    <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
        <div style='max-width:600px;margin:0 auto;background:#1a1f3a;padding:20px;border-radius:10px;border:1px solid #2a3f5f;'>
            <h2 style='color:#ff6b6b;margin-bottom:10px;'>🚨 FlightTrak Alert: {event_type}</h2>
            <h3 style='color:#4fc3f7;margin-bottom:15px;'>{description}</h3>
            
            <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                <h4 style='color:#feca57;margin-bottom:10px;'>Aircraft Details:</h4>
                <table style='width:100%;color:#e0e6ed;'>
                    <tr><td><strong>ICAO:</strong></td><td>{aircraft_data.get('hex', 'N/A')}</td></tr>
                    <tr><td><strong>Flight:</strong></td><td>{aircraft_data.get('flight', 'N/A')}</td></tr>
                    <tr><td><strong>Altitude:</strong></td><td>{aircraft_data.get('alt_baro', 'N/A')} ft</td></tr>
                    <tr><td><strong>Speed:</strong></td><td>{aircraft_data.get('gs', 'N/A')} kt</td></tr>
                    <tr><td><strong>Squawk:</strong></td><td>{aircraft_data.get('squawk', 'N/A')}</td></tr>
                </table>
            </div>
            
            <p style='margin-top:20px;text-align:center;'>
                <a href='https://flightaware.com/live/flight/{aircraft_data.get("flight", "")}' 
                   style='background:#4fc3f7;color:#0a0e27;padding:10px 20px;text-decoration:none;border-radius:5px;font-weight:bold;'>
                   Track on FlightAware
                </a>
            </p>
            
            <p style='font-size:12px;color:#8892b0;text-align:center;margin-top:20px;'>
                FlightTrak Enhanced Pattern Detection System
            </p>
        </div>
    </body></html>
    """
    
    message = Mail(
        from_email=email_cfg['sender'],
        to_emails=email_cfg['recipients'],
        subject=f"FlightTrak Alert: {event_type} - {aircraft_data.get('hex', 'Unknown')}",
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
        resp = sg.send(message)
        logging.info(f"Pattern alert sent for {event_type}: {aircraft_data.get('hex', 'Unknown')}")
    except Exception as e:
        logging.error(f"Error sending pattern alert: {e}")

def log_event(event_type, description, aircraft_data):
    """Log interesting events"""
    event = {
        'time': datetime.now().isoformat(),
        'timestamp': time.time(),
        'type': event_type,
        'description': description,
        'aircraft': aircraft_data,
        'id': len(interesting_events)
    }
    interesting_events.append(event)
    
    # Update stats
    if event_type == 'EMERGENCY':
        stats['emergencies_detected'] += 1
    elif event_type in ['PATTERN', 'ALTITUDE', 'SPEED']:
        stats['patterns_detected'] += 1
    
    # Send email alert for important events
    if event_type in ['EMERGENCY', 'PATTERN']:
        send_pattern_alert(event_type, description, aircraft_data)
    
    print(f"[{event_type}] {description}")

def analyze_aircraft(aircraft):
    """Enhanced aircraft analysis"""
    hex_code = aircraft.get('hex', '')
    if not hex_code:
        return
        
    stats_data = aircraft_stats[hex_code]
    current_time = time.time()
    
    # Update basic stats
    stats_data['total_messages'] += aircraft.get('messages', 0)
    stats_data['last_seen'] = current_time
    if not stats_data['first_seen']:
        stats_data['first_seen'] = current_time
        
    # Track callsigns
    if aircraft.get('flight'):
        callsign = aircraft['flight'].strip()
        if callsign not in stats_data['callsigns']:
            stats_data['callsigns'].add(callsign)
            if len(stats_data['callsigns']) > 1:
                log_event('CALLSIGN', f"Multiple callsigns detected: {list(stats_data['callsigns'])}", aircraft)
            
    # Track squawks
    if aircraft.get('squawk'):
        squawk = aircraft['squawk']
        stats_data['squawks'].add(squawk)
        
        # Check for emergency squawks
        if squawk in ['7500', '7600', '7700']:
            emergency_types = {'7500': 'HIJACK', '7600': 'RADIO FAILURE', '7700': 'EMERGENCY'}
            log_event('EMERGENCY', f"{emergency_types[squawk]} - Aircraft squawking {squawk}!", aircraft)
            
    # Track positions for pattern detection
    if 'lat' in aircraft and 'lon' in aircraft:
        position = {
            'lat': aircraft['lat'],
            'lon': aircraft['lon'],
            'time': current_time
        }
        stats_data['positions'].append(position)
        
        # Check for circling patterns
        if len(stats_data['positions']) >= 10:
            positions = list(stats_data['positions'])
            first = positions[0]
            last = positions[-1]
            
            # Calculate distance between first and last position
            dist = haversine_miles(first['lat'], first['lon'], last['lat'], last['lon'])
            
            # If aircraft returned close to start position
            if dist < 2:  # Within 2 miles
                total_dist = 0
                for i in range(1, len(positions)):
                    total_dist += haversine_miles(
                        positions[i-1]['lat'], positions[i-1]['lon'],
                        positions[i]['lat'], positions[i]['lon']
                    )
                
                if total_dist > 10:  # Traveled more than 10 miles total
                    log_event('PATTERN', f"Circling pattern detected - {total_dist:.1f} miles traveled", aircraft)
                    
    # Track altitudes
    if aircraft.get('alt_baro'):
        alt = aircraft['alt_baro']
        stats_data['altitudes'].append(alt)
        
        # Check for rapid altitude changes
        if len(stats_data['altitudes']) >= 5:
            alts = list(stats_data['altitudes'])
            alt_change = max(alts) - min(alts)
            if alt_change > 5000:  # More than 5000ft change in recent readings
                stats_data['rapid_changes'] += 1
                log_event('ALTITUDE', f"Rapid altitude change: {alt_change}ft in recent readings", aircraft)
                
    # Track speeds
    if aircraft.get('gs'):
        speed = aircraft['gs']
        stats_data['speeds'].append(speed)
        
        # Check for unusual speeds
        if speed > 650:  # Very high speed
            log_event('SPEED', f"High speed detected: {speed}kt", aircraft)
        elif speed < 40 and aircraft.get('alt_baro', 0) > 10000:
            log_event('SPEED', f"Unusually low speed at altitude: {speed}kt @ {aircraft.get('alt_baro')}ft", aircraft)

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
    """Background thread to update aircraft data with analysis"""
    global stats
    
    while True:
        data = fetch_aircraft_data()
        if data:
            current_aircraft = {}
            
            for aircraft in data.get('aircraft', []):
                hex_code = aircraft.get('hex', '')
                if not hex_code:
                    continue
                
                # Analyze aircraft for patterns
                analyze_aircraft(aircraft)
                
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
            stats['max_simultaneous'] = max(stats['max_simultaneous'], len(current_aircraft))
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
            
            # Add analysis data
            analysis = aircraft_stats.get(hex_code, {})
            aircraft['analysis'] = {
                'callsigns': len(analysis.get('callsigns', set())),
                'rapid_changes': analysis.get('rapid_changes', 0),
                'duration': round((current_time - analysis.get('first_seen', current_time)) / 60, 1)
            }
            
            active_aircraft.append(aircraft)
    
    # Sort by distance
    active_aircraft.sort(key=lambda x: x.get('distance', float('inf')))
    
    return jsonify({
        'aircraft': active_aircraft,
        'stats': {
            'current': stats['current_count'],
            'total_seen': stats['total_seen'],
            'max_simultaneous': stats['max_simultaneous'],
            'closest_approach': round(stats['closest_approach'], 1) if stats['closest_approach'] != float('inf') else None,
            'closest_aircraft': stats['closest_aircraft'],
            'patterns_detected': stats['patterns_detected'],
            'emergencies_detected': stats['emergencies_detected']
        },
        'timestamp': current_time
    })

@app.route('/api/events')
def api_events():
    """Get interesting events"""
    return jsonify({
        'events': list(interesting_events)[-20:],  # Last 20 events
        'total_events': len(interesting_events)
    })

@app.route('/api/patterns')
def api_patterns():
    """Get pattern analysis data"""
    pattern_summary = {
        'emergency_aircraft': 0,
        'circling_aircraft': 0,
        'multiple_callsigns': 0,
        'rapid_climbers': 0
    }
    
    for hex_code, analysis in aircraft_stats.items():
        if '7500' in analysis.get('squawks', set()) or '7600' in analysis.get('squawks', set()) or '7700' in analysis.get('squawks', set()):
            pattern_summary['emergency_aircraft'] += 1
        if len(analysis.get('callsigns', set())) > 1:
            pattern_summary['multiple_callsigns'] += 1
        if analysis.get('rapid_changes', 0) > 0:
            pattern_summary['rapid_climbers'] += 1
    
    return jsonify(pattern_summary)

if __name__ == '__main__':
    # Start background data fetcher
    thread = threading.Thread(target=update_aircraft_data, daemon=True)
    thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5030, debug=True)