#!/usr/bin/env python3
"""Test tracked aircraft alerting"""

import logging
from config_manager import config
from email_service import EmailService

# Setup logging
logging.basicConfig(level=logging.INFO)

# Simulate Tommy Hilfiger's aircraft
test_aircraft = {
    'hex': 'a6f2b7',
    'flight': 'N818TH',
    'alt_baro': 35000,
    'gs': 450.5,
    'lat': 34.5,
    'lon': -80.5,
    'squawk': '1234',
    'track': 270,
    'baro_rate': 0
}

tracked_info = {
    'icao': 'A6F2B7',
    'tail_number': 'N818TH',
    'description': "Tommy Hilfiger's Falcon 900 with custom nautical interior",
    'owner': 'Tommy Hilfiger',
    'model': 'Dassault Falcon 900'
}

distance = 25.5  # miles from home

# Get configuration
recipients = config.get_alert_recipients('tracked_aircraft')
print(f"Alert recipients: {recipients}")
print(f"Alert enabled: {config.is_alert_enabled('tracked_aircraft')}")

if not recipients:
    print("ERROR: No recipients configured!")
    exit(1)

# Initialize email service
email_service = EmailService(config.get_email_config())

# Send test alert
print("\nSending test tracked aircraft alert...")
success = email_service.send_aircraft_alert(
    test_aircraft, tracked_info, distance, recipients
)

if success:
    print("SUCCESS: Alert sent!")
else:
    print("FAILED: Alert not sent")
