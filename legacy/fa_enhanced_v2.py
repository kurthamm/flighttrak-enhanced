#!/usr/bin/env python3
import socket
import json
import time
import os
import subprocess
import logging
import math
import requests
from datetime import datetime, timedelta
from threading import Thread
from collections import defaultdict, deque
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import our advanced anomaly detector
try:
    from anomaly_detector import FlightAnomalyDetector
    ANOMALY_DETECTION_ENABLED = True
except ImportError as e:
    logging.warning(f"Anomaly detection disabled: {e}")
    ANOMALY_DETECTION_ENABLED = False

def send_gmail_smtp(to_emails, subject, html_content, email_cfg):
    """Send email using Gmail SMTP instead of SendGrid"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_cfg['sender']
        msg['Subject'] = subject
        
        # Handle multiple recipients
        if isinstance(to_emails, list):
            msg['To'] = ', '.join(to_emails)
            recipients = to_emails
        else:
            msg['To'] = to_emails
            recipients = [to_emails]
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Connect to Gmail SMTP
        server = smtplib.SMTP(email_cfg['smtp_server'], email_cfg['smtp_port'])
        server.starttls()  # Enable TLS encryption
        server.login(email_cfg['sender'], email_cfg['password'])
        
        # Send email
        server.send_message(msg, to_addrs=recipients)
        server.quit()
        
        logging.info(f"Email sent successfully via Gmail SMTP to {recipients}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending email via Gmail SMTP: {e}")
        return False

# Set up logging
logging.basicConfig(
    filename='flightalert.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logging.info("Starting Enhanced Flight Alert service v3 with Gmail SMTP.")

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

# Data management settings
DATA_CULL_INTERVAL = 86400  # Cull data every 24 hours (daily)
MAX_DETECTED_DAYS = 7       # Keep detections for 7 days
MAX_FILE_SIZE_MB = 5        # Rotate when file exceeds 5MB

def haversine_miles(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    dist_km = R_km * c
    return dist_km * 0.621371

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {path}: {e}")
        return None

def cull_old_detections(detected_file, max_age_days=7):
    """Remove old detections and keep only recent ones"""
    if not os.path.exists(detected_file):
        return 0
    
    # Create timestamped detected aircraft file
    timestamped_file = detected_file + '.timestamped'
    current_time = time.time()
    cutoff_time = current_time - (max_age_days * 24 * 60 * 60)
    
    kept_count = 0
    removed_count = 0
    
    # Read existing data
    try:
        with open(detected_file, 'r') as f:
            detected_aircraft = [line.strip() for line in f if line.strip()]
    except:
        return 0
    
    # If we don't have timestamped data, create it from scratch
    if not os.path.exists(timestamped_file):
        # For existing detections, assume they're all recent
        with open(timestamped_file, 'w') as f:
            for icao in detected_aircraft:
                f.write(f"{icao},{current_time}\n")
        logging.info(f"Created timestamped detection file with {len(detected_aircraft)} aircraft")
        return 0
    
    # Read timestamped data and filter
    recent_aircraft = []
    try:
        with open(timestamped_file, 'r') as f:
            for line in f:
                line = line.strip()
                if ',' in line:
                    icao, timestamp_str = line.split(',', 1)
                    try:
                        timestamp = float(timestamp_str)
                        if timestamp >= cutoff_time:
                            recent_aircraft.append(icao)
                            kept_count += 1
                        else:
                            removed_count += 1
                    except ValueError:
                        # Invalid timestamp, keep it
                        recent_aircraft.append(icao)
                        kept_count += 1
    except:
        return 0
    
    # Update both files
    with open(detected_file, 'w') as f:
        for icao in recent_aircraft:
            f.write(f"{icao}\n")
    
    with open(timestamped_file, 'w') as f:
        for icao in recent_aircraft:
            f.write(f"{icao},{current_time}\n")
    
    if removed_count > 0:
        logging.info(f"Data culling: kept {kept_count}, removed {removed_count} old detections")
    
    return removed_count

def add_timestamped_detection(icao, detected_file):
    """Add detection with timestamp"""
    timestamped_file = detected_file + '.timestamped'
    current_time = time.time()
    
    # Add to regular file
    with open(detected_file, 'a') as f:
        f.write(f"{icao}\n")
    
    # Add to timestamped file
    with open(timestamped_file, 'a') as f:
        f.write(f"{icao},{current_time}\n")

def auto_data_management(detected_file):
    """Background thread for automatic data management"""
    logging.info(f"Starting auto data management thread (interval: {DATA_CULL_INTERVAL/3600:.1f} hours)")
    
    while True:
        time.sleep(DATA_CULL_INTERVAL)
        
        try:
            # Check file size
            if os.path.exists(detected_file):
                file_size_mb = os.path.getsize(detected_file) / (1024 * 1024)
                
                if file_size_mb > MAX_FILE_SIZE_MB:
                    logging.info(f"File size {file_size_mb:.1f}MB exceeds limit {MAX_FILE_SIZE_MB}MB")
                
                # Cull old data
                removed = cull_old_detections(detected_file, MAX_DETECTED_DAYS)
                
                # Log status
                try:
                    with open(detected_file, 'r') as f:
                        current_count = sum(1 for line in f if line.strip())
                    final_size_mb = os.path.getsize(detected_file) / (1024 * 1024)
                    logging.info(f"Data management complete: {current_count} aircraft, {final_size_mb:.1f}MB")
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"Error in auto data management: {e}")

def send_pattern_alert(event_type, description, aircraft_data, email_cfg):
    """Send email alert for interesting patterns"""
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
                FlightTrak Enhanced v3 with Advanced Anomaly Detection
            </p>
        </div>
    </body></html>
    """
    
    try:
        success = send_gmail_smtp(
            to_emails=email_cfg['recipients'],
            subject=f"FlightTrak Pattern Alert: {event_type} - {aircraft_data.get('hex', 'Unknown')}",
            html_content=html_content,
            email_cfg=email_cfg
        )
        if success:
            logging.info(f"Pattern alert sent for {event_type}: {aircraft_data.get('hex', 'Unknown')}")
    except Exception as e:
        logging.error(f"Error sending pattern alert: {e}")

def send_anomaly_alert(anomaly, email_cfg):
    """Send email alert for detected anomalies"""
    severity_colors = {
        'CRITICAL': '#ff4757',
        'HIGH': '#ff6b6b', 
        'MEDIUM': '#ffa502',
        'LOW': '#3742fa'
    }
    
    severity_emojis = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '🔍',
        'LOW': '📊'
    }
    
    color = severity_colors.get(anomaly['severity'], '#666')
    emoji = severity_emojis.get(anomaly['severity'], '🔍')
    
    aircraft = anomaly['aircraft']
    
    html_content = f"""
    <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
        <div style='max-width:600px;margin:0 auto;background:#1a1f3a;padding:20px;border-radius:10px;border:1px solid #2a3f5f;'>
            <h2 style='color:{color};margin-bottom:10px;'>{emoji} FlightTrak Anomaly Alert</h2>
            <h3 style='color:#4fc3f7;margin-bottom:15px;'>{anomaly['type']}: {anomaly['description']}</h3>
            
            <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                <h4 style='color:#feca57;margin-bottom:10px;'>Severity: <span style='color:{color};'>{anomaly['severity']}</span></h4>
                <h4 style='color:#feca57;margin-bottom:10px;'>Aircraft Details:</h4>
                <table style='width:100%;color:#e0e6ed;'>
                    <tr><td><strong>ICAO:</strong></td><td>{aircraft.get('hex', 'N/A')}</td></tr>
                    <tr><td><strong>Flight:</strong></td><td>{aircraft.get('flight', 'N/A')}</td></tr>
                    <tr><td><strong>Altitude:</strong></td><td>{aircraft.get('alt_baro', 'N/A')} ft</td></tr>
                    <tr><td><strong>Speed:</strong></td><td>{aircraft.get('gs', 'N/A')} kt</td></tr>
                    <tr><td><strong>Squawk:</strong></td><td>{aircraft.get('squawk', 'N/A')}</td></tr>
                    <tr><td><strong>Vertical Rate:</strong></td><td>{aircraft.get('baro_rate', 'N/A')} ft/min</td></tr>
                </table>
            </div>
            
            <p style='margin-top:20px;text-align:center;'>
                <a href='https://flightaware.com/live/flight/{aircraft.get("flight", "")}' 
                   style='background:#4fc3f7;color:#0a0e27;padding:10px 20px;text-decoration:none;border-radius:5px;font-weight:bold;'>
                   Track on FlightAware
                </a>
            </p>
            
            <p style='font-size:12px;color:#8892b0;text-align:center;margin-top:20px;'>
                FlightTrak Advanced Anomaly Detection System
            </p>
        </div>
    </body></html>
    """
    
    try:
        success = send_gmail_smtp(
            to_emails=email_cfg['recipients'],
            subject=f"FlightTrak Anomaly: {anomaly['type']} - {aircraft.get('hex', 'Unknown')} [{anomaly['severity']}]",
            html_content=html_content,
            email_cfg=email_cfg
        )
        if success:
            logging.info(f"Anomaly alert sent for {anomaly['type']}: {aircraft.get('hex', 'Unknown')}")
    except Exception as e:
        logging.error(f"Error sending anomaly alert: {e}")

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
        
        # Check for rapid altitude changes (reduce frequency of logging)
        if len(stats_data['altitudes']) >= 5:
            alts = list(stats_data['altitudes'])
            alt_change = max(alts) - min(alts)
            if alt_change > 10000:  # Increased threshold to reduce spam
                stats_data['rapid_changes'] += 1
                # Only log once per aircraft per session
                if stats_data['rapid_changes'] == 1:
                    description = f"Rapid altitude change: {alt_change}ft detected"
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

def send_notification(subject, body, email_cfg):
    try:
        success = send_gmail_smtp(
            to_emails=email_cfg['notification_email'],
            subject=subject,
            html_content=f"<p>{body}</p>",
            email_cfg=email_cfg
        )
        if success:
            logging.info(f"Notification '{subject}' sent")
    except Exception as e:
        logging.error(f"Error sending notification '{subject}': {e}")

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

    try:
        success = send_gmail_smtp(
            to_emails=email_cfg['recipients'],
            subject=f"Aircraft Alert: {owner} (ICAO: {icao})",
            html_content=content,
            email_cfg=email_cfg
        )
        if success:
            logging.info(f"Alert email sent for {icao}")
    except Exception as e:
        logging.error(f"Error sending alert email for {icao}: {e}")

def alive_notification(cfg, interval):
    while True:
        send_notification("Enhanced FlightAlert is alive", f"Service running with auto data management (keeping {MAX_DETECTED_DAYS} days of data).", cfg)
        time.sleep(interval)

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

def monitor_aircraft(host, port, ac_list, cfg, home_lat, home_lon, detected_file):
    detected = set(open(detected_file).read().splitlines()) if os.path.exists(detected_file) else set()
    PLANES_URL = 'https://planes.hamm.me/data/aircraft.json'
    
    # Initialize anomaly detector
    anomaly_detector = None
    if ANOMALY_DETECTION_ENABLED:
        try:
            anomaly_detector = FlightAnomalyDetector(home_lat, home_lon)
            logging.info("Advanced anomaly detection system initialized")
        except Exception as e:
            logging.error(f"Failed to initialize anomaly detector: {e}")
            anomaly_detector = None
    
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
    logging.info(f"Auto data management: keeping {MAX_DETECTED_DAYS} days, culling every {DATA_CULL_INTERVAL/3600:.1f} hours")
    if anomaly_detector:
        logging.info("Advanced anomaly detection: ENABLED")
    else:
        logging.info("Advanced anomaly detection: DISABLED")
    
    # Start auto data management thread
    data_mgmt_thread = Thread(target=auto_data_management, args=(detected_file,), daemon=True)
    data_mgmt_thread.start()
    
    # Track anomaly alert frequency to prevent spam
    anomaly_alert_cooldown = defaultdict(float)
    ALERT_COOLDOWN_SECONDS = 300  # 5 minutes between same type of alerts for same aircraft
    
    while True:
        try:
            response = requests.get(PLANES_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Analyze ALL aircraft for patterns, not just tracked ones
            for aircraft in data.get('aircraft', []):
                if aircraft.get('hex'):
                    # Original pattern analysis
                    analyze_aircraft_patterns(aircraft, cfg, home_lat, home_lon)
                    
                    # Advanced anomaly detection
                    if anomaly_detector:
                        try:
                            anomalies = anomaly_detector.analyze_aircraft(aircraft)
                            for anomaly in anomalies:
                                # Check cooldown to prevent spam
                                hex_code = aircraft.get('hex', '')
                                anomaly_key = f"{hex_code}_{anomaly['type']}"
                                current_time = time.time()
                                
                                if current_time - anomaly_alert_cooldown[anomaly_key] > ALERT_COOLDOWN_SECONDS:
                                    anomaly_alert_cooldown[anomaly_key] = current_time
                                    
                                    # Send alert for high priority anomalies
                                    if anomaly['severity'] in ['CRITICAL', 'HIGH']:
                                        send_anomaly_alert(anomaly, cfg)
                                    
                                    # Log all anomalies
                                    logging.warning(f"ANOMALY DETECTED: {anomaly['type']} - {anomaly['description']} "
                                                  f"[{anomaly['severity']}] - Aircraft: {hex_code}")
                        except Exception as e:
                            logging.error(f"Error in anomaly detection for {aircraft.get('hex', 'unknown')}: {e}")
            
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
                            add_timestamped_detection(icao, detected_file)
                            
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
    send_notification("Enhanced FlightAlert v3 Started", f"Service is up with advanced anomaly detection and auto data management (keeping {MAX_DETECTED_DAYS} days of detections).", email_cfg)
    notify_service_start()
    Thread(target=alive_notification, args=(email_cfg, cfg.get('alive_interval',86400)), daemon=True).start()
    monitor_aircraft('127.0.0.1', 30002, ac_list, email_cfg, home_lat, home_lon, detected_file)