#!/usr/bin/env python3
"""
Test enhanced email alerts with celebrity context, news, and photo links
"""
import json
from email_service import EmailService
from config_manager import config

def test_celebrity_email():
    """Test email generation for celebrity aircraft"""

    # Load aircraft list
    with open('/home/kurt/flighttrak/aircraft_list.json') as f:
        data = json.load(f)

    # Find Taylor Swift's aircraft
    taylor_swift = None
    for aircraft in data['aircraft_to_detect']:
        if aircraft['tail_number'] == 'N621MM':
            taylor_swift = aircraft
            break

    if not taylor_swift:
        print("✗ Taylor Swift aircraft not found")
        return False

    # Create test aircraft data (simulated ADS-B data)
    test_aircraft = {
        'hex': 'A81B13',
        'flight': 'N621MM',
        'lat': 40.7128,
        'lon': -74.0060,
        'alt_baro': 38000,
        'gs': 520,
        'track': 90,
        'baro_rate': 0,
        'squawk': '1200'
    }

    # Create email service
    email_config = config.get_email_config()
    email_service = EmailService(email_config)

    # Generate HTML (don't send, just test generation)
    try:
        html = email_service._generate_aircraft_alert_html(
            test_aircraft,
            taylor_swift,
            distance=47.3,
            flight_plan=None
        )

        # Check for key features
        checks = {
            'Celebrity Context Box': '💎 Celebrity Aircraft Details' in html,
            'Net Worth': '$1.1 billion' in html,
            'Aircraft Value': '$54 million' in html,
            'Specs Table': '5,950 nautical miles' in html,
            'Fun Facts': 'Most tracked celebrity jet' in html,
            'Wikipedia Link': 'wikipedia.org' in html,
            'Photo Links - JetPhotos': 'jetphotos.com' in html,
            'Photo Links - Planespotters': 'planespotters.net' in html,
            'Flight Tracking Links': 'flightaware.com' in html
        }

        print("\n✅ Email Template Generation Test Results:\n")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            if not passed:
                all_passed = False

        # Save HTML for manual inspection
        with open('/tmp/test_email_taylor_swift.html', 'w') as f:
            f.write(html)
        print(f"\n✓ Full email saved to: /tmp/test_email_taylor_swift.html")
        print("  (Open in browser to see formatted email)")

        return all_passed

    except Exception as e:
        print(f"\n✗ Error generating email: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Testing enhanced email alerts...")
    success = test_celebrity_email()

    if success:
        print("\n🎉 All enhancements working correctly!")
    else:
        print("\n⚠️  Some checks failed - review output above")

    exit(0 if success else 1)
