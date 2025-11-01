#!/usr/bin/env python3
"""
Historical Flight Path Analysis for FlightTrak
Better circling detection using flight path history
"""

import math
import time
import json
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
import sqlite3
import numpy as np

@dataclass
class FlightPosition:
    """Single flight position record"""
    timestamp: float
    lat: float
    lon: float
    altitude: int
    heading: float
    speed: float

@dataclass
class FlightPath:
    """Complete flight path with analysis"""
    icao: str
    positions: List[FlightPosition]
    total_distance: float
    max_altitude: int
    min_altitude: int
    avg_speed: float
    duration_minutes: float
    is_circling: bool
    circle_center: Optional[Tuple[float, float]]
    circle_radius: Optional[float]

class FlightPathAnalyzer:
    """Analyzes historical flight paths for pattern detection"""
    
    def __init__(self, db_path='flight_paths.db', max_positions_per_flight=200):
        self.db_path = db_path
        self.max_positions_per_flight = max_positions_per_flight
        self.flight_paths = defaultdict(lambda: deque(maxlen=max_positions_per_flight))
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for persistent storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    icao TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    altitude INTEGER,
                    heading REAL,
                    speed REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    icao TEXT NOT NULL,
                    analysis_timestamp REAL NOT NULL,
                    total_distance REAL,
                    duration_minutes REAL,
                    is_circling BOOLEAN,
                    circle_center_lat REAL,
                    circle_center_lon REAL,
                    circle_radius REAL,
                    pattern_type TEXT,
                    confidence_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indices for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_icao_timestamp ON flight_positions(icao, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON flight_positions(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_icao ON flight_analysis(icao)')
            
            conn.commit()
            conn.close()
            logging.info("Flight path database initialized")
        except Exception as e:
            logging.error(f"Failed to initialize flight path database: {e}")
    
    def haversine_miles(self, lat1, lon1, lat2, lon2):
        """Calculate distance in miles between two points"""
        R_km = 6371.0
        φ1, φ2 = math.radians(lat1), math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)
        a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        dist_km = R_km * c
        return dist_km * 0.621371
    
    def add_position(self, icao: str, lat: float, lon: float, altitude: int = None, 
                    heading: float = None, speed: float = None):
        """Add a new position to flight path"""
        timestamp = time.time()
        position = FlightPosition(
            timestamp=timestamp,
            lat=lat,
            lon=lon,
            altitude=altitude or 0,
            heading=heading or 0,
            speed=speed or 0
        )
        
        # Add to memory
        self.flight_paths[icao].append(position)
        
        # Persist to database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO flight_positions (icao, timestamp, lat, lon, altitude, heading, speed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (icao, timestamp, lat, lon, altitude, heading, speed))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Failed to save position for {icao}: {e}")
    
    def get_flight_path(self, icao: str, hours_back: int = 2) -> List[FlightPosition]:
        """Get flight path from database for specified time period"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (hours_back * 3600)
            cursor.execute('''
                SELECT timestamp, lat, lon, altitude, heading, speed
                FROM flight_positions
                WHERE icao = ? AND timestamp > ?
                ORDER BY timestamp ASC
            ''', (icao, cutoff_time))
            
            positions = []
            for row in cursor.fetchall():
                positions.append(FlightPosition(
                    timestamp=row[0],
                    lat=row[1],
                    lon=row[2],
                    altitude=row[3],
                    heading=row[4],
                    speed=row[5]
                ))
            
            conn.close()
            return positions
        except Exception as e:
            logging.error(f"Failed to get flight path for {icao}: {e}")
            return []
    
    def calculate_total_distance(self, positions: List[FlightPosition]) -> float:
        """Calculate total distance traveled"""
        if len(positions) < 2:
            return 0.0
        
        total = 0.0
        for i in range(1, len(positions)):
            total += self.haversine_miles(
                positions[i-1].lat, positions[i-1].lon,
                positions[i].lat, positions[i].lon
            )
        return total
    
    def detect_circling_pattern(self, positions: List[FlightPosition], 
                               min_positions: int = 10) -> Tuple[bool, Optional[Tuple[float, float]], Optional[float], float]:
        """
        Advanced circling detection using geometric analysis
        Returns (is_circling, center_coords, radius, confidence)
        """
        if len(positions) < min_positions:
            return False, None, None, 0.0
        
        # Extract coordinates
        coords = [(pos.lat, pos.lon) for pos in positions]
        
        # Calculate centroid
        center_lat = sum(lat for lat, lon in coords) / len(coords)
        center_lon = sum(lon for lat, lon in coords) / len(coords)
        
        # Calculate distances from centroid
        distances = [
            self.haversine_miles(center_lat, center_lon, lat, lon)
            for lat, lon in coords
        ]
        
        # Calculate statistics
        avg_distance = np.mean(distances)
        std_distance = np.std(distances)
        
        # Check for circling characteristics
        # 1. Low standard deviation relative to mean (consistent distance from center)
        consistency_ratio = std_distance / max(avg_distance, 0.1)
        
        # 2. Aircraft returns close to starting position
        start_pos = coords[0]
        end_pos = coords[-1]
        closure_distance = self.haversine_miles(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
        
        # 3. Total distance vs. displacement ratio (should be high for circling)
        total_distance = self.calculate_total_distance(positions)
        displacement = self.haversine_miles(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
        efficiency_ratio = displacement / max(total_distance, 0.1)
        
        # 4. Heading changes (should be relatively consistent for circling)
        heading_changes = []
        for i in range(1, len(positions)):
            if positions[i].heading > 0 and positions[i-1].heading > 0:
                heading_diff = abs(positions[i].heading - positions[i-1].heading)
                # Handle 360/0 boundary
                if heading_diff > 180:
                    heading_diff = 360 - heading_diff
                heading_changes.append(heading_diff)
        
        avg_heading_change = np.mean(heading_changes) if heading_changes else 0
        
        # Calculate confidence score
        confidence = 0.0
        
        # Consistency factor (lower std = higher confidence)
        if consistency_ratio < 0.3:
            confidence += 0.3
        elif consistency_ratio < 0.5:
            confidence += 0.2
        
        # Closure factor (returning to start)
        if closure_distance < 1.0:  # Within 1 mile
            confidence += 0.3
        elif closure_distance < 2.0:
            confidence += 0.2
        
        # Efficiency factor (low efficiency = circling)
        if efficiency_ratio < 0.2:
            confidence += 0.3
        elif efficiency_ratio < 0.4:
            confidence += 0.2
        
        # Total distance factor (must have traveled reasonable distance)
        if total_distance > 5.0:  # At least 5 miles
            confidence += 0.1
        
        # Determine if circling
        is_circling = confidence >= 0.6 and avg_distance > 0.5  # At least 0.5 mile radius
        
        return is_circling, (center_lat, center_lon), avg_distance, confidence
    
    def analyze_flight_pattern(self, icao: str, hours_back: int = 2) -> Optional[FlightPath]:
        """Comprehensive flight pattern analysis"""
        positions = self.get_flight_path(icao, hours_back)
        
        if len(positions) < 5:
            return None
        
        # Basic statistics
        total_distance = self.calculate_total_distance(positions)
        duration = (positions[-1].timestamp - positions[0].timestamp) / 60  # minutes
        
        altitudes = [pos.altitude for pos in positions if pos.altitude > 0]
        speeds = [pos.speed for pos in positions if pos.speed > 0]
        
        max_altitude = max(altitudes) if altitudes else 0
        min_altitude = min(altitudes) if altitudes else 0
        avg_speed = np.mean(speeds) if speeds else 0
        
        # Circling detection
        is_circling, circle_center, circle_radius, confidence = self.detect_circling_pattern(positions)
        
        # Create flight path object
        flight_path = FlightPath(
            icao=icao,
            positions=positions,
            total_distance=total_distance,
            max_altitude=max_altitude,
            min_altitude=min_altitude,
            avg_speed=avg_speed,
            duration_minutes=duration,
            is_circling=is_circling,
            circle_center=circle_center,
            circle_radius=circle_radius
        )
        
        # Save analysis to database
        self.save_analysis(icao, flight_path, confidence)
        
        return flight_path
    
    def save_analysis(self, icao: str, flight_path: FlightPath, confidence: float):
        """Save flight analysis to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            pattern_type = "circling" if flight_path.is_circling else "linear"
            center_lat = flight_path.circle_center[0] if flight_path.circle_center else None
            center_lon = flight_path.circle_center[1] if flight_path.circle_center else None
            
            cursor.execute('''
                INSERT INTO flight_analysis 
                (icao, analysis_timestamp, total_distance, duration_minutes, is_circling,
                 circle_center_lat, circle_center_lon, circle_radius, pattern_type, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                icao, time.time(), flight_path.total_distance, flight_path.duration_minutes,
                flight_path.is_circling, center_lat, center_lon, flight_path.circle_radius,
                pattern_type, confidence
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Failed to save analysis for {icao}: {e}")
    
    def get_circling_aircraft(self, confidence_threshold: float = 0.6) -> List[Dict]:
        """Get aircraft currently detected as circling"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent circling detections (last hour)
            cutoff_time = time.time() - 3600
            cursor.execute('''
                SELECT icao, circle_center_lat, circle_center_lon, circle_radius, 
                       confidence_score, analysis_timestamp
                FROM flight_analysis
                WHERE is_circling = 1 
                  AND confidence_score >= ?
                  AND analysis_timestamp > ?
                ORDER BY analysis_timestamp DESC
            ''', (confidence_threshold, cutoff_time))
            
            circling_aircraft = []
            for row in cursor.fetchall():
                circling_aircraft.append({
                    'icao': row[0],
                    'center_lat': row[1],
                    'center_lon': row[2],
                    'radius': row[3],
                    'confidence': row[4],
                    'detected_at': row[5]
                })
            
            conn.close()
            return circling_aircraft
        except Exception as e:
            logging.error(f"Failed to get circling aircraft: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """Remove old flight data to manage database size"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            
            cursor.execute('DELETE FROM flight_positions WHERE timestamp < ?', (cutoff_time,))
            cursor.execute('DELETE FROM flight_analysis WHERE analysis_timestamp < ?', (cutoff_time,))
            
            positions_deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            logging.info(f"Cleaned up {positions_deleted} old flight positions")
            return positions_deleted
        except Exception as e:
            logging.error(f"Failed to cleanup old data: {e}")
            return 0

# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    analyzer = FlightPathAnalyzer()
    
    # Simulate some test flight paths
    print("Testing flight path analysis...")
    
    # Test 1: Circling pattern
    icao_test1 = "TEST01"
    center_lat, center_lon = 35.0, -80.0
    radius = 2.0  # 2 mile radius
    
    # Generate circular flight path
    for i in range(20):
        angle = (i / 20) * 2 * math.pi
        lat = center_lat + (radius / 69.0) * math.cos(angle)  # Rough lat conversion
        lon = center_lon + (radius / 69.0) * math.sin(angle) / math.cos(math.radians(center_lat))
        
        analyzer.add_position(icao_test1, lat, lon, 2000, (angle * 180 / math.pi) % 360, 120)
        time.sleep(0.1)  # Small delay between positions
    
    # Analyze the pattern
    analysis = analyzer.analyze_flight_pattern(icao_test1)
    if analysis:
        print(f"\nTest 1 - Circling Pattern:")
        print(f"  ICAO: {analysis.icao}")
        print(f"  Is Circling: {analysis.is_circling}")
        print(f"  Circle Center: {analysis.circle_center}")
        print(f"  Circle Radius: {analysis.circle_radius:.2f} miles")
        print(f"  Total Distance: {analysis.total_distance:.2f} miles")
        print(f"  Duration: {analysis.duration_minutes:.1f} minutes")
    
    # Test 2: Linear flight path
    icao_test2 = "TEST02"
    start_lat, start_lon = 35.0, -80.0
    
    # Generate linear flight path
    for i in range(15):
        lat = start_lat + (i * 0.01)  # Moving north
        lon = start_lon + (i * 0.005)  # Moving slightly east
        
        analyzer.add_position(icao_test2, lat, lon, 5000 + (i * 100), 45, 250)
        time.sleep(0.1)
    
    # Analyze the pattern
    analysis2 = analyzer.analyze_flight_pattern(icao_test2)
    if analysis2:
        print(f"\nTest 2 - Linear Pattern:")
        print(f"  ICAO: {analysis2.icao}")
        print(f"  Is Circling: {analysis2.is_circling}")
        print(f"  Total Distance: {analysis2.total_distance:.2f} miles")
        print(f"  Duration: {analysis2.duration_minutes:.1f} minutes")
    
    # Check for circling aircraft
    circling = analyzer.get_circling_aircraft()
    print(f"\nCurrently circling aircraft: {len(circling)}")
    for aircraft in circling:
        print(f"  {aircraft['icao']}: confidence {aircraft['confidence']:.2f}")