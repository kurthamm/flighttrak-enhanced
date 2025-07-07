#!/usr/bin/env python3
"""
Enhanced FlightTrak Dashboard with integrated flight analyzer, email alerts, and aircraft lookup
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

# Import enhanced systems
try:
    from aircraft_lookup import AircraftLookup
    aircraft_lookup = AircraftLookup()
    AIRCRAFT_LOOKUP_ENABLED = True
    logging.info("Aircraft lookup system enabled")
except ImportError as e:
    logging.warning(f"Aircraft lookup disabled: {e}")
    aircraft_lookup = None
    AIRCRAFT_LOOKUP_ENABLED = False

try:
    from airport_data import AirportDetector
    airport_detector = AirportDetector()
    AIRPORT_DETECTION_ENABLED = True
    logging.info("Airport detection system enabled")
except ImportError as e:
    logging.warning(f"Airport detection disabled: {e}")
    airport_detector = None
    AIRPORT_DETECTION_ENABLED = False

try:
    from aircraft_rules import AircraftAlertRules
    alert_rules = AircraftAlertRules()
    AIRCRAFT_RULES_ENABLED = True
    logging.info("Aircraft-aware alert rules enabled")
except ImportError as e:
    logging.warning(f"Aircraft rules disabled: {e}")
    alert_rules = None
    AIRCRAFT_RULES_ENABLED = False

try:
    from path_analyzer import HistoricalPathAnalyzer
    path_analyzer = HistoricalPathAnalyzer()
    PATH_ANALYSIS_ENABLED = True
    logging.info("Historical path analysis enabled")
except ImportError as e:
    logging.warning(f"Path analysis disabled: {e}")
    path_analyzer = None
    PATH_ANALYSIS_ENABLED = False

try:
    from weather_context import WeatherContextProvider
    weather_provider = WeatherContextProvider()
    WEATHER_CONTEXT_ENABLED = True
    logging.info("Weather context system enabled")
except ImportError as e:
    logging.warning(f"Weather context disabled: {e}")
    weather_provider = None
    WEATHER_CONTEXT_ENABLED = False




app = Flask(__name__)

# Configuration
PLANES_URL = "https://planes.hamm.me/data/aircraft.json"
HOME_LAT = 34.1133171
HOME_LON = -80.9024019
UPDATE_INTERVAL = 2  # seconds

# Ensure all system flags are properly defined
if 'AIRCRAFT_LOOKUP_ENABLED' not in globals():
    AIRCRAFT_LOOKUP_ENABLED = False
if 'AIRPORT_DETECTION_ENABLED' not in globals():
    AIRPORT_DETECTION_ENABLED = False
if 'AIRCRAFT_RULES_ENABLED' not in globals():
    AIRCRAFT_RULES_ENABLED = False
if 'HISTORICAL_ANALYSIS_ENABLED' not in globals():
    HISTORICAL_ANALYSIS_ENABLED = False
if 'WEATHER_INTEGRATION_ENABLED' not in globals():
    WEATHER_INTEGRATION_ENABLED = False

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
    'current_count': 0,
    'max_simultaneous': 0,
    'closest_approach': float('inf'),
    'closest_aircraft': None,
    'last_update': 0,
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

def get_enhanced_aircraft_context(aircraft_data):
    """Get enhanced context for aircraft using all intelligent systems"""
    hex_code = aircraft_data.get('hex', '')
    
    # Get aircraft lookup info
    lookup_info = {}
    if AIRCRAFT_LOOKUP_ENABLED:
        try:
            lookup_info = aircraft_lookup.lookup_aircraft(hex_code)
        except Exception as e:
            logging.error(f"Lookup error for {hex_code}: {e}")
    
    # Check airport proximity
    airport_info = None
    if AIRPORT_DETECTION_ENABLED and 'lat' in aircraft_data and 'lon' in aircraft_data:
        try:
            airport_info = airport_detector.check_airport_proximity(
                aircraft_data['lat'],
                aircraft_data['lon'],
                aircraft_data.get('alt_baro', 0)
            )
        except Exception as e:
            logging.error(f"Airport detection error for {hex_code}: {e}")
    
    # Get weather context
    weather_context = None
    current_weather = None
    if WEATHER_INTEGRATION_ENABLED:
        try:
            current_weather = weather_detector.get_weather_data()
            if current_weather:
                weather_context = weather_detector.analyze_weather_impact(current_weather)
        except Exception as e:
            logging.error(f"Weather analysis error: {e}")
    
    # Create description
    registration = lookup_info.get('registration', hex_code.upper())
    operator = lookup_info.get('operator', 'Unknown Operator')
    aircraft_type = lookup_info.get('aircraft_type', 'Unknown Aircraft')
    
    description = f"{registration} ({operator})"
    if aircraft_type != 'Unknown Aircraft':
        description += f" - {aircraft_type}"
    
    return {
        'description': description,
        'lookup_info': lookup_info,
        'airport_info': airport_info,
        'weather_context': weather_context,
        'current_weather': current_weather
    }

def send_pattern_alert(event_type, description, aircraft_data):
    """Send email alert for interesting patterns"""
    if not config or not config.get('email_config'):
        return
        
    email_cfg = config['email_config']
    
    # Get aircraft lookup information if available
    hex_code = aircraft_data.get('hex', '')
    lookup_info = {}
    if AIRCRAFT_LOOKUP_ENABLED and hex_code:
        try:
            lookup_info = aircraft_lookup.lookup_aircraft(hex_code)
        except Exception as e:
            logging.error(f"Lookup error in email alert for {hex_code}: {e}")
    
    # Extract information with fallbacks
    registration = lookup_info.get('registration', aircraft_data.get('flight', hex_code.upper()))
    aircraft_type = lookup_info.get('aircraft_type', 'Unknown')
    manufacturer = lookup_info.get('manufacturer', 'Unknown')
    model = lookup_info.get('model', 'Unknown Aircraft')
    operator = lookup_info.get('operator', 'Unknown Operator')
    country = lookup_info.get('country', 'Unknown')
    category = lookup_info.get('category', 'Aircraft')
    
    # Create enhanced HTML email with full aircraft information
    html_content = f"""
    <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
        <div style='max-width:700px;margin:0 auto;background:#1a1f3a;padding:25px;border-radius:12px;border:1px solid #2a3f5f;box-shadow:0 4px 6px rgba(0,0,0,0.3);'>
            
            <!-- Alert Header -->
            <div style='text-align:center;margin-bottom:25px;padding-bottom:20px;border-bottom:2px solid #2a3f5f;'>
                <h1 style='color:#ff6b6b;margin:0;font-size:24px;'>🚨 FlightTrak Alert</h1>
                <h2 style='color:#4fc3f7;margin:10px 0;font-size:20px;'>{event_type}</h2>
                <p style='color:#feca57;font-size:16px;margin:5px 0;'>{description}</p>
            </div>
            
            <!-- Aircraft Identity Section -->
            <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                <h3 style='color:#4fc3f7;margin:0 0 15px 0;font-size:18px;'>🛩️ Aircraft Identity</h3>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
                    <div><strong>Registration:</strong> <span style='color:#feca57;'>{registration}</span></div>
                    <div><strong>ICAO Code:</strong> <span style='color:#feca57;'>{hex_code.upper()}</span></div>
                    <div><strong>Flight/Callsign:</strong> <span style='color:#feca57;'>{aircraft_data.get('flight', 'N/A')}</span></div>
                    <div><strong>Category:</strong> <span style='color:#feca57;'>{category}</span></div>
                </div>
            </div>
            
            <!-- Aircraft Type Section -->
            <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                <h3 style='color:#4fc3f7;margin:0 0 15px 0;font-size:18px;'>✈️ Aircraft Type</h3>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
                    <div><strong>Manufacturer:</strong> <span style='color:#feca57;'>{manufacturer}</span></div>
                    <div><strong>Model:</strong> <span style='color:#feca57;'>{model}</span></div>
                    <div><strong>Type Code:</strong> <span style='color:#feca57;'>{aircraft_type}</span></div>
                    <div><strong>Country:</strong> <span style='color:#feca57;'>{country}</span></div>
                </div>
            </div>
            
            <!-- Operator Section -->
            <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                <h3 style='color:#4fc3f7;margin:0 0 15px 0;font-size:18px;'>🏢 Operator Information</h3>
                <div style='text-align:center;'>
                    <strong style='font-size:16px;color:#feca57;'>{operator}</strong>
                </div>
            </div>
            
            <!-- Flight Data Section -->
            <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                <h3 style='color:#4fc3f7;margin:0 0 15px 0;font-size:18px;'>📊 Flight Data</h3>
                <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;'>
                    <div><strong>Altitude:</strong> <span style='color:#a29bfe;'>{aircraft_data.get('alt_baro', 'N/A')} ft</span></div>
                    <div><strong>Speed:</strong> <span style='color:#6c5ce7;'>{aircraft_data.get('gs', 'N/A')} kt</span></div>
                    <div><strong>Heading:</strong> <span style='color:#00d2d3;'>{aircraft_data.get('track', 'N/A')}°</span></div>
                    <div><strong>Squawk:</strong> <span style='color:#ff6b6b;'>{aircraft_data.get('squawk', 'N/A')}</span></div>
                    <div><strong>Vertical Rate:</strong> <span style='color:#a29bfe;'>{aircraft_data.get('baro_rate', 'N/A')} ft/min</span></div>
                    <div><strong>Distance:</strong> <span style='color:#48dbfb;'>{aircraft_data.get('distance', 'N/A')} mi</span></div>
                </div>
            </div>
            
            <!-- Position Information -->
            {f'''
            <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                <h3 style='color:#4fc3f7;margin:0 0 15px 0;font-size:18px;'>📍 Position</h3>
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;'>
                    <div><strong>Latitude:</strong> <span style='color:#feca57;'>{aircraft_data.get('lat', 'N/A')}</span></div>
                    <div><strong>Longitude:</strong> <span style='color:#feca57;'>{aircraft_data.get('lon', 'N/A')}</span></div>
                </div>
            </div>
            ''' if aircraft_data.get('lat') and aircraft_data.get('lon') else ''}
            
            <!-- Action Buttons -->
            <div style='text-align:center;margin:30px 0;'>
                <a href='https://flightaware.com/live/flight/{aircraft_data.get("flight", "")}' 
                   style='background:#4fc3f7;color:#0a0e27;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 10px;display:inline-block;'>
                   🔗 Track on FlightAware
                </a>
                <a href='https://www.flightradar24.com/data/aircraft/{registration.replace(" ", "")}' 
                   style='background:#feca57;color:#0a0e27;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 10px;display:inline-block;'>
                   📡 View on FlightRadar24
                </a>
            </div>
            
            <!-- Footer -->
            <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #2a3f5f;'>
                <p style='font-size:12px;color:#8892b0;margin:5px 0;'>
                    FlightTrak Enhanced Pattern Detection System
                </p>
                <p style='font-size:11px;color:#8892b0;margin:5px 0;'>
                    Aircraft data provided by hexdb.io • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
        </div>
    </body></html>
    """
    
    # Create enhanced subject line with aircraft identity
    aircraft_identity = registration if registration != hex_code.upper() else hex_code.upper()
    subject_line = f"🚨 FlightTrak Alert: {event_type} - {aircraft_identity} ({operator})"
    
    message = Mail(
        from_email=email_cfg['sender'],
        to_emails=email_cfg['recipients'],
        subject=subject_line,
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
    """Enhanced aircraft analysis with intelligent systems"""
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
    
    # Add position to historical analysis
    if PATH_ANALYSIS_ENABLED and 'lat' in aircraft and 'lon' in aircraft:
        path_analyzer.add_position(hex_code, aircraft)
        
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
        
        # Check for emergency squawks with enhanced context
        if squawk in ['7500', '7600', '7700']:
            emergency_types = {'7500': 'HIJACK', '7600': 'RADIO FAILURE', '7700': 'EMERGENCY'}
            
            # Get enhanced aircraft information
            enhanced_info = get_enhanced_aircraft_context(aircraft)
            description = f"{emergency_types[squawk]} - {enhanced_info['description']} squawking {squawk}!"
            
            log_event('EMERGENCY', description, aircraft)
            
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
                    
    # Enhanced altitude analysis with intelligent systems
    if aircraft.get('alt_baro'):
        alt = aircraft['alt_baro']
        stats_data['altitudes'].append(alt)
        
        # Check for rapid altitude changes with context awareness
        if len(stats_data['altitudes']) >= 5:
            alts = list(stats_data['altitudes'])
            alt_change = max(alts) - min(alts)
            if alt_change > 5000:  # More than 5000ft change in recent readings
                stats_data['rapid_changes'] += 1
                
                # Get enhanced context for better alerting
                enhanced_info = get_enhanced_aircraft_context(aircraft)
                should_alert = True
                reason = f"Rapid altitude change: {alt_change}ft in recent readings"
                
                # Check if weather explains the altitude changes
                if WEATHER_INTEGRATION_ENABLED and enhanced_info.get('current_weather'):
                    suppress, weather_reason = weather_detector.should_suppress_alert(
                        'altitude_changes', enhanced_info['current_weather']
                    )
                    if suppress:
                        should_alert = False
                        reason += f" (Weather-related: {weather_reason})"
                
                if should_alert:
                    log_event('ALTITUDE', f"{enhanced_info['description']} - {reason}", aircraft)
        
        # Enhanced low altitude checking with aircraft type awareness
        if AIRCRAFT_RULES_ENABLED:
            try:
                enhanced_info = get_enhanced_aircraft_context(aircraft)
                should_alert_alt, severity, reason = aircraft_rules.evaluate_altitude_alert(
                    {'hex': hex_code, 'alt_baro': alt, 'lookup': enhanced_info.get('lookup_info', {})}, 
                    enhanced_info.get('airport_info')
                )
                
                if should_alert_alt:
                    # Check weather suppression
                    weather_suppressed = False
                    if WEATHER_INTEGRATION_ENABLED and enhanced_info.get('current_weather'):
                        suppress, weather_reason = weather_detector.should_suppress_alert(
                            'low_altitude', enhanced_info['current_weather']
                        )
                        if suppress:
                            weather_suppressed = True
                            reason += f" (Weather: {weather_reason})"
                    
                    if not weather_suppressed:
                        log_event('LOW_ALTITUDE', f"{enhanced_info['description']} - {reason}", aircraft)
            except Exception as e:
                logging.error(f"Enhanced altitude analysis error for {hex_code}: {e}")
                
    # Enhanced speed analysis with aircraft type awareness
    if aircraft.get('gs'):
        speed = aircraft['gs']
        stats_data['speeds'].append(speed)
        
        if AIRCRAFT_RULES_ENABLED:
            try:
                enhanced_info = get_enhanced_aircraft_context(aircraft)
                should_alert_speed, severity, reason = aircraft_rules.evaluate_speed_alert(
                    {'hex': hex_code, 'gs': speed, 'alt_baro': aircraft.get('alt_baro', 0), 
                     'lookup': enhanced_info.get('lookup_info', {})}
                )
                
                if should_alert_speed:
                    # Check weather suppression
                    weather_suppressed = False
                    if WEATHER_INTEGRATION_ENABLED and enhanced_info.get('current_weather'):
                        suppress, weather_reason = weather_detector.should_suppress_alert(
                            'slow_speed', enhanced_info['current_weather']
                        )
                        if suppress:
                            weather_suppressed = True
                            reason += f" (Weather: {weather_reason})"
                    
                    if not weather_suppressed:
                        log_event('SPEED', f"{enhanced_info['description']} - {reason}", aircraft)
            except Exception as e:
                logging.error(f"Enhanced speed analysis error for {hex_code}: {e}")
        else:
            # Fallback to basic speed checks
            if speed > 650:  # Very high speed
                enhanced_info = get_enhanced_aircraft_context(aircraft)
                log_event('SPEED', f"{enhanced_info['description']} - High speed: {speed}kt", aircraft)
            elif speed < 40 and aircraft.get('alt_baro', 0) > 10000:
                enhanced_info = get_enhanced_aircraft_context(aircraft)
                log_event('SPEED', f"{enhanced_info['description']} - Low speed at altitude: {speed}kt @ {aircraft.get('alt_baro')}ft", aircraft)

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
    """Get current aircraft data with enhanced lookup information"""
    current_time = time.time()
    active_aircraft = []
    
    # Collect ICAO codes for batch lookup
    icao_codes_to_lookup = []
    aircraft_data_list = []
    
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
            
            aircraft_data_list.append(aircraft)
            icao_codes_to_lookup.append(hex_code)
    
    # Perform batch aircraft lookup if enabled
    aircraft_lookup_data = {}
    if AIRCRAFT_LOOKUP_ENABLED and icao_codes_to_lookup:
        try:
            aircraft_lookup_data = aircraft_lookup.batch_lookup(icao_codes_to_lookup)
        except Exception as e:
            logging.error(f"Aircraft lookup error: {e}")
    
    # Enhance aircraft data with lookup information
    for aircraft in aircraft_data_list:
        hex_code = aircraft['hex']
        
        # Add aircraft lookup data
        if hex_code in aircraft_lookup_data:
            lookup_info = aircraft_lookup_data[hex_code]
            aircraft['lookup'] = {
                'registration': lookup_info.get('registration', f'Unknown ({hex_code.upper()})'),
                'aircraft_type': lookup_info.get('aircraft_type', 'Unknown'),
                'manufacturer': lookup_info.get('manufacturer', 'Unknown'),
                'model': lookup_info.get('model', 'Unknown Aircraft'),
                'operator': lookup_info.get('operator', 'Unknown Operator'),
                'country': lookup_info.get('country', 'Unknown'),
                'category': lookup_info.get('category', 'Aircraft'),
                'description': lookup_info.get('description', 'Unknown aircraft type'),
                'source': lookup_info.get('source', 'none')
            }
            
            # Use registration as display name if no flight number
            if not aircraft.get('flight') or aircraft.get('flight').strip() == hex_code:
                aircraft['display_name'] = lookup_info.get('registration', hex_code.upper())
                aircraft['display_type'] = 'registration'
            else:
                aircraft['display_name'] = aircraft.get('flight', hex_code.upper())
                aircraft['display_type'] = 'callsign'
        else:
            # No lookup data available
            aircraft['lookup'] = {
                'registration': f'Unknown ({hex_code.upper()})',
                'aircraft_type': 'Unknown',
                'manufacturer': 'Unknown',
                'model': 'Unknown Aircraft',
                'operator': 'Unknown Operator',
                'country': 'Unknown',
                'category': 'Aircraft',
                'description': 'Aircraft information not available',
                'source': 'none'
            }
            aircraft['display_name'] = aircraft.get('flight', hex_code.upper())
            aircraft['display_type'] = 'icao' if not aircraft.get('flight') or aircraft.get('flight').strip() == hex_code else 'callsign'
        
        active_aircraft.append(aircraft)
    
    # Sort by distance
    active_aircraft.sort(key=lambda x: x.get('distance', float('inf')))
    
    # Calculate time-based statistics instead of all-time totals
    one_day_ago = current_time - 86400
    one_week_ago = current_time - (7 * 86400)
    
    today_count = sum(1 for info in aircraft_history.values() 
                     if info.get('first_seen', 0) >= one_day_ago)
    week_count = sum(1 for info in aircraft_history.values() 
                    if info.get('first_seen', 0) >= one_week_ago)
    
    return jsonify({
        'aircraft': active_aircraft,
        'stats': {
            'current': stats['current_count'],
            'today_total': today_count,
            'week_total': week_count,
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

@app.route('/api/lookup-stats')
def api_lookup_stats():
    """Get aircraft lookup system statistics"""
    if AIRCRAFT_LOOKUP_ENABLED:
        try:
            stats = aircraft_lookup.get_cache_stats()
            stats['enabled'] = True
            return jsonify(stats)
        except Exception as e:
            return jsonify({'enabled': True, 'error': str(e)})
    else:
        return jsonify({'enabled': False})

@app.route('/api/patterns')
def api_patterns():
    """Get enhanced pattern analysis data"""
    pattern_summary = {
        'emergency_aircraft': 0,
        'circling_aircraft': 0,
        'multiple_callsigns': 0,
        'rapid_climbers': 0
    }
    
    # Enhanced circling detection
    if HISTORICAL_ANALYSIS_ENABLED:
        try:
            circling_aircraft = path_analyzer.get_circling_aircraft()
            pattern_summary['circling_aircraft'] = len(circling_aircraft)
        except Exception as e:
            logging.error(f"Error getting circling aircraft: {e}")
    
    for hex_code, analysis in aircraft_stats.items():
        if '7500' in analysis.get('squawks', set()) or '7600' in analysis.get('squawks', set()) or '7700' in analysis.get('squawks', set()):
            pattern_summary['emergency_aircraft'] += 1
        if len(analysis.get('callsigns', set())) > 1:
            pattern_summary['multiple_callsigns'] += 1
        if analysis.get('rapid_changes', 0) > 0:
            pattern_summary['rapid_climbers'] += 1
    
    return jsonify(pattern_summary)

@app.route('/api/weather')
def api_weather():
    """Get current weather information and impact"""
    if not WEATHER_INTEGRATION_ENABLED:
        return jsonify({'enabled': False})
    
    try:
        weather_summary = weather_detector.get_weather_summary()
        return jsonify(weather_summary)
    except Exception as e:
        return jsonify({'enabled': True, 'error': str(e)})

@app.route('/api/airports')
def api_airports():
    """Get nearby airports information"""
    if not AIRPORT_DETECTION_ENABLED:
        return jsonify({'enabled': False})
    
    try:
        # Get airports within 50 miles for display
        airports_info = []
        for icao, airport in airport_detector.airports.items():
            distance = airport_detector.haversine_miles(
                HOME_LAT, HOME_LON, airport.lat, airport.lon
            )
            airports_info.append({
                'icao': airport.icao,
                'name': airport.name,
                'lat': airport.lat,
                'lon': airport.lon,
                'distance_miles': round(distance, 1),
                'airport_type': airport.airport_type,
                'elevation_ft': airport.elevation_ft
            })
        
        # Sort by distance
        airports_info.sort(key=lambda x: x['distance_miles'])
        
        return jsonify({
            'enabled': True,
            'airports': airports_info[:10],  # Top 10 closest
            'total_airports': len(airports_info)
        })
    except Exception as e:
        return jsonify({'enabled': True, 'error': str(e)})

@app.route('/api/system-status')
def api_system_status():
    """Get status of all intelligent systems"""
    return jsonify({
        'aircraft_lookup': AIRCRAFT_LOOKUP_ENABLED,
        'airport_detection': AIRPORT_DETECTION_ENABLED,
        'aircraft_rules': AIRCRAFT_RULES_ENABLED,
        'historical_analysis': HISTORICAL_ANALYSIS_ENABLED,
        'weather_integration': WEATHER_INTEGRATION_ENABLED,
        'timestamp': time.time()
    })

@app.route('/api/ai-intelligence')
def api_ai_intelligence():
    """Get AI Intelligence System status and recent alerts"""
    try:
        import subprocess
        import os
        
        # Check if AI intelligence service is running
        try:
            result = subprocess.run(['systemctl', 'is-active', 'flighttrak-ai-intelligence'], 
                                  capture_output=True, text=True, timeout=5)
            ai_service_running = result.stdout.strip() == 'active'
        except:
            ai_service_running = False
        
        # Get intelligence from log file and database
        alerts_sent = 0
        news_correlations = 0
        patterns_detected = 0
        location_intelligence = 0
        
        try:
            if os.path.exists('ai_intelligence_service.log'):
                with open('ai_intelligence_service.log', 'r') as f:
                    log_content = f.read()
                    # Count different types of intelligence activities
                    alerts_sent = log_content.count('alert sent')
                    news_correlations = log_content.count('Enhanced Intelligence')
                    patterns_detected = log_content.count('pattern detected')
                    location_intelligence = log_content.count('Geographic Intelligence')
        except:
            pass
            
        # Try to get data from intelligence database
        try:
            import sqlite3
            if os.path.exists('intelligence.db'):
                conn = sqlite3.connect('intelligence.db')
                cursor = conn.cursor()
                
                # Count events in database
                cursor.execute("SELECT COUNT(*) FROM events WHERE timestamp > datetime('now', '-24 hours')")
                daily_events = cursor.fetchone()[0]
                patterns_detected = max(patterns_detected, daily_events)
                
                conn.close()
        except:
            pass
        
        return jsonify({
            'enabled': ai_service_running,
            'service_status': 'running' if ai_service_running else 'stopped',
            'enhanced_intelligence': {
                'location_services': 4,  # OpenStreetMap, MapBox, HERE, What3Words
                'news_sources': 6,       # NewsAPI, Reddit, Google News, etc.
                'total_services': 10
            },
            'alerts_sent': alerts_sent,
            'patterns_detected': patterns_detected,
            'news_correlations': news_correlations,
            'location_intelligence': location_intelligence,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'enabled': False,
            'error': str(e),
            'timestamp': time.time()
        })

if __name__ == '__main__':
    # Start background data fetcher
    thread = threading.Thread(target=update_aircraft_data, daemon=True)
    thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5030, debug=True)