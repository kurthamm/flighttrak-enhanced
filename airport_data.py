#!/usr/bin/env python3
"""
Airport Detection System for FlightTrak
Provides airport proximity checking to reduce false low-altitude alerts
"""

import math
import json
import logging
from typing import Dict, List, Tuple, Optional
import requests
from dataclasses import dataclass

@dataclass
class Airport:
    """Airport information"""
    icao: str
    iata: str
    name: str
    lat: float
    lon: float
    elevation_ft: int
    runway_length_ft: int
    airport_type: str  # 'large_airport', 'medium_airport', 'small_airport', 'heliport'
    country: str
    region: str

class AirportDetector:
    """Airport proximity detection system"""
    
    def __init__(self, home_lat=34.1133171, home_lon=-80.9024019, radius_miles=100):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.radius_miles = radius_miles
        self.airports = {}
        self.load_airport_data()
        
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
    
    def load_airport_data(self):
        """Load airport data for the region"""
        # Major airports in Charlotte, NC area
        charlotte_area_airports = [
            # Major Commercial Airports
            Airport("KCLT", "CLT", "Charlotte Douglas International Airport", 35.2140, -80.9431, 748, 10000, "large_airport", "US", "NC"),
            Airport("KGSO", "GSO", "Piedmont Triad International Airport", 36.0978, -79.9373, 925, 10000, "large_airport", "US", "NC"),
            Airport("KRDU", "RDU", "Raleigh-Durham International Airport", 35.8776, -78.7875, 435, 10000, "large_airport", "US", "NC"),
            Airport("KCAE", "CAE", "Columbia Metropolitan Airport", 33.9388, -81.1195, 236, 8000, "medium_airport", "US", "SC"),
            
            # Medium Airports
            Airport("KFAY", "FAY", "Fayetteville Regional Airport", 34.9915, -78.8803, 189, 7700, "medium_airport", "US", "NC"),
            Airport("KAVL", "AVL", "Asheville Regional Airport", 35.4362, -82.5418, 2165, 8001, "medium_airport", "US", "NC"),
            
            # Smaller Airports and General Aviation
            Airport("KJQF", "JQF", "Concord Regional Airport", 35.3881, -80.7092, 705, 5500, "small_airport", "US", "NC"),
            Airport("KEHO", "EHO", "Shelby-Cleveland County Regional Airport", 35.2594, -81.6053, 826, 5500, "small_airport", "US", "NC"),
            Airport("KRUQ", "RUQ", "Rowan County Airport", 35.6447, -80.5067, 923, 5000, "small_airport", "US", "NC"),
            Airport("KGWQ", "GWQ", "Gastonia Municipal Airport", 35.2053, -81.1497, 777, 4000, "small_airport", "US", "NC"),
            Airport("KFFA", "FFA", "First Flight Airport", 36.0183, -75.6711, 13, 3000, "small_airport", "US", "NC"),
            
            # Heliports and Medical Facilities
            Airport("CLT1", None, "Carolinas Medical Center Heliport", 35.2094, -80.8322, 720, 100, "heliport", "US", "NC"),
            Airport("CLT2", None, "Presbyterian Hospital Heliport", 35.1742, -80.8661, 650, 100, "heliport", "US", "NC"),
            Airport("CLT3", None, "Novant Health Heliport", 35.2400, -80.8400, 700, 100, "heliport", "US", "NC"),
            
            # Military Bases
            Airport("KPOB", "POB", "Pope Army Airfield", 35.1708, -79.0146, 217, 7500, "military", "US", "NC"),
            
            # Additional Regional Airports
            Airport("KHFF", "HFF", "Mackall Army Airfield", 35.0753, -79.5069, 252, 5000, "military", "US", "NC"),
            Airport("KGMU", "GMU", "Greenville-Spartanburg International", 34.8956, -82.2189, 964, 11000, "large_airport", "US", "SC"),
            Airport("KCHS", "CHS", "Charleston International Airport", 32.8986, -80.0405, 46, 9000, "large_airport", "US", "SC"),
            Airport("KMYR", "MYR", "Myrtle Beach International Airport", 33.6797, -78.9283, 25, 9500, "medium_airport", "US", "SC"),
        ]
        
        # Filter airports within radius
        for airport in charlotte_area_airports:
            distance = self.haversine_miles(self.home_lat, self.home_lon, airport.lat, airport.lon)
            if distance <= self.radius_miles:
                self.airports[airport.icao] = airport
                logging.info(f"Loaded airport: {airport.name} ({airport.icao}) - {distance:.1f} mi")
    
    def get_approach_zones(self, airport: Airport) -> Dict[str, float]:
        """Get approach zone parameters for different aircraft types"""
        zones = {
            'large_airport': {
                'radius_miles': 15.0,  # Large approach corridor
                'altitude_threshold': 5000,  # Higher threshold for approach
                'pattern_altitude': 2000,   # Traffic pattern altitude
            },
            'medium_airport': {
                'radius_miles': 10.0,
                'altitude_threshold': 3000,
                'pattern_altitude': 1500,
            },
            'small_airport': {
                'radius_miles': 5.0,
                'altitude_threshold': 2000,
                'pattern_altitude': 1000,
            },
            'heliport': {
                'radius_miles': 2.0,
                'altitude_threshold': 1000,
                'pattern_altitude': 500,
            },
            'military': {
                'radius_miles': 20.0,  # Military has larger restricted areas
                'altitude_threshold': 10000,
                'pattern_altitude': 3000,
            }
        }
        return zones.get(airport.airport_type, zones['small_airport'])
    
    def check_airport_proximity(self, lat: float, lon: float, altitude_ft: int) -> Optional[Dict]:
        """
        Check if aircraft is near an airport and might be on approach/departure
        Returns airport info if near an airport, None otherwise
        """
        for icao, airport in self.airports.items():
            distance_miles = self.haversine_miles(lat, lon, airport.lat, airport.lon)
            zones = self.get_approach_zones(airport)
            
            if distance_miles <= zones['radius_miles']:
                # Aircraft is within airport approach zone
                altitude_above_airport = altitude_ft - airport.elevation_ft
                
                approach_info = {
                    'airport': airport,
                    'distance_miles': distance_miles,
                    'altitude_above_airport': altitude_above_airport,
                    'zones': zones,
                    'likely_approach': altitude_above_airport <= zones['altitude_threshold'],
                    'in_pattern': altitude_above_airport <= zones['pattern_altitude'],
                    'reason': self._get_proximity_reason(distance_miles, altitude_above_airport, zones)
                }
                
                return approach_info
        
        return None
    
    def _get_proximity_reason(self, distance_miles: float, altitude_above_airport: int, zones: Dict) -> str:
        """Determine the most likely reason for low altitude near airport"""
        if altitude_above_airport <= 500:
            if distance_miles <= 2:
                return "Likely on final approach or departure"
            else:
                return "Low altitude near airport - possible approach"
        elif altitude_above_airport <= zones['pattern_altitude']:
            return "In traffic pattern altitude"
        elif altitude_above_airport <= zones['altitude_threshold']:
            return "On approach corridor"
        else:
            return "Near airport but at normal altitude"
    
    def is_low_altitude_normal(self, lat: float, lon: float, altitude_ft: int, aircraft_type: str = None) -> Tuple[bool, str]:
        """
        Determine if low altitude is normal given location and context
        Returns (is_normal, explanation)
        """
        airport_info = self.check_airport_proximity(lat, lon, altitude_ft)
        
        if airport_info:
            airport = airport_info['airport']
            reason = airport_info['reason']
            
            # Different rules for different aircraft types
            if aircraft_type and 'helicopter' in aircraft_type.lower():
                # Helicopters have more flexibility
                if airport_info['distance_miles'] <= 5:
                    return True, f"Helicopter near {airport.name} - {reason}"
            
            if airport_info['likely_approach'] or airport_info['in_pattern']:
                return True, f"Normal operations near {airport.name} - {reason}"
            
            # Even if not on direct approach, proximity to airport makes low altitude more normal
            if airport_info['distance_miles'] <= 3 and altitude_ft >= 500:
                return True, f"Near {airport.name} ({airport_info['distance_miles']:.1f} mi) - likely normal operations"
        
        # Check for common low-altitude corridors
        if self._check_common_routes(lat, lon, altitude_ft):
            return True, "On known low-altitude training or survey route"
        
        return False, "Low altitude away from known airports or routes"
    
    def _check_common_routes(self, lat: float, lon: float, altitude_ft: int) -> bool:
        """Check for known low-altitude routes (training areas, survey routes, etc.)"""
        # Add specific low-altitude training areas or common routes here
        # For now, we'll use some general heuristics
        
        # Check if following highways or major geographic features (simplified)
        # This could be expanded with actual route data
        return False
    
    def get_nearby_airports(self, lat: float, lon: float, max_distance: float = 20) -> List[Dict]:
        """Get list of nearby airports within specified distance"""
        nearby = []
        for icao, airport in self.airports.items():
            distance = self.haversine_miles(lat, lon, airport.lat, airport.lon)
            if distance <= max_distance:
                nearby.append({
                    'airport': airport,
                    'distance_miles': distance,
                    'zones': self.get_approach_zones(airport)
                })
        
        # Sort by distance
        nearby.sort(key=lambda x: x['distance_miles'])
        return nearby
    
    def get_airport_info(self, icao: str) -> Optional[Airport]:
        """Get airport information by ICAO code"""
        return self.airports.get(icao.upper())

# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    detector = AirportDetector()
    
    print(f"Loaded {len(detector.airports)} airports in {detector.radius_miles} mile radius")
    print("\nTesting airport proximity detection:")
    
    # Test cases
    test_cases = [
        # Near CLT airport (should be normal)
        (35.214, -80.943, 1000, "Commercial aircraft on approach to CLT"),
        # Medical helicopter at hospital
        (35.2094, -80.8322, 500, "Medical helicopter at hospital heliport"),
        # Random location, low altitude (should be suspicious)  
        (34.5, -80.5, 800, "Aircraft at low altitude away from airports"),
        # Near small airport
        (35.2053, -81.1497, 1200, "Aircraft near Gastonia Municipal"),
    ]
    
    for lat, lon, alt, description in test_cases:
        is_normal, explanation = detector.is_low_altitude_normal(lat, lon, alt)
        nearby = detector.get_nearby_airports(lat, lon, 10)
        
        print(f"\n{description}:")
        print(f"  Location: {lat:.4f}, {lon:.4f} @ {alt}ft")
        print(f"  Normal: {is_normal}")
        print(f"  Explanation: {explanation}")
        if nearby:
            closest = nearby[0]
            print(f"  Closest airport: {closest['airport'].name} ({closest['distance_miles']:.1f} mi)")