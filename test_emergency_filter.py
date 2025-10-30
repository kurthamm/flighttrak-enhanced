#!/usr/bin/env python3
"""
Test script to demonstrate emergency squawk false positive filtering
"""

from anomaly_detector import FlightAnomalyDetector

# Initialize detector with home coordinates
home_lat, home_lon = 40.7128, -74.0060  # Example: NYC

detector = FlightAnomalyDetector(home_lat, home_lon)

print("=" * 80)
print("Testing Emergency Squawk False Positive Filtering")
print("=" * 80)

# Test Case 1: FALSE POSITIVE - Landing approach near JFK
print("\n1. Aircraft landing at JFK (should be FILTERED as false positive)")
landing_aircraft = {
    'hex': 'ACAB11',
    'flight': 'UAL123',
    'squawk': '7600',  # Radio failure
    'alt_baro': 4150,  # Low altitude
    'baro_rate': -576,  # Descending
    'gs': 180,  # Approach speed
    'lat': 40.65,  # Near JFK
    'lon': -73.78
}
anomalies = detector.analyze_aircraft(landing_aircraft)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) == 0:
    print("   ✓ PASS - False positive correctly filtered")
else:
    print(f"   ✗ FAIL - Should have been filtered: {anomalies}")

# Test Case 2: GENUINE EMERGENCY - High altitude 7600
print("\n2. Aircraft at cruise altitude with 7600 (should be DETECTED)")
cruise_emergency = {
    'hex': 'ABC123',
    'flight': 'AAL456',
    'squawk': '7600',
    'alt_baro': 35000,  # Cruise altitude
    'baro_rate': -100,  # Slight descent
    'gs': 450,  # Cruise speed
    'lat': 40.0,
    'lon': -75.0
}
anomalies = detector.analyze_aircraft(cruise_emergency)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) > 0:
    print("   ✓ PASS - Genuine emergency detected")
    print(f"   Alert: {anomalies[0]['description']}")
else:
    print("   ✗ FAIL - Should have detected emergency")

# Test Case 3: GENUINE EMERGENCY - 7700 (always detected, never filtered)
print("\n3. Aircraft with 7700 general emergency (should ALWAYS be DETECTED)")
general_emergency = {
    'hex': 'DEF789',
    'flight': 'DAL789',
    'squawk': '7700',  # General emergency
    'alt_baro': 3000,  # Even at low altitude
    'baro_rate': -500,  # Even descending
    'gs': 150,
    'lat': 40.65,  # Even near airport
    'lon': -73.78
}
anomalies = detector.analyze_aircraft(general_emergency)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) > 0:
    print("   ✓ PASS - Emergency detected (7700 never filtered)")
    print(f"   Alert: {anomalies[0]['description']}")
else:
    print("   ✗ FAIL - Should have detected emergency")

# Test Case 4: FALSE POSITIVE - Low altitude, descending, no location data
print("\n4. Aircraft very low & descending, no location (should be FILTERED)")
low_descending = {
    'hex': 'GHI456',
    'flight': 'SWA321',
    'squawk': '7600',
    'alt_baro': 3500,  # Very low
    'baro_rate': -800,  # Fast descent
    'gs': 140
    # No lat/lon - can't confirm airport proximity
}
anomalies = detector.analyze_aircraft(low_descending)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) == 0:
    print("   ✓ PASS - False positive filtered (assumed landing)")
else:
    print(f"   ✗ FAIL - Should have been filtered: {anomalies}")

# Test Case 5: GENUINE EMERGENCY - 7600 but climbing
print("\n5. Aircraft with 7600 but CLIMBING (should be DETECTED)")
climbing_emergency = {
    'hex': 'JKL123',
    'flight': 'UAL999',
    'squawk': '7600',
    'alt_baro': 8000,
    'baro_rate': 1200,  # CLIMBING (positive rate)
    'gs': 200,
    'lat': 40.65,
    'lon': -73.78
}
anomalies = detector.analyze_aircraft(climbing_emergency)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) > 0:
    print("   ✓ PASS - Genuine emergency detected (climbing, not landing)")
    print(f"   Alert: {anomalies[0]['description']}")
else:
    print("   ✗ FAIL - Should have detected emergency")

# Test Case 6: FALSE POSITIVE - Descending near LAX
print("\n6. Aircraft landing at LAX (should be FILTERED)")
lax_landing = {
    'hex': 'MNO789',
    'flight': 'AAL100',
    'squawk': '7600',
    'alt_baro': 2500,
    'baro_rate': -650,
    'gs': 160,
    'lat': 33.95,  # Near LAX
    'lon': -118.40
}
anomalies = detector.analyze_aircraft(lax_landing)
print(f"   Result: {len(anomalies)} anomalies detected")
if len(anomalies) == 0:
    print("   ✓ PASS - False positive correctly filtered (LAX approach)")
else:
    print(f"   ✗ FAIL - Should have been filtered: {anomalies}")

print("\n" + "=" * 80)
print("Test Summary")
print("=" * 80)
print("The filter now intelligently distinguishes between:")
print("  • False positives: 7600 during landing approach (descending, low alt, near airport)")
print("  • Genuine emergencies: 7600 at cruise, or 7700/7500/7777 always")
print("\nThis should dramatically reduce false positive email alerts!")
print("=" * 80)
