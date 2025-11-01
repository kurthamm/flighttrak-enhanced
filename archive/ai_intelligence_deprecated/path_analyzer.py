#!/usr/bin/env python3
"""
Historical Flight Path Analysis System for FlightTrak
Advanced circling detection and pattern analysis using flight history
"""

import math
import time
import json
import logging
import sqlite3
from typing import Dict, List, Tuple, Optional, NamedTuple
from collections import deque, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

@dataclass
class FlightPoint:
    """Single flight position point"""
    lat: float
    lon: float
    altitude: int
    timestamp: float
    speed: float
    heading: int
    vertical_rate: int = 0

@dataclass
class PathSegment:
    """Flight path segment analysis"""
    start_point: FlightPoint
    end_point: FlightPoint
    distance_miles: float
    duration_seconds: float
    avg_speed: float
    heading_change: float
    altitude_change: int

class PatternType:
    """Types of flight patterns"""
    STRAIGHT_LINE = "straight_line"
    CIRCLING_LEFT = "circling_left"
    CIRCLING_RIGHT = "circling_right"
    FIGURE_EIGHT = "figure_eight"
    SEARCH_PATTERN = "search_pattern"
    HOLDING_PATTERN = "holding_pattern"
    APPROACH_PATTERN = "approach_pattern"
    DEPARTURE_PATTERN = "departure_pattern"
    TRAINING_PATTERN = "training_pattern"
    RANDOM_MANEUVERS = "random_maneuvers"

@dataclass
class FlightPattern:
    """Detected flight pattern"""
    pattern_type: str
    confidence: float  # 0.0 to 1.0
    center_lat: float
    center_lon: float
    radius_miles: float
    duration_minutes: float
    turn_rate: float  # degrees per minute
    description: str
    risk_level: str  # LOW, MEDIUM, HIGH

class HistoricalPathAnalyzer:
    """Advanced flight path analysis using historical data"""
    
    def __init__(self, db_path='flight_paths.db'):
        self.db_path = db_path
        self.init_database()
        self.active_paths = defaultdict(lambda: deque(maxlen=200))  # Store last 200 points per aircraft
        self.pattern_cache = {}  # Cache recent pattern analysis
        
    def init_database(self):
        """Initialize SQLite database for flight path storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    icao_hex TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    altitude INTEGER,
                    speed REAL,
                    heading INTEGER,
                    vertical_rate INTEGER,
                    created_date DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    icao_hex TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    center_lat REAL,
                    center_lon REAL,
                    radius_miles REAL,
                    duration_minutes REAL,
                    risk_level TEXT,
                    description TEXT,
                    detected_at REAL NOT NULL,
                    created_date DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Flight path database initialized")
        except Exception as e:
            logging.error(f"Failed to initialize flight path database: {e}")
    
    def haversine_miles(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles between two points"""
        R_km = 6371.0
        φ1, φ2 = math.radians(lat1), math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)
        a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        dist_km = R_km * c
        return dist_km * 0.621371
    
    def bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360
    
    def add_position(self, icao_hex: str, aircraft_data: Dict):
        """Add new position to flight path"""
        if not aircraft_data.get('lat') or not aircraft_data.get('lon'):
            return
        
        point = FlightPoint(
            lat=aircraft_data['lat'],
            lon=aircraft_data['lon'],
            altitude=aircraft_data.get('alt_baro', aircraft_data.get('alt_geom', 0)),
            timestamp=time.time(),
            speed=aircraft_data.get('gs', 0),
            heading=aircraft_data.get('track', 0),
            vertical_rate=aircraft_data.get('baro_rate', 0)
        )
        
        # Add to active path
        self.active_paths[icao_hex].append(point)
        
        # Store in database (async would be better for production)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO flight_paths 
                (icao_hex, timestamp, lat, lon, altitude, speed, heading, vertical_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (icao_hex, point.timestamp, point.lat, point.lon, 
                  point.altitude, point.speed, point.heading, point.vertical_rate))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error storing flight path for {icao_hex}: {e}")
    
    def analyze_circling_pattern(self, icao_hex: str, min_points: int = 20) -> Optional[FlightPattern]:
        """Analyze flight path for circling patterns"""
        path = self.active_paths.get(icao_hex, deque())
        
        if len(path) < min_points:
            return None
        
        points = list(path)[-min_points:]  # Analyze last N points
        
        # Calculate center point (geometric centroid)
        center_lat = sum(p.lat for p in points) / len(points)
        center_lon = sum(p.lon for p in points) / len(points)
        
        # Calculate distances from center
        distances = [self.haversine_miles(center_lat, center_lon, p.lat, p.lon) for p in points]
        avg_radius = sum(distances) / len(distances)
        radius_variance = sum((d - avg_radius) ** 2 for d in distances) / len(distances)
        radius_consistency = 1.0 - min(radius_variance / (avg_radius ** 2), 1.0)
        
        # Calculate heading changes to detect circular motion
        heading_changes = []
        for i in range(1, len(points)):
            prev_bearing = self.bearing(points[i-1].lat, points[i-1].lon, points[i].lat, points[i].lon)
            curr_bearing = points[i].heading
            
            heading_change = curr_bearing - prev_bearing
            # Normalize to [-180, 180]
            while heading_change > 180:
                heading_change -= 360
            while heading_change < -180:
                heading_change += 360
            heading_changes.append(heading_change)
        
        if not heading_changes:
            return None
        
        # Determine turn direction and consistency
        total_turn = sum(heading_changes)
        avg_turn_rate = abs(total_turn) / (points[-1].timestamp - points[0].timestamp) * 60  # degrees per minute
        
        # Check for consistent turning
        positive_turns = sum(1 for h in heading_changes if h > 5)
        negative_turns = sum(1 for h in heading_changes if h < -5)
        turn_consistency = max(positive_turns, negative_turns) / len(heading_changes)
        
        # Calculate pattern confidence
        confidence = 0.0
        
        # Radius consistency factor (0.3 weight)
        confidence += radius_consistency * 0.3
        
        # Turn consistency factor (0.4 weight)
        confidence += turn_consistency * 0.4
        
        # Minimum turn rate factor (0.2 weight)
        if avg_turn_rate > 3:  # At least 3 degrees per minute
            confidence += min(avg_turn_rate / 30, 1.0) * 0.2
        
        # Path closure factor (0.1 weight)
        start_point = points[0]
        end_point = points[-1]
        closure_distance = self.haversine_miles(start_point.lat, start_point.lon, end_point.lat, end_point.lon)
        if closure_distance < avg_radius:
            confidence += (1.0 - closure_distance / avg_radius) * 0.1
        
        # Determine pattern type and risk level
        if confidence < 0.3:
            return None  # Not a clear pattern
        
        if total_turn > 0:
            pattern_type = PatternType.CIRCLING_RIGHT
        else:
            pattern_type = PatternType.CIRCLING_LEFT
        
        # Risk assessment
        risk_level = "LOW"
        description = f"Aircraft circling {pattern_type.split('_')[1]} with {avg_radius:.1f} mile radius"
        
        if avg_radius < 2 and avg_turn_rate > 10:
            risk_level = "HIGH"
            description += " - Tight circling pattern, possible emergency or unusual activity"
        elif avg_radius < 5 and avg_turn_rate > 6:
            risk_level = "MEDIUM"
            description += " - Moderate circling pattern, possible search or patrol activity"
        
        duration = (points[-1].timestamp - points[0].timestamp) / 60  # minutes
        
        pattern = FlightPattern(
            pattern_type=pattern_type,
            confidence=confidence,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_miles=avg_radius,
            duration_minutes=duration,
            turn_rate=avg_turn_rate,
            description=description,
            risk_level=risk_level
        )
        
        # Cache and store pattern
        self.pattern_cache[icao_hex] = pattern
        self._store_pattern(icao_hex, pattern)
        
        return pattern
    
    def analyze_search_pattern(self, icao_hex: str) -> Optional[FlightPattern]:
        """Detect search or survey patterns (back-and-forth, grid patterns)"""
        path = self.active_paths.get(icao_hex, deque())
        
        if len(path) < 30:
            return None
        
        points = list(path)[-50:]  # Analyze last 50 points
        
        # Analyze heading changes for back-and-forth pattern
        heading_reversals = 0
        consistent_legs = 0
        
        for i in range(2, len(points)):
            h1 = points[i-2].heading
            h2 = points[i-1].heading
            h3 = points[i].heading
            
            # Check for heading reversal (180 degree turn within tolerance)
            heading_diff = abs(h3 - h1)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            
            if 120 < heading_diff < 240:  # Roughly opposite directions
                heading_reversals += 1
            
            # Check for consistent straight legs
            if abs(h2 - h1) < 10 and abs(h3 - h2) < 10:
                consistent_legs += 1
        
        # Calculate pattern confidence
        reversal_rate = heading_reversals / len(points)
        consistency_rate = consistent_legs / len(points)
        
        if reversal_rate > 0.1 and consistency_rate > 0.3:
            confidence = min((reversal_rate * 5 + consistency_rate) * 0.5, 1.0)
            
            # Calculate bounding box
            lats = [p.lat for p in points]
            lons = [p.lon for p in points]
            center_lat = (max(lats) + min(lats)) / 2
            center_lon = (max(lons) + min(lons)) / 2
            
            # Estimate search area
            area_width = self.haversine_miles(min(lats), center_lon, max(lats), center_lon)
            area_height = self.haversine_miles(center_lat, min(lons), center_lat, max(lons))
            avg_dimension = (area_width + area_height) / 2
            
            duration = (points[-1].timestamp - points[0].timestamp) / 60
            
            return FlightPattern(
                pattern_type=PatternType.SEARCH_PATTERN,
                confidence=confidence,
                center_lat=center_lat,
                center_lon=center_lon,
                radius_miles=avg_dimension,
                duration_minutes=duration,
                turn_rate=0,
                description=f"Search/survey pattern over {avg_dimension:.1f} mile area",
                risk_level="LOW"
            )
        
        return None
    
    def _store_pattern(self, icao_hex: str, pattern: FlightPattern):
        """Store detected pattern in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO flight_patterns 
                (icao_hex, pattern_type, confidence, center_lat, center_lon, 
                 radius_miles, duration_minutes, risk_level, description, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (icao_hex, pattern.pattern_type, pattern.confidence, pattern.center_lat,
                  pattern.center_lon, pattern.radius_miles, pattern.duration_minutes,
                  pattern.risk_level, pattern.description, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error storing pattern for {icao_hex}: {e}")
    
    def get_aircraft_patterns(self, icao_hex: str, hours_back: int = 24) -> List[FlightPattern]:
        """Get recent patterns for aircraft"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (hours_back * 3600)
            cursor.execute('''
                SELECT pattern_type, confidence, center_lat, center_lon, radius_miles,
                       duration_minutes, risk_level, description, detected_at
                FROM flight_patterns 
                WHERE icao_hex = ? AND detected_at > ?
                ORDER BY detected_at DESC
            ''', (icao_hex, cutoff_time))
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append(FlightPattern(
                    pattern_type=row[0],
                    confidence=row[1],
                    center_lat=row[2],
                    center_lon=row[3],
                    radius_miles=row[4],
                    duration_minutes=row[5],
                    turn_rate=0,  # Not stored in this query
                    risk_level=row[6],
                    description=row[7]
                ))
            
            conn.close()
            return patterns
        except Exception as e:
            logging.error(f"Error retrieving patterns for {icao_hex}: {e}")
            return []
    
    def analyze_all_patterns(self, icao_hex: str) -> Dict[str, Optional[FlightPattern]]:
        """Run all pattern analysis on aircraft"""
        results = {}
        
        # Check for circling patterns
        circling = self.analyze_circling_pattern(icao_hex)
        if circling and circling.confidence > 0.5:
            results['circling'] = circling
        
        # Check for search patterns
        search = self.analyze_search_pattern(icao_hex)
        if search and search.confidence > 0.4:
            results['search'] = search
        
        return results
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """Clean up old flight path data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
            
            cursor.execute('DELETE FROM flight_paths WHERE created_date < ?', (cutoff_date_str,))
            cursor.execute('DELETE FROM flight_patterns WHERE created_date < ?', (cutoff_date_str,))
            
            deleted_paths = cursor.rowcount
            conn.commit()
            conn.close()
            
            logging.info(f"Cleaned up {deleted_paths} old flight path records")
            return deleted_paths
        except Exception as e:
            logging.error(f"Error cleaning up old data: {e}")
            return 0

# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    analyzer = HistoricalPathAnalyzer()
    
    # Simulate aircraft circling pattern
    print("Testing circling pattern detection:")
    
    test_icao = 'TEST01'
    center_lat, center_lon = 34.1133171, -80.9024019
    radius = 2.0  # miles
    
    # Generate circular path
    for i in range(30):
        angle = (i * 12) * math.pi / 180  # 12 degrees per step
        lat = center_lat + (radius / 69.0) * math.cos(angle)  # rough conversion
        lon = center_lon + (radius / 69.0) * math.sin(angle) / math.cos(math.radians(center_lat))
        
        aircraft_data = {
            'lat': lat,
            'lon': lon,
            'alt_baro': 2000,
            'gs': 100,
            'track': int((angle * 180 / math.pi + 90) % 360),
            'baro_rate': 0
        }
        
        analyzer.add_position(test_icao, aircraft_data)
        time.sleep(0.01)  # Small delay to create realistic timestamps
    
    # Analyze patterns
    patterns = analyzer.analyze_all_patterns(test_icao)
    
    for pattern_type, pattern in patterns.items():
        if pattern:
            print(f"\n{pattern_type.upper()} Pattern Detected:")
            print(f"  Type: {pattern.pattern_type}")
            print(f"  Confidence: {pattern.confidence:.2f}")
            print(f"  Center: {pattern.center_lat:.4f}, {pattern.center_lon:.4f}")
            print(f"  Radius: {pattern.radius_miles:.1f} miles")
            print(f"  Duration: {pattern.duration_minutes:.1f} minutes")
            print(f"  Risk Level: {pattern.risk_level}")
            print(f"  Description: {pattern.description}")