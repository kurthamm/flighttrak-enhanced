#!/usr/bin/env python3
"""
Flight Pattern Analyzer - Identifies interesting patterns in aircraft movements
"""

import json
import time
import requests
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import math

class FlightAnalyzer:
    def __init__(self, planes_url="https://planes.hamm.me/data/aircraft.json"):
        self.planes_url = planes_url
        self.flight_patterns = defaultdict(list)
        self.aircraft_stats = defaultdict(lambda: {
            'total_messages': 0,
            'positions': [],
            'altitudes': [],
            'speeds': [],
            'first_seen': None,
            'last_seen': None,
            'callsigns': set(),
            'squawks': set()
        })
        self.interesting_events = []
        
    def fetch_data(self):
        """Fetch current aircraft data"""
        try:
            response = requests.get(self.planes_url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None
    
    def analyze_aircraft(self, aircraft):
        """Analyze individual aircraft for interesting patterns"""
        hex_code = aircraft.get('hex', '')
        if not hex_code:
            return
            
        stats = self.aircraft_stats[hex_code]
        current_time = time.time()
        
        # Update basic stats
        stats['total_messages'] += aircraft.get('messages', 0)
        stats['last_seen'] = current_time
        if not stats['first_seen']:
            stats['first_seen'] = current_time
            
        # Track callsigns
        if aircraft.get('flight'):
            stats['callsigns'].add(aircraft['flight'].strip())
            
        # Track squawks
        if aircraft.get('squawk'):
            squawk = aircraft['squawk']
            stats['squawks'].add(squawk)
            
            # Check for emergency squawks
            if squawk in ['7500', '7600', '7700']:
                self.log_event('EMERGENCY', f"Aircraft {hex_code} squawking {squawk}!", aircraft)
                
        # Track positions
        if 'lat' in aircraft and 'lon' in aircraft:
            position = {
                'lat': aircraft['lat'],
                'lon': aircraft['lon'],
                'time': current_time
            }
            stats['positions'].append(position)
            
            # Check for unusual maneuvers
            if len(stats['positions']) > 2:
                self.check_unusual_maneuvers(hex_code, stats['positions'])
                
        # Track altitudes
        if aircraft.get('alt_baro'):
            alt = aircraft['alt_baro']
            stats['altitudes'].append(alt)
            
            # Check for rapid altitude changes
            if len(stats['altitudes']) > 2:
                recent_alts = stats['altitudes'][-5:]
                if len(recent_alts) > 2:
                    alt_change = max(recent_alts) - min(recent_alts)
                    if alt_change > 3000:  # More than 3000ft change
                        self.log_event('ALTITUDE', 
                            f"Rapid altitude change: {alt_change}ft", aircraft)
                        
        # Track speeds
        if aircraft.get('gs'):
            speed = aircraft['gs']
            stats['speeds'].append(speed)
            
            # Check for unusual speeds
            if speed > 600:  # Very high speed
                self.log_event('SPEED', f"High speed detected: {speed}kt", aircraft)
            elif speed < 60 and aircraft.get('alt_baro', 0) > 5000:
                self.log_event('SPEED', f"Low speed at altitude: {speed}kt @ {aircraft.get('alt_baro')}ft", aircraft)
    
    def check_unusual_maneuvers(self, hex_code, positions):
        """Check for unusual flight patterns"""
        if len(positions) < 3:
            return
            
        # Check for circling (returning to similar position)
        recent = positions[-10:]
        if len(recent) >= 10:
            first = recent[0]
            last = recent[-1]
            
            # Calculate distance between first and last position
            dist = self.haversine_distance(
                first['lat'], first['lon'],
                last['lat'], last['lon']
            )
            
            # If aircraft returned close to start position after moving
            if dist < 2:  # Within 2 miles
                total_dist = 0
                for i in range(1, len(recent)):
                    total_dist += self.haversine_distance(
                        recent[i-1]['lat'], recent[i-1]['lon'],
                        recent[i]['lat'], recent[i]['lon']
                    )
                
                if total_dist > 10:  # Traveled more than 10 miles total
                    self.log_event('PATTERN', f"Circling pattern detected", 
                        {'hex': hex_code})
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance in miles"""
        R_km = 6371.0
        φ1, φ2 = math.radians(lat1), math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)
        a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R_km * c * 0.621371
    
    def log_event(self, event_type, description, aircraft_data):
        """Log interesting events"""
        event = {
            'time': datetime.now().isoformat(),
            'type': event_type,
            'description': description,
            'aircraft': aircraft_data
        }
        self.interesting_events.append(event)
        print(f"[{event_type}] {description}")
    
    def get_statistics(self):
        """Generate statistics from collected data"""
        stats = {
            'total_aircraft': len(self.aircraft_stats),
            'active_aircraft': 0,
            'most_seen': None,
            'longest_tracked': None,
            'callsign_changes': [],
            'interesting_events': self.interesting_events[-20:]  # Last 20 events
        }
        
        current_time = time.time()
        max_messages = 0
        longest_duration = 0
        
        for hex_code, aircraft_stats in self.aircraft_stats.items():
            # Check if recently active (within last 5 minutes)
            if current_time - aircraft_stats['last_seen'] < 300:
                stats['active_aircraft'] += 1
                
            # Find most seen aircraft
            if aircraft_stats['total_messages'] > max_messages:
                max_messages = aircraft_stats['total_messages']
                stats['most_seen'] = {
                    'hex': hex_code,
                    'messages': max_messages,
                    'callsigns': list(aircraft_stats['callsigns'])
                }
                
            # Find longest tracked
            if aircraft_stats['first_seen']:
                duration = aircraft_stats['last_seen'] - aircraft_stats['first_seen']
                if duration > longest_duration:
                    longest_duration = duration
                    stats['longest_tracked'] = {
                        'hex': hex_code,
                        'duration_minutes': round(duration / 60, 1),
                        'callsigns': list(aircraft_stats['callsigns'])
                    }
                    
            # Check for callsign changes
            if len(aircraft_stats['callsigns']) > 1:
                stats['callsign_changes'].append({
                    'hex': hex_code,
                    'callsigns': list(aircraft_stats['callsigns'])
                })
        
        return stats
    
    def run_continuous_analysis(self, interval=5):
        """Run continuous analysis"""
        print(f"Starting flight analysis (checking every {interval} seconds)...")
        
        while True:
            data = self.fetch_data()
            if data and 'aircraft' in data:
                for aircraft in data['aircraft']:
                    self.analyze_aircraft(aircraft)
                    
                # Print statistics every minute
                if int(time.time()) % 60 < interval:
                    stats = self.get_statistics()
                    print(f"\n--- Statistics at {datetime.now().strftime('%H:%M:%S')} ---")
                    print(f"Total aircraft seen: {stats['total_aircraft']}")
                    print(f"Currently active: {stats['active_aircraft']}")
                    if stats['most_seen']:
                        print(f"Most seen: {stats['most_seen']['hex']} ({stats['most_seen']['messages']} messages)")
                    if stats['longest_tracked']:
                        print(f"Longest tracked: {stats['longest_tracked']['hex']} ({stats['longest_tracked']['duration_minutes']} minutes)")
                    if stats['callsign_changes']:
                        print(f"Aircraft with multiple callsigns: {len(stats['callsign_changes'])}")
                    print("---\n")
                    
            time.sleep(interval)

if __name__ == '__main__':
    analyzer = FlightAnalyzer()
    analyzer.run_continuous_analysis()