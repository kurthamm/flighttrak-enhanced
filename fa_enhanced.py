#!/usr/bin/env python3
import socket
import json
import time
import os
import subprocess
import logging
import math
import requests
from datetime import datetime
from threading import Thread
from collections import defaultdict, deque
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Set up logging
logging.basicConfig(
    filename='flightalert.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logging.info("Starting Enhanced Flight Alert service.")

# Pattern detection storage
aircraft_stats = defaultdict(lambda: {
    'positions': deque(maxlen=50),
    'altitudes': deque(maxlen=20),
    'speeds': deque(maxlen=20),
    'first_seen': None,
    'last_seen': None,
    'callsigns': set(),
    'squawks': set(),
    'rapid_changes': 0
})

# Haversine formula: distance in miles between two lat/lon
def haversine_miles(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist_km = R_km * c
    return dist_km * 0.621371

# Load JSON file utility
def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {path}: {e}")
        return None

def send_pattern_alert(event_type, description, aircraft_data, email_cfg):
    """Send email alert for interesting patterns"""
    # Create fancy HTML email
    html_content = f"""
    <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
        <div style='max-width:600px;margin:0 auto;background:#1a1f3a;padding:20px;border-radius:10px;border:1px solid #2a3f5f;'>
            <h2 style='color:#ff6b6b;margin-bottom:10px;'>🚨 FlightTrak Pattern Alert: {event_type}</h2>
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
        subject=f"FlightTrak Pattern Alert: {event_type} - {aircraft_data.get('hex', 'Unknown')}",
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
        resp = sg.send(message)
        logging.info(f"Pattern alert sent for {event_type}: {aircraft_data.get('hex', 'Unknown')} (status {resp.status_code})")
    except Exception as e:
        logging.error(f"Error sending pattern alert: {e}")

def analyze_aircraft_patterns(aircraft, email_cfg, home_lat, home_lon):
    """Analyze aircraft for interesting patterns"""
    hex_code = aircraft.get('hex', '')
    if not hex_code:
        return
        
    stats_data = aircraft_stats[hex_code]
    current_time = time.time()
    
    # Update basic stats
    stats_data['last_seen'] = current_time
    if not stats_data['first_seen']:
        stats_data['first_seen'] = current_time
        
    # Track callsigns
    if aircraft.get('flight'):
        callsign = aircraft['flight'].strip()
        if callsign not in stats_data['callsigns']:
            stats_data['callsigns'].add(callsign)
            if len(stats_data['callsigns']) > 1:
                logging.info(f"Multiple callsigns detected for {hex_code}: {list(stats_data['callsigns'])}")
            
    # Track squawks and check for emergencies
    if aircraft.get('squawk'):
        squawk = aircraft['squawk']
        stats_data['squawks'].add(squawk)
        
        # Check for emergency squawks
        if squawk in ['7500', '7600', '7700']:
            emergency_types = {'7500': 'HIJACK', '7600': 'RADIO FAILURE', '7700': 'EMERGENCY'}
            description = f"{emergency_types[squawk]} - Aircraft squawking {squawk}!"
            logging.warning(f"EMERGENCY DETECTED: {description}")
            send_pattern_alert('EMERGENCY', description, aircraft, email_cfg)
            
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
                    description = f"Circling pattern detected - {total_dist:.1f} miles traveled in small area"
                    logging.info(f"PATTERN DETECTED: {description}")
                    send_pattern_alert('PATTERN', description, aircraft, email_cfg)
                    
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
                description = f"Rapid altitude change: {alt_change}ft in recent readings"
                logging.info(f"ALTITUDE PATTERN: {description}")
                
    # Track speeds
    if aircraft.get('gs'):
        speed = aircraft['gs']
        stats_data['speeds'].append(speed)
        
        # Check for unusual speeds
        if speed > 650:  # Very high speed
            description = f"High speed detected: {speed}kt"
            logging.info(f"SPEED PATTERN: {description}")
        elif speed < 40 and aircraft.get('alt_baro', 0) > 10000:
            description = f"Unusually low speed at altitude: {speed}kt @ {aircraft.get('alt_baro')}ft"
            logging.info(f"SPEED PATTERN: {description}")

# Send basic notification
def send_notification(subject, body, email_cfg):
    msg = Mail(
        from_email=email_cfg['sender'],
        to_emails=email_cfg['notification_email'],
        subject=subject,
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
        resp = sg.send(msg)
        logging.info(f"Notification '{subject}' sent (status {resp.status_code})")
    except Exception as e:
        logging.error(f"Error sending notification '{subject}': {e}")

# Build and send HTML alert
def send_email_alert(ac, email_cfg):
    icao = ac['icao']
    flight = ac.get('flight', 'N/A')
    tail = ac.get('tail_number', 'N/A')
    owner = ac.get('owner', 'N/A')
    dist = ac.get('distance_mi', 'unknown')
    alt = ac.get('alt_baro', 'N/A')
    gs = ac.get('gs', 'N/A')
    hdg = ac.get('track', ac.get('true_heading', 'N/A'))

    # Summary info
    header = (f"🛩️ Aircraft Alert: {owner} (ICAO: {icao})"
              f"<span style='font-size:0.8em; color:#666;'>"
              f" Distance: {dist} mi • Alt: {alt} ft • Spd: {gs} kt"
              f"</span>")
    subline = f"Tail: {tail} | Callsign: {flight}"

    # Collapsible details table
    details = [
        ('ICAO', icao),
        ('Callsign', flight),
        ('Tail Number', tail),
        ('Owner', owner),
        ('Latitude', ac.get('lat', 'N/A')),
        ('Longitude', ac.get('lon', 'N/A')),
        ('Baro Alt', alt),
        ('Ground Speed', gs),
        ('Heading', hdg),
        ('Vertical Rate', ac.get('baro_rate', 'N/A')),
        ('Squawk', ac.get('squawk', 'N/A')),
        ('Category', ac.get('category', 'N/A')),
        ('RSSI', ac.get('rssi', 'N/A')),
        ('Distance', f"{dist} mi")
    ]

    # Build HTML
    html = ["<html><body style='font-family:Arial,sans-serif;line-height:1.4'>",
            f"<h2 style='margin-bottom:0.2em;'>{header}</h2>",
            f"<p style='margin-top:0.2em;'>{subline}</p>",
            "<details style='margin-top:1em;border:1px solid #ccc;padding:0.5em;border-radius:4px;'>",
            "<summary style='font-weight:bold; cursor:pointer;'>▶ Click for full details</summary>",
            "<table style='width:100%;border-collapse:collapse;margin-top:0.5em;'>",
            "<tr style='background:#f0f0f0;'><th style='padding:6px;'>Field</th><th style='padding:6px;'>Value</th></tr>"]
    for i,(k,v) in enumerate(details):
        bg = '#fafafa' if i%2 else '#fff'
        html.append(f"<tr style='background:{bg};'><td style='padding:6px;'>{k}</td><td style='padding:6px;'>{v}</td></tr>")
    html += ["</table>",
             "<p style='margin-top:0.8em;'>",
             f"🔗 <a href='http://flightaware.com/live/flight/{flight}'>FlightAware</a> | ",
             f"📍 <a href='https://maps.google.com/?q={ac.get('lat')},{ac.get('lon')}'>Google Maps</a>",
             "</p>",
             "</details>",
             "</body></html>"]
    content = ''.join(html)

    message = Mail(
        from_email=email_cfg['sender'],
        to_emails=email_cfg['recipients'],
        subject=f"Aircraft Alert: {owner} (ICAO: {icao})",
        html_content=content
    )
    try:
        sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
        resp = sg.send(message)
        logging.info(f"Alert email sent for {icao} (status {resp.status_code})")
    except Exception as e:
        logging.error(f"Error sending alert email for {icao}: {e}")

# Thread for "alive" notifications
def alive_notification(cfg, interval):
    while True:
        send_notification("FlightAlert is alive", "Enhanced service still running with pattern detection.", cfg)
        time.sleep(interval)

# Run send_service_notification.py
def notify_service_start():
    try:
        subprocess.run([
            "venv/bin/python3",
            "send_service_notification.py",
            "start"
        ], check=True)
        logging.info("Service start notification sent.")
    except Exception as e:
        logging.error(f"Failed start notify: {e}")

# Monitor dump1090 AVR-TCP
def monitor_aircraft(host, port, ac_list, cfg, home_lat, home_lon, detected_file):
    detected = set(open(detected_file).read().splitlines()) if os.path.exists(detected_file) else set()
    PLANES_URL = 'https://planes.hamm.me/data/aircraft.json'
    
    def lookup_aircraft_data(icao):
        try:
            import requests
            response = requests.get(PLANES_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            for ac in data.get('aircraft', []):
                if ac.get('hex','').lower()==icao.lower():
                    return ac
        except Exception as e:
            logging.error(f"lookup_aircraft_data {icao}: {e}")
        return None

    # For remote monitoring, we'll poll the JSON API instead of TCP socket
    import requests
    logging.info(f"Monitoring aircraft data from {PLANES_URL}")
    
    # Log initial detection state
    logging.info(f"Starting with {len(detected)} previously detected aircraft")
    logging.info(f"Monitoring {len(ac_list)} aircraft from tracking list")
    
    while True:
        try:
            response = requests.get(PLANES_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Analyze ALL aircraft for patterns, not just tracked ones
            for aircraft in data.get('aircraft', []):
                if aircraft.get('hex'):
                    analyze_aircraft_patterns(aircraft, cfg, home_lat, home_lon)
            
            # Check tracked aircraft for alerts
            for aircraft in data.get('aircraft', []):
                icao = aircraft.get('hex', '').upper()
                if not icao:
                    continue
                    
                # Check if this is a tracked aircraft we haven't detected yet
                if icao not in detected:
                    for ac_info in ac_list:
                        if ac_info['icao'].upper() == icao:
                            # New detection!
                            detected.add(icao)
                            with open(detected_file, 'a') as f:
                                f.write(icao + '\n')
                            
                            # Merge stored info with live data
                            ac = {**ac_info, **aircraft}
                            
                            # Calculate distance if position available
                            if 'lat' in aircraft and 'lon' in aircraft:
                                lat = float(aircraft['lat'])
                                lon = float(aircraft['lon'])
                                ac['distance_mi'] = f"{haversine_miles(home_lat, home_lon, lat, lon):.1f}"
                            else:
                                ac['distance_mi'] = 'unknown'
                            
                            # Send alert
                            send_email_alert(ac, cfg)
                            logging.info(f"Detected tracked aircraft: {icao}")
                            break
            
            # Wait before next check
            time.sleep(2)  # Poll every 2 seconds
            
        except Exception as e:
            logging.error(f"Error monitoring aircraft: {e}")
            time.sleep(5)  # Wait longer on error

if __name__ == '__main__':
    cfg = load_json('config.json')
    if not cfg: exit(1)
    ac_list = load_json('aircraft_list.json').get('aircraft_to_detect', [])
    email_cfg = cfg['email_config']
    home_lat = cfg['home']['lat']
    home_lon = cfg['home']['lon']
    detected_file = 'detected_aircraft.txt'
    
    # Startup
    send_notification("Enhanced FlightAlert Started", "Service is up with pattern detection enabled.", email_cfg)
    notify_service_start()
    Thread(target=alive_notification, args=(email_cfg, cfg.get('alive_interval',86400)), daemon=True).start()
    monitor_aircraft('127.0.0.1', 30002, ac_list, email_cfg, home_lat, home_lon, detected_file)