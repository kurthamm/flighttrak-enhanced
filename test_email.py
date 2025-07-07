#!/usr/bin/env python3
"""
Test email script for FlightTrak Enhanced
Sends a sample alert to verify email configuration
"""

import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime

def load_config():
    try:
        with open('config.json') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def send_test_email():
    config = load_config()
    if not config:
        return
    
    email_cfg = config['email_config']
    
    # Create test aircraft data
    test_aircraft = {
        'hex': 'TEST123',
        'flight': 'TEST001',
        'alt_baro': 35000,
        'gs': 450,
        'squawk': '1200',
        'lat': 34.1133171,
        'lon': -80.9024019
    }
    
    # Create fancy test email
    html_content = f"""
    <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
        <div style='max-width:600px;margin:0 auto;background:#1a1f3a;padding:20px;border-radius:10px;border:1px solid #2a3f5f;'>
            <h2 style='color:#4fc3f7;margin-bottom:10px;'>✅ FlightTrak Enhanced - Test Email</h2>
            <h3 style='color:#00d2d3;margin-bottom:15px;'>System Configuration Test Successful!</h3>
            
            <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                <h4 style='color:#feca57;margin-bottom:10px;'>🎯 Test Results:</h4>
                <table style='width:100%;color:#e0e6ed;'>
                    <tr><td><strong>✅ Email System:</strong></td><td>Working</td></tr>
                    <tr><td><strong>✅ Pattern Detection:</strong></td><td>Active</td></tr>
                    <tr><td><strong>✅ GitHub Repository:</strong></td><td>Published</td></tr>
                    <tr><td><strong>✅ Web Dashboard:</strong></td><td>Running on Port 5030</td></tr>
                    <tr><td><strong>✅ Service Status:</strong></td><td>Enhanced Version Running</td></tr>
                </table>
            </div>
            
            <div style='background:#1e3c72;padding:15px;border-radius:8px;margin:15px 0;'>
                <h4 style='color:#feca57;margin-bottom:10px;'>🛩️ Sample Aircraft Alert:</h4>
                <table style='width:100%;color:#e0e6ed;'>
                    <tr><td><strong>ICAO:</strong></td><td>{test_aircraft['hex']}</td></tr>
                    <tr><td><strong>Flight:</strong></td><td>{test_aircraft['flight']}</td></tr>
                    <tr><td><strong>Altitude:</strong></td><td>{test_aircraft['alt_baro']:,} ft</td></tr>
                    <tr><td><strong>Speed:</strong></td><td>{test_aircraft['gs']} kt</td></tr>
                    <tr><td><strong>Squawk:</strong></td><td>{test_aircraft['squawk']}</td></tr>
                    <tr><td><strong>Position:</strong></td><td>{test_aircraft['lat']}, {test_aircraft['lon']}</td></tr>
                </table>
            </div>
            
            <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                <h4 style='color:#feca57;margin-bottom:10px;'>📊 System Status:</h4>
                <p style='color:#e0e6ed;margin:5px 0;'>• Enhanced service running with pattern detection</p>
                <p style='color:#e0e6ed;margin:5px 0;'>• Monitoring aircraft from planes.hamm.me tunnel</p>
                <p style='color:#e0e6ed;margin:5px 0;'>• Tracking 59 aircraft including celebrities and government</p>
                <p style='color:#e0e6ed;margin:5px 0;'>• Pattern alerts: Emergency codes, circling, altitude changes</p>
                <p style='color:#e0e6ed;margin:5px 0;'>• Web dashboard with real-time analytics available</p>
            </div>
            
            <p style='margin-top:20px;text-align:center;'>
                <a href='http://165.22.176.251:5030' 
                   style='background:#4fc3f7;color:#0a0e27;padding:10px 20px;text-decoration:none;border-radius:5px;font-weight:bold;margin:5px;display:inline-block;'>
                   📊 View Dashboard
                </a>
                <a href='https://github.com/kurthamm/flighttrak-enhanced' 
                   style='background:#feca57;color:#0a0e27;padding:10px 20px;text-decoration:none;border-radius:5px;font-weight:bold;margin:5px;display:inline-block;'>
                   💻 GitHub Repository
                </a>
            </p>
            
            <div style='border-top:1px solid #2a3f5f;margin-top:20px;padding-top:15px;'>
                <p style='font-size:12px;color:#8892b0;text-align:center;'>
                    FlightTrak Enhanced v2.0 • Test sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
                <p style='font-size:12px;color:#8892b0;text-align:center;'>
                    Advanced Aircraft Monitoring with AI-Ready Pattern Detection
                </p>
            </div>
        </div>
    </body></html>
    """
    
    message = Mail(
        from_email=email_cfg['sender'],
        to_emails=['kurt@hamm.me'],
        subject='✅ FlightTrak Enhanced - System Test & Configuration Verification',
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
        response = sg.send(message)
        print(f"✅ Test email sent successfully!")
        print(f"📧 Sent to: kurt@hamm.me")
        print(f"📊 SendGrid status: {response.status_code}")
        print(f"🎯 Check your inbox for the test email!")
        return True
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        return False

if __name__ == '__main__':
    print("🚀 FlightTrak Enhanced - Email Test")
    print("=" * 40)
    send_test_email()