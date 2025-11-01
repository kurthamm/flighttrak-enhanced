#!/usr/bin/env python3
"""
Test script for health monitoring diagnostics
Run this to see what the diagnostic system would detect
"""

import sys
from flight_monitor import FlightMonitor
from email_service import EmailService
from config_manager import config

def main():
    print("=" * 70)
    print("FlightTrak Health Monitoring Diagnostics Test")
    print("=" * 70)
    print()

    # Create monitor instance
    print("Initializing FlightMonitor...")
    monitor = FlightMonitor()
    print("✓ Monitor initialized")
    print()

    # Run diagnostics
    print("Running system diagnostics...")
    print("-" * 70)
    diagnostics = monitor._run_diagnostics()

    # Display results
    status_symbols = {
        'ok': '✅',
        'warning': '⚠️',
        'failed': '❌',
        'skipped': '⏭️',
        'unknown': '❓'
    }

    all_ok = True
    failed_checks = []

    check_names = {
        'network': 'Internet Connectivity',
        'planes_url': 'planes.hamm.me Data Source',
        'dump1090_service': 'dump1090 Systemd Service',
        'dump1090_port': 'ADS-B Receiver Port'
    }

    for check_key, check_name in check_names.items():
        if check_key in diagnostics:
            result = diagnostics[check_key]
            status = result['status']
            details = result['details']
            symbol = status_symbols.get(status, '❓')

            print(f"{symbol} {check_name}")
            print(f"   Status: {status.upper()}")
            print(f"   Details: {details}")
            print()

            if status in ['failed', 'warning']:
                all_ok = False
                failed_checks.append((check_name, status, details))

    print("-" * 70)
    print()

    # Summary
    if all_ok:
        print("✅ All systems operational!")
        print("   No health alerts would be sent (assuming aircraft are being detected)")
    else:
        print("⚠️  ISSUES DETECTED!")
        print()
        print("Root Cause Analysis:")
        print("-" * 70)

        for check_name, status, details in failed_checks:
            print(f"• {check_name}: {status.upper()}")
            print(f"  {details}")
            print()

        print("-" * 70)
        print()
        print("If no aircraft are detected for 60+ minutes, you will receive an")
        print("email alert with these diagnostic results and recommended actions.")

    print()
    print("=" * 70)
    print("Configuration:")
    print(f"  Alert Threshold: {config.get('alerts.health_monitoring.no_aircraft_threshold_minutes', 60)} minutes")
    print(f"  Alert Cooldown: {config.get('alerts.health_monitoring.alert_cooldown_hours', 4)} hours")
    print(f"  Recipients: {', '.join(config.get_alert_recipients('health_monitoring'))}")
    print("=" * 70)

if __name__ == '__main__':
    main()
