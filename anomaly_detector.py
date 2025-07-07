#!/usr/bin/env python3
"""
Advanced Anomaly Detection System for FlightTrak
Detects unusual flight patterns, aviation safety concerns, and weird/interesting behaviors
"""

import json
import math
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
import numpy as np

class FlightAnomalyDetector:
    def __init__(self, home_lat, home_lon):
        self.home_lat = home_lat
        self.home_lon = home_lon
        
        # Aircraft tracking data
        self.aircraft_history = defaultdict(lambda: {
            'positions': deque(maxlen=100),
            'altitudes': deque(maxlen=50),
            'speeds': deque(maxlen=50),
            'headings': deque(maxlen=50),
            'vertical_rates': deque(maxlen=30),
            'callsigns': set(),
            'squawks': set(),
            'first_seen': None,
            'last_seen': None,
            'pattern_alerts': set(),
            'behavior_score': 0,
            'anomaly_count': 0
        })
        
        # Airport proximity data (example airports - expand as needed)
        self.airports = [
            {'icao': 'KJFK', 'lat': 40.6413, 'lon': -73.7781, 'name': 'JFK International'},
            {'icao': 'KLGA', 'lat': 40.7769, 'lon': -73.8740, 'name': 'LaGuardia'},
            {'icao': 'KEWR', 'lat': 40.6895, 'lon': -74.1745, 'name': 'Newark Liberty'},
            {'icao': 'KBOS', 'lat': 42.3656, 'lon': -71.0096, 'name': 'Boston Logan'},
            {'icao': 'KDCA', 'lat': 38.8512, 'lon': -77.0402, 'name': 'Reagan National'},
        ]
        
        # Military bases and restricted areas
        self.restricted_areas = [
            {'name': 'Area 51', 'lat': 37.2431, 'lon': -115.7930, 'radius': 10},
            {'name': 'Camp David', 'lat': 39.6433, 'lon': -77.4656, 'radius': 5},
            {'name': 'White House', 'lat': 38.8977, 'lon': -77.0365, 'radius': 3},
        ]
        
        # Pattern thresholds
        self.thresholds = {
            'max_normal_speed': 600,        # Max normal commercial speed (kt)
            'min_normal_altitude': 1000,    # Min normal cruise altitude (ft)
            'max_vertical_rate': 6000,      # Max normal climb/descent rate (ft/min)
            'circling_radius': 3,           # Miles for circling detection
            'formation_distance': 2,        # Miles for formation flying
            'emergency_altitude': 500,      # Emergency low altitude (ft)
            'suspicious_loiter_time': 1800, # 30 minutes loitering
        }

    def haversine_miles(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in miles"""
        R = 3959  # Earth radius in miles
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 2 * R * math.asin(math.sqrt(a))

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """Calculate bearing between two points"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360

    def analyze_aircraft(self, aircraft_data):
        """Main analysis function - returns list of anomalies detected"""
        anomalies = []
        hex_code = aircraft_data.get('hex', '')
        if not hex_code:
            return anomalies

        history = self.aircraft_history[hex_code]
        current_time = time.time()
        
        # Update tracking data
        self._update_aircraft_history(aircraft_data, history, current_time)
        
        # Run all anomaly detection algorithms
        anomalies.extend(self._detect_emergency_patterns(aircraft_data, history))
        anomalies.extend(self._detect_unusual_flight_behavior(aircraft_data, history))
        anomalies.extend(self._detect_suspicious_patterns(aircraft_data, history))
        anomalies.extend(self._detect_aviation_safety_issues(aircraft_data, history))
        anomalies.extend(self._detect_weird_interesting_patterns(aircraft_data, history))
        anomalies.extend(self._detect_formation_flying(aircraft_data))
        anomalies.extend(self._detect_restricted_area_violations(aircraft_data))
        
        # Update behavior score
        if anomalies:
            history['anomaly_count'] += len(anomalies)
            history['behavior_score'] = min(100, history['behavior_score'] + len(anomalies) * 5)
        
        return anomalies

    def _update_aircraft_history(self, aircraft, history, current_time):
        """Update aircraft tracking history"""
        history['last_seen'] = current_time
        if not history['first_seen']:
            history['first_seen'] = current_time

        # Position tracking
        if 'lat' in aircraft and 'lon' in aircraft:
            position = {
                'lat': aircraft['lat'],
                'lon': aircraft['lon'],
                'time': current_time,
                'altitude': aircraft.get('alt_baro', 0)
            }
            history['positions'].append(position)

        # Track other parameters
        if aircraft.get('alt_baro'):
            history['altitudes'].append(aircraft['alt_baro'])
        if aircraft.get('gs'):
            history['speeds'].append(aircraft['gs'])
        if aircraft.get('track'):
            history['headings'].append(aircraft['track'])
        if aircraft.get('baro_rate'):
            history['vertical_rates'].append(aircraft['baro_rate'])
        if aircraft.get('flight'):
            history['callsigns'].add(aircraft['flight'].strip())
        if aircraft.get('squawk'):
            history['squawks'].add(aircraft['squawk'])

    def _detect_emergency_patterns(self, aircraft, history):
        """Detect emergency situations"""
        anomalies = []
        
        # Emergency squawk codes
        squawk = aircraft.get('squawk')
        if squawk:
            emergency_codes = {
                '7500': 'HIJACK ALERT',
                '7600': 'RADIO FAILURE', 
                '7700': 'GENERAL EMERGENCY',
                '7777': 'MILITARY INTERCEPT'
            }
            if squawk in emergency_codes:
                anomalies.append({
                    'type': 'EMERGENCY',
                    'severity': 'CRITICAL',
                    'description': f'{emergency_codes[squawk]} - Squawking {squawk}',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        # Rapid altitude loss (possible emergency descent)
        if len(history['altitudes']) >= 5:
            recent_alts = list(history['altitudes'])[-5:]
            alt_change = recent_alts[0] - recent_alts[-1]
            if alt_change > 8000:  # Lost 8000+ feet recently
                anomalies.append({
                    'type': 'EMERGENCY_DESCENT',
                    'severity': 'HIGH',
                    'description': f'Rapid altitude loss: {alt_change:.0f} feet',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        # Emergency altitude (very low)
        altitude = aircraft.get('alt_baro', 0)
        if altitude > 0 and altitude < self.thresholds['emergency_altitude']:
            # Check if near airport
            near_airport = self._is_near_airport(aircraft.get('lat'), aircraft.get('lon'))
            if not near_airport:
                anomalies.append({
                    'type': 'LOW_ALTITUDE',
                    'severity': 'HIGH',
                    'description': f'Extremely low altitude: {altitude} ft (not near airport)',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        return anomalies

    def _detect_unusual_flight_behavior(self, aircraft, history):
        """Detect unusual flight patterns"""
        anomalies = []

        # Extreme speeds
        speed = aircraft.get('gs', 0)
        if speed > self.thresholds['max_normal_speed']:
            anomalies.append({
                'type': 'HIGH_SPEED',
                'severity': 'MEDIUM',
                'description': f'Unusually high speed: {speed} knots',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        # Extreme vertical rates
        v_rate = aircraft.get('baro_rate', 0)
        if abs(v_rate) > self.thresholds['max_vertical_rate']:
            direction = 'climbing' if v_rate > 0 else 'descending'
            anomalies.append({
                'type': 'EXTREME_VERTICAL_RATE',
                'severity': 'MEDIUM',
                'description': f'Extreme {direction} rate: {abs(v_rate)} ft/min',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        # Erratic altitude changes
        if len(history['altitudes']) >= 10:
            alts = list(history['altitudes'])
            alt_variance = np.var(alts) if len(alts) > 1 else 0
            if alt_variance > 1000000:  # High altitude variance
                anomalies.append({
                    'type': 'ERRATIC_ALTITUDE',
                    'severity': 'MEDIUM',
                    'description': f'Erratic altitude changes detected (variance: {alt_variance:.0f})',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        # Multiple callsign changes (possible identity spoofing)
        if len(history['callsigns']) > 3:
            anomalies.append({
                'type': 'MULTIPLE_CALLSIGNS',
                'severity': 'MEDIUM',
                'description': f'Multiple callsigns used: {list(history["callsigns"])}',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        return anomalies

    def _detect_suspicious_patterns(self, aircraft, history):
        """Detect potentially suspicious activities"""
        anomalies = []

        # Prolonged circling/loitering
        if len(history['positions']) >= 20:
            positions = list(history['positions'])
            start_pos = positions[0]
            current_pos = positions[-1]
            
            # Check if aircraft has been in small area for long time
            distance_from_start = self.haversine_miles(
                start_pos['lat'], start_pos['lon'],
                current_pos['lat'], current_pos['lon']
            )
            
            time_duration = current_pos['time'] - start_pos['time']
            
            if distance_from_start < 5 and time_duration > self.thresholds['suspicious_loiter_time']:
                anomalies.append({
                    'type': 'SUSPICIOUS_LOITERING',
                    'severity': 'MEDIUM',
                    'description': f'Loitering in {distance_from_start:.1f} mile area for {time_duration/60:.0f} minutes',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        # Zig-zag patterns (possible surveillance)
        if len(history['headings']) >= 10:
            headings = list(history['headings'])
            heading_changes = 0
            for i in range(1, len(headings)):
                diff = abs(headings[i] - headings[i-1])
                if diff > 180:
                    diff = 360 - diff
                if diff > 45:  # Significant heading change
                    heading_changes += 1
            
            if heading_changes > 6:  # Many course changes
                anomalies.append({
                    'type': 'ZIGZAG_PATTERN',
                    'severity': 'LOW',
                    'description': f'Zig-zag flight pattern detected ({heading_changes} course changes)',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        return anomalies

    def _detect_aviation_safety_issues(self, aircraft, history):
        """Detect aviation safety concerns"""
        anomalies = []

        # Transponder malfunction detection
        messages = aircraft.get('messages', 0)
        seen = aircraft.get('seen', 0)
        if messages > 0 and seen > 30:  # No updates for 30+ seconds
            anomalies.append({
                'type': 'TRANSPONDER_ISSUE',
                'severity': 'MEDIUM',
                'description': f'Possible transponder issue - no updates for {seen} seconds',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        # Unusual squawk code changes
        if len(history['squawks']) > 2:
            anomalies.append({
                'type': 'MULTIPLE_SQUAWKS',
                'severity': 'LOW',
                'description': f'Multiple squawk codes: {list(history["squawks"])}',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        # Check for TCAS alerts (if available in data)
        # This would require additional data from ADS-B
        
        return anomalies

    def _detect_weird_interesting_patterns(self, aircraft, history):
        """Detect weird, unusual, or interesting patterns"""
        anomalies = []

        # Perfect geometric patterns
        if len(history['positions']) >= 8:
            positions = list(history['positions'])[-8:]
            if self._is_geometric_pattern(positions):
                anomalies.append({
                    'type': 'GEOMETRIC_PATTERN',
                    'severity': 'LOW',
                    'description': 'Flying in geometric pattern (circle, square, triangle)',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })

        # Extremely high altitude for aircraft type
        altitude = aircraft.get('alt_baro', 0)
        if altitude > 50000:  # Very high altitude
            anomalies.append({
                'type': 'EXTREME_ALTITUDE',
                'severity': 'LOW',
                'description': f'Extremely high altitude: {altitude} feet',
                'aircraft': aircraft,
                'timestamp': time.time()
            })

        # Night flying in unusual patterns
        current_hour = datetime.now().hour
        if 0 <= current_hour <= 5:  # Night hours
            if len(history['positions']) >= 10:
                # Check for unusual night activity
                positions = list(history['positions'])
                total_distance = 0
                for i in range(1, len(positions)):
                    total_distance += self.haversine_miles(
                        positions[i-1]['lat'], positions[i-1]['lon'],
                        positions[i]['lat'], positions[i]['lon']
                    )
                
                if total_distance > 50:  # Extensive night flying
                    anomalies.append({
                        'type': 'EXTENSIVE_NIGHT_FLYING',
                        'severity': 'LOW',
                        'description': f'Extensive night flying pattern ({total_distance:.1f} miles)',
                        'aircraft': aircraft,
                        'timestamp': time.time()
                    })

        # Backwards flying (could indicate aerobatics or emergency)
        if aircraft.get('gs', 0) > 50:  # Has significant speed
            track = aircraft.get('track')
            if track is not None and len(history['positions']) >= 2:
                recent_positions = list(history['positions'])[-2:]
                calculated_bearing = self.calculate_bearing(
                    recent_positions[0]['lat'], recent_positions[0]['lon'],
                    recent_positions[1]['lat'], recent_positions[1]['lon']
                )
                bearing_diff = abs(track - calculated_bearing)
                if bearing_diff > 180:
                    bearing_diff = 360 - bearing_diff
                
                if bearing_diff > 90:  # Flying sideways/backwards
                    anomalies.append({
                        'type': 'UNUSUAL_ORIENTATION',
                        'severity': 'LOW',
                        'description': f'Aircraft orientation unusual (track: {track}°, actual: {calculated_bearing:.0f}°)',
                        'aircraft': aircraft,
                        'timestamp': time.time()
                    })

        return anomalies

    def _detect_formation_flying(self, aircraft):
        """Detect formation flying"""
        anomalies = []
        
        if not ('lat' in aircraft and 'lon' in aircraft):
            return anomalies

        current_lat, current_lon = aircraft['lat'], aircraft['lon']
        current_alt = aircraft.get('alt_baro', 0)
        current_time = time.time()
        
        # Check against other recent aircraft
        formation_aircraft = []
        for hex_code, history in self.aircraft_history.items():
            if hex_code == aircraft.get('hex'):
                continue
                
            if not history['positions']:
                continue
                
            last_pos = history['positions'][-1]
            time_diff = current_time - last_pos['time']
            
            if time_diff < 60:  # Within last minute
                distance = self.haversine_miles(
                    current_lat, current_lon,
                    last_pos['lat'], last_pos['lon']
                )
                alt_diff = abs(current_alt - last_pos['altitude'])
                
                if distance < self.thresholds['formation_distance'] and alt_diff < 1000:
                    formation_aircraft.append(hex_code)
        
        if len(formation_aircraft) >= 1:  # At least one other aircraft nearby
            anomalies.append({
                'type': 'FORMATION_FLYING',
                'severity': 'LOW',
                'description': f'Formation flying detected with {len(formation_aircraft)} other aircraft',
                'aircraft': aircraft,
                'timestamp': time.time(),
                'related_aircraft': formation_aircraft
            })
        
        return anomalies

    def _detect_restricted_area_violations(self, aircraft):
        """Detect flights through restricted areas"""
        anomalies = []
        
        if not ('lat' in aircraft and 'lon' in aircraft):
            return anomalies

        for area in self.restricted_areas:
            distance = self.haversine_miles(
                aircraft['lat'], aircraft['lon'],
                area['lat'], area['lon']
            )
            
            if distance < area['radius']:
                anomalies.append({
                    'type': 'RESTRICTED_AREA',
                    'severity': 'HIGH',
                    'description': f'Aircraft in restricted area: {area["name"]} ({distance:.1f} miles from center)',
                    'aircraft': aircraft,
                    'timestamp': time.time()
                })
        
        return anomalies

    def _is_near_airport(self, lat, lon, radius_miles=10):
        """Check if position is near a known airport"""
        if lat is None or lon is None:
            return False
            
        for airport in self.airports:
            distance = self.haversine_miles(lat, lon, airport['lat'], airport['lon'])
            if distance < radius_miles:
                return True
        return False

    def _is_geometric_pattern(self, positions):
        """Check if positions form a geometric pattern"""
        if len(positions) < 6:
            return False
        
        # Check for circular pattern
        center_lat = sum(p['lat'] for p in positions) / len(positions)
        center_lon = sum(p['lon'] for p in positions) / len(positions)
        
        distances = [
            self.haversine_miles(p['lat'], p['lon'], center_lat, center_lon)
            for p in positions
        ]
        
        # If all distances are similar, it's likely a circle
        if len(set(round(d, 1) for d in distances)) <= 2:
            return True
        
        return False

    def get_aircraft_risk_score(self, hex_code):
        """Get risk score for an aircraft"""
        if hex_code not in self.aircraft_history:
            return 0
        return self.aircraft_history[hex_code]['behavior_score']

    def get_summary_statistics(self):
        """Get summary of anomaly detection statistics"""
        total_aircraft = len(self.aircraft_history)
        high_risk_aircraft = sum(1 for h in self.aircraft_history.values() if h['behavior_score'] > 20)
        total_anomalies = sum(h['anomaly_count'] for h in self.aircraft_history.values())
        
        return {
            'total_aircraft_tracked': total_aircraft,
            'high_risk_aircraft': high_risk_aircraft,
            'total_anomalies_detected': total_anomalies,
            'aircraft_with_anomalies': sum(1 for h in self.aircraft_history.values() if h['anomaly_count'] > 0)
        }