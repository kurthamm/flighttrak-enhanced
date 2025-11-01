#!/usr/bin/env python3
"""
Weekly Summary Report for FlightTrak
Generates and emails a comprehensive report of all detections and alerts from the past week
Runs every Sunday at midnight EST
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from config_manager import config
from email_service import EmailService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weekly_report.log'),
        logging.StreamHandler()
    ]
)

def parse_detection_line(line):
    """Parse a JSON line from detected_aircraft.txt"""
    try:
        # Parse JSON format from flight_monitor.py
        # Format: {"timestamp": "ISO date", "icao": "HEX", "registration": "N123",
        #          "description": "Owner - Model", "flight": "ABC123", "altitude": 35000,
        #          "speed": 450, "distance": 25.5, "squawk": "1234"}
        data = json.loads(line.strip())

        # Parse timestamp
        timestamp = datetime.fromisoformat(data['timestamp'])

        # Get tracked aircraft info
        icao = data.get('icao', 'Unknown').upper()

        # Parse description to extract owner and model
        description = data.get('description', 'Unknown')
        if ' - ' in description:
            parts = description.split(' - ', 1)
            owner = parts[0]
            model = parts[1] if len(parts) > 1 else 'Unknown'
        else:
            owner = description
            model = 'Unknown'

        return {
            'timestamp': timestamp,
            'tail_number': data.get('registration', 'Unknown'),
            'icao': icao,
            'owner': owner,
            'model': model,
            'distance': float(data.get('distance', 0)),
            'description': description,
            'flight': data.get('flight', 'N/A')
        }
    except Exception as e:
        logging.debug(f"Could not parse line: {line[:100]} - {e}")
        return None

def load_detections_from_file(start_date, end_date):
    """Load detections from detected_aircraft.txt within date range"""
    detections = []
    detection_file = Path('detected_aircraft.txt')

    if not detection_file.exists():
        logging.warning(f"Detection file not found: {detection_file}")
        return detections

    try:
        with open(detection_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                detection = parse_detection_line(line)
                if detection and start_date <= detection['timestamp'] <= end_date:
                    detections.append(detection)
    except Exception as e:
        logging.error(f"Error reading detection file: {e}")

    return detections

def load_emergency_events(start_date, end_date):
    """Load emergency events from emergency_events.json"""
    emergencies = []
    emergency_file = Path('emergency_events.json')

    if not emergency_file.exists():
        logging.info(f"Emergency events file not found: {emergency_file}")
        return emergencies

    try:
        with open(emergency_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    # Parse JSON format from flight_monitor.py
                    # Format: {"timestamp": "ISO date", "icao": "HEX", "squawk": "7700",
                    #          "type": "EMERGENCY", "description": "...", ...}
                    data = json.loads(line.strip())

                    # Parse timestamp
                    timestamp = datetime.fromisoformat(data['timestamp'])

                    if start_date <= timestamp <= end_date:
                        emergencies.append({
                            'timestamp': timestamp,
                            'icao': data.get('icao', 'Unknown').upper(),
                            'squawk': data.get('squawk', 'Unknown'),
                            'type': data.get('type', 'Unknown'),
                            'description': data.get('description', ''),
                            'flight': data.get('flight', 'N/A'),
                            'altitude': data.get('altitude', 'N/A'),
                            'speed': data.get('speed', 'N/A')
                        })
                except Exception as e:
                    logging.debug(f"Could not parse emergency event line: {line[:100]} - {e}")

    except Exception as e:
        logging.error(f"Error reading emergency events file: {e}")

    return emergencies

def generate_weekly_summary():
    """Generate weekly summary report"""
    # Calculate date range (Monday - Sunday of previous week)
    today = datetime.now()
    # Get last Sunday at midnight
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    end_date = last_sunday.replace(hour=23, minute=59, second=59, microsecond=0)

    # Get Monday of that week
    start_date = end_date - timedelta(days=6)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    logging.info(f"Generating weekly report for {start_date.date()} to {end_date.date()}")

    # Load detections and emergencies
    detections = load_detections_from_file(start_date, end_date)
    emergencies = load_emergency_events(start_date, end_date)

    if not detections and not emergencies:
        logging.info("No detections or emergencies found for this week")
        return None

    # Analyze detections
    summary = {
        'start_date': start_date,
        'end_date': end_date,
        'total_detections': len(detections),
        'unique_aircraft': len(set(d['icao'] for d in detections)) if detections else 0,
        'total_emergencies': len(emergencies),
        'by_aircraft': defaultdict(list),
        'by_day': defaultdict(int),
        'closest_approach': None,
        'most_detected': None,
        'emergencies': emergencies
    }

    # Group by aircraft
    for detection in detections:
        key = detection['icao']
        summary['by_aircraft'][key].append(detection)

        # Track by day
        day_key = detection['timestamp'].strftime('%A')
        summary['by_day'][day_key] += 1

        # Track closest approach
        if summary['closest_approach'] is None or detection['distance'] < summary['closest_approach']['distance']:
            summary['closest_approach'] = detection

    # Find most frequently detected
    if summary['by_aircraft']:
        detection_counts = {icao: len(detections) for icao, detections in summary['by_aircraft'].items()}
        most_detected_icao = max(detection_counts, key=detection_counts.get)
        summary['most_detected'] = {
            'icao': most_detected_icao,
            'count': detection_counts[most_detected_icao],
            'aircraft': summary['by_aircraft'][most_detected_icao][0]
        }

    return summary, detections

def format_html_report(summary, detections):
    """Format weekly summary as HTML email"""
    if not summary:
        return None

    start_str = summary['start_date'].strftime('%B %d, %Y')
    end_str = summary['end_date'].strftime('%B %d, %Y')

    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 16px;
                opacity: 0.9;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }}
            .stat-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #4a90e2;
                text-align: center;
            }}
            .stat-value {{
                font-size: 36px;
                font-weight: bold;
                color: #4a90e2;
                margin-bottom: 5px;
            }}
            .stat-label {{
                color: #666;
                font-size: 14px;
            }}
            .section {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .section h2 {{
                margin-top: 0;
                color: #1e3c72;
                border-bottom: 2px solid #4a90e2;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background: #f8f9fa;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #e0e0e0;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #f0f0f0;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            .highlight {{
                background: #fff3cd;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                margin: 15px 0;
            }}
            .highlight h3 {{
                margin-top: 0;
                color: #856404;
            }}
            .aircraft-name {{
                font-weight: bold;
                color: #1e3c72;
            }}
            .distance-close {{
                color: #dc3545;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 2px solid #e0e0e0;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✈️ FlightTrak Weekly Summary</h1>
            <p>{start_str} - {end_str}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{summary['total_detections']}</div>
                <div class="stat-label">Total Detections</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['unique_aircraft']}</div>
                <div class="stat-label">Unique Aircraft</div>
            </div>
            <div class="stat-card" style="border-left-color: #dc3545;">
                <div class="stat-value" style="color: #dc3545;">{summary['total_emergencies']}</div>
                <div class="stat-label">Emergency Alerts</div>
            </div>
        </div>

        <div class="section">
            <h2>🏆 Highlights</h2>
    """

    # Add highlights only if there were detections
    if summary['most_detected']:
        html += f"""
            <div class="highlight">
                <h3>Most Frequently Detected</h3>
                <p>
                    <span class="aircraft-name">{summary['most_detected']['aircraft']['owner']}</span>
                    ({summary['most_detected']['aircraft']['tail_number']})
                    <br>
                    <strong>{summary['most_detected']['count']} detections</strong> this week
                    <br>
                    {summary['most_detected']['aircraft']['model']}
                </p>
            </div>
    """

    if summary['closest_approach']:
        html += f"""
            <div class="highlight">
                <h3>Closest Approach</h3>
                <p>
                    <span class="aircraft-name">{summary['closest_approach']['owner']}</span>
                    ({summary['closest_approach']['tail_number']})
                    <br>
                    <span class="distance-close">{summary['closest_approach']['distance']:.1f} miles</span>
                    <br>
                    {summary['closest_approach']['timestamp'].strftime('%A, %B %d at %I:%M %p')}
                </p>
            </div>
    """

    if not summary['most_detected'] and not summary['closest_approach']:
        html += """
            <p style="text-align: center; color: #666; padding: 20px;">
                No tracked aircraft detections this week, but see emergency alerts below.
            </p>
    """

    html += """
        </div>
    """

    # Add emergency alerts section if any emergencies occurred
    if summary['emergencies']:
        html += """
        <div class="section">
            <h2>🚨 Emergency Alerts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date/Time</th>
                        <th>Aircraft</th>
                        <th>Squawk Code</th>
                        <th>Emergency Type</th>
                    </tr>
                </thead>
                <tbody>
    """
        for emergency in summary['emergencies']:
            emergency_colors = {
                'HIJACK': '#8b0000',
                'RADIO FAILURE': '#ff8c00',
                'EMERGENCY': '#dc3545',
                'MILITARY INTERCEPT': '#6a0dad'
            }
            color = emergency_colors.get(emergency['type'], '#dc3545')

            html += f"""
                    <tr style="border-left: 4px solid {color};">
                        <td>{emergency['timestamp'].strftime('%A, %B %d at %I:%M %p')}</td>
                        <td style="font-family: monospace;">{emergency['icao']}</td>
                        <td style="font-weight: bold; color: {color};">{emergency['squawk']}</td>
                        <td style="color: {color};">{emergency['type']}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
    """

    html += """
        <div class="section">
            <h2>📊 Detections by Day</h2>
            <table>
                <thead>
                    <tr>
                        <th>Day</th>
                        <th>Detections</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Add day-by-day breakdown
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days_order:
        count = summary['by_day'].get(day, 0)
        html += f"""
                    <tr>
                        <td>{day}</td>
                        <td>{count}</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🛩️ All Detected Aircraft</h2>
            <table>
                <thead>
                    <tr>
                        <th>Aircraft</th>
                        <th>Owner</th>
                        <th>Model</th>
                        <th>Detections</th>
                        <th>Closest</th>
                    </tr>
                </thead>
                <tbody>
    """

    # Sort aircraft by number of detections (descending)
    sorted_aircraft = sorted(
        summary['by_aircraft'].items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    for icao, aircraft_detections in sorted_aircraft:
        first = aircraft_detections[0]
        count = len(aircraft_detections)
        closest = min(d['distance'] for d in aircraft_detections)

        html += f"""
                    <tr>
                        <td>{first['tail_number']}</td>
                        <td class="aircraft-name">{first['owner']}</td>
                        <td>{first['model']}</td>
                        <td>{count}</td>
                        <td>{closest:.1f} mi</td>
                    </tr>
        """

    html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>FlightTrak Weekly Summary Report</p>
            <p>Tracking 69 celebrity, government, and historic aircraft</p>
        </div>
    </body>
    </html>
    """

    return html

def send_weekly_report():
    """Generate and send weekly summary report"""
    try:
        # Generate summary
        result = generate_weekly_summary()

        if result is None:
            logging.info("No detections this week, skipping report")
            return

        summary, detections = result

        # Format HTML report
        html_content = format_html_report(summary, detections)

        if not html_content:
            logging.warning("Could not generate HTML report")
            return

        # Get email configuration
        email_config = config.get_email_config()
        recipients = config.get_alert_recipients('tracked_aircraft')

        if not recipients:
            logging.error("No recipients configured for weekly report")
            return

        # Send email
        email_service = EmailService(email_config)

        start_str = summary['start_date'].strftime('%b %d')
        end_str = summary['end_date'].strftime('%b %d, %Y')
        subject = f"FlightTrak Weekly Summary: {start_str} - {end_str} ({summary['total_detections']} detections)"

        success = email_service.send_html_email(
            recipients=recipients,
            subject=subject,
            html_content=html_content
        )

        if success:
            logging.info(f"Weekly report sent successfully to {', '.join(recipients)}")
        else:
            logging.error("Failed to send weekly report")

    except Exception as e:
        logging.error(f"Error generating weekly report: {e}", exc_info=True)

if __name__ == '__main__':
    logging.info("Starting weekly report generation")
    send_weekly_report()
    logging.info("Weekly report generation complete")
