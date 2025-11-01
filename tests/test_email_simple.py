#!/usr/bin/env python3
"""Simple email test for FlightTrak using the actual EmailService"""

import sys
sys.path.insert(0, '/home/kurt/flighttrak')

from config_manager import config
from email_service import EmailService

def test_email():
    print("🧪 Testing FlightTrak Email Configuration")
    print("=" * 50)
    
    # Get email config
    email_config = config.get_email_config()
    print(f"📧 Email sender: {email_config.get('sender')}")
    print(f"🔧 SMTP server: {email_config.get('smtp_server')}:{email_config.get('smtp_port')}")
    
    # Initialize email service
    try:
        email_service = EmailService(email_config)
        print("✅ Email service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize email service: {e}")
        return False
    
    # Create test aircraft data
    test_aircraft = {
        'hex': 'A6F2B7',
        'flight': 'TEST001',
        'alt_baro': 35000,
        'gs': 450.5,
        'squawk': '1200',
        'lat': 34.5,
        'lon': -81.0,
        'track': 180,
        'vert_rate': 0
    }
    
    test_tracked_info = {
        'tail_number': 'N818TH',
        'model': 'Dassault Falcon 900',
        'owner': 'Tommy Hilfiger',
        'description': 'TEST: Tommy Hilfiger\'s Falcon 900 with custom nautical interior'
    }
    
    test_distance = 42.5
    
    # Send test email
    print("\n📨 Sending test aircraft alert...")
    recipients = ['kurt@hamm.me']
    
    success = email_service.send_aircraft_alert(
        test_aircraft,
        test_tracked_info,
        test_distance,
        recipients
    )
    
    if success:
        print("✅ TEST EMAIL SENT SUCCESSFULLY!")
        print(f"📬 Check {recipients[0]} for the test alert")
        return True
    else:
        print("❌ Failed to send test email")
        return False

if __name__ == '__main__':
    test_email()
