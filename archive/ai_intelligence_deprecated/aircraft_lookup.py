#!/usr/bin/env python3
"""
Aircraft ICAO Hex Code Lookup System
Resolves ICAO hex codes to aircraft registration, type, operator information
Uses multiple free APIs and databases for comprehensive aircraft data
"""

import requests
import json
import time
import logging
from typing import Dict, Optional, Union
import sqlite3
import os
from datetime import datetime, timedelta

class AircraftLookup:
    def __init__(self, cache_duration_hours=24):
        self.cache_duration = cache_duration_hours * 3600  # Convert to seconds
        self.cache_db = 'aircraft_cache.db'
        self.init_cache_db()
        
        # API endpoints
        self.hexdb_base = "https://hexdb.io/api/v1/aircraft"
        self.adsbx_db_url = "https://downloads.adsbexchange.com/downloads/basic-ac-db.json.gz"
        
        # Request headers to be polite
        self.headers = {
            'User-Agent': 'FlightTrak-AircraftLookup/1.0 (Flight Monitoring System)',
            'Accept': 'application/json'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 500ms between requests

    def init_cache_db(self):
        """Initialize SQLite cache database"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS aircraft_cache (
                    icao_hex TEXT PRIMARY KEY,
                    registration TEXT,
                    aircraft_type TEXT,
                    manufacturer TEXT,
                    model TEXT,
                    operator TEXT,
                    owner TEXT,
                    country TEXT,
                    last_updated INTEGER,
                    raw_data TEXT
                )
            ''')
            
            # Index for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_icao ON aircraft_cache(icao_hex)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_updated ON aircraft_cache(last_updated)')
            
            conn.commit()
            conn.close()
            logging.info("Aircraft cache database initialized")
        except Exception as e:
            logging.error(f"Failed to initialize cache database: {e}")

    def rate_limit(self):
        """Ensure we don't overwhelm APIs with requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def get_from_cache(self, icao_hex: str) -> Optional[Dict]:
        """Get aircraft data from cache if recent enough"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM aircraft_cache 
                WHERE icao_hex = ? AND last_updated > ?
            ''', (icao_hex.lower(), time.time() - self.cache_duration))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'icao_hex': row[0],
                    'registration': row[1],
                    'aircraft_type': row[2],
                    'manufacturer': row[3],
                    'model': row[4],
                    'operator': row[5],
                    'owner': row[6],
                    'country': row[7],
                    'last_updated': row[8],
                    'source': 'cache'
                }
            return None
        except Exception as e:
            logging.error(f"Cache lookup error for {icao_hex}: {e}")
            return None

    def save_to_cache(self, icao_hex: str, data: Dict):
        """Save aircraft data to cache"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO aircraft_cache 
                (icao_hex, registration, aircraft_type, manufacturer, model, 
                 operator, owner, country, last_updated, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                icao_hex.lower(),
                data.get('registration'),
                data.get('aircraft_type'),
                data.get('manufacturer'),
                data.get('model'),
                data.get('operator'),
                data.get('owner'),
                data.get('country'),
                int(time.time()),
                json.dumps(data.get('raw_data', {}))
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Cache save error for {icao_hex}: {e}")

    def lookup_hexdb(self, icao_hex: str) -> Optional[Dict]:
        """Lookup aircraft data from hexdb.io API"""
        try:
            self.rate_limit()
            url = f"{self.hexdb_base}/{icao_hex}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract useful information from hexdb response
                aircraft_info = {
                    'icao_hex': icao_hex.lower(),
                    'registration': data.get('Registration'),
                    'aircraft_type': data.get('ICAOTypeCode'),
                    'manufacturer': data.get('Manufacturer'),
                    'model': data.get('Type'),
                    'operator': data.get('RegisteredOwners'),
                    'owner': data.get('RegisteredOwners'),
                    'country': self.extract_country_from_registration(data.get('Registration', '')),
                    'source': 'hexdb.io',
                    'raw_data': data
                }
                
                # Save to cache
                self.save_to_cache(icao_hex, aircraft_info)
                
                logging.info(f"Successfully looked up {icao_hex} from hexdb.io")
                return aircraft_info
                
            elif response.status_code == 404:
                # Aircraft not found in hexdb
                return None
            else:
                logging.warning(f"hexdb.io returned status {response.status_code} for {icao_hex}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error looking up {icao_hex} from hexdb.io: {e}")
            return None
        except Exception as e:
            logging.error(f"Error looking up {icao_hex} from hexdb.io: {e}")
            return None

    def extract_country_from_registration(self, registration: str) -> str:
        """Extract country from aircraft registration prefix"""
        if not registration:
            return "Unknown"
            
        # Common registration prefixes
        country_codes = {
            'N': 'USA',
            'G-': 'UK',
            'D-': 'Germany',
            'F-': 'France',
            'C-': 'Canada',
            'VH-': 'Australia',
            'JA': 'Japan',
            'HL': 'South Korea',
            'B-': 'China',
            'VT-': 'India',
            'EC-': 'Spain',
            'I-': 'Italy',
            'PH-': 'Netherlands',
            'OO-': 'Belgium',
            'OE-': 'Austria',
            'HB-': 'Switzerland',
            'LN-': 'Norway',
            'SE-': 'Sweden',
            'OH-': 'Finland',
            'UR-': 'Ukraine',
            'RA-': 'Russia',
        }
        
        reg_upper = registration.upper()
        for prefix, country in country_codes.items():
            if reg_upper.startswith(prefix):
                return country
        
        # Default to first character for other patterns
        return f"Country-{registration[0] if registration else 'Unknown'}"

    def parse_aircraft_type(self, type_code: str) -> Dict[str, str]:
        """Parse ICAO aircraft type code into category information"""
        if not type_code:
            return {'category': 'Unknown', 'description': 'Unknown aircraft type'}
        
        # Common aircraft type patterns
        type_info = {
            'category': 'Aircraft',
            'description': type_code
        }
        
        # Identify aircraft categories by common patterns
        if any(x in type_code.upper() for x in ['B737', 'B738', 'B739']):
            type_info.update({'category': 'Commercial Airliner', 'description': 'Boeing 737 Series'})
        elif any(x in type_code.upper() for x in ['B777', 'B778', 'B779']):
            type_info.update({'category': 'Commercial Airliner', 'description': 'Boeing 777 Series'})
        elif any(x in type_code.upper() for x in ['A320', 'A319', 'A321']):
            type_info.update({'category': 'Commercial Airliner', 'description': 'Airbus A320 Family'})
        elif any(x in type_code.upper() for x in ['A330', 'A340', 'A350']):
            type_info.update({'category': 'Commercial Airliner', 'description': 'Airbus Wide-body'})
        elif 'C172' in type_code.upper():
            type_info.update({'category': 'General Aviation', 'description': 'Cessna 172'})
        elif any(x in type_code.upper() for x in ['GLEX', 'GLF', 'G650']):
            type_info.update({'category': 'Business Jet', 'description': 'Gulfstream'})
        elif any(x in type_code.upper() for x in ['H60', 'H-60', 'UH60']):
            type_info.update({'category': 'Military Helicopter', 'description': 'Black Hawk'})
        elif 'C130' in type_code.upper():
            type_info.update({'category': 'Military Transport', 'description': 'C-130 Hercules'})
        
        return type_info

    def lookup_aircraft(self, icao_hex: str) -> Dict:
        """
        Main lookup function - tries cache first, then APIs
        Returns comprehensive aircraft information
        """
        if not icao_hex:
            return self.create_unknown_aircraft(icao_hex)
        
        icao_hex = icao_hex.strip().lower()
        
        # First check cache
        cached_data = self.get_from_cache(icao_hex)
        if cached_data:
            return cached_data
        
        # Try hexdb.io API
        aircraft_data = self.lookup_hexdb(icao_hex)
        
        if aircraft_data:
            # Enhance with parsed type information
            type_info = self.parse_aircraft_type(aircraft_data.get('aircraft_type', ''))
            aircraft_data.update(type_info)
            return aircraft_data
        
        # If all lookups fail, return unknown aircraft with ICAO
        unknown_data = self.create_unknown_aircraft(icao_hex)
        self.save_to_cache(icao_hex, unknown_data)  # Cache the "not found" result
        return unknown_data

    def create_unknown_aircraft(self, icao_hex: str) -> Dict:
        """Create a standardized response for unknown aircraft"""
        return {
            'icao_hex': icao_hex.lower() if icao_hex else 'unknown',
            'registration': f'Unknown ({icao_hex.upper()})' if icao_hex else 'Unknown',
            'aircraft_type': 'Unknown',
            'manufacturer': 'Unknown',
            'model': 'Unknown Aircraft',
            'operator': 'Unknown Operator',
            'owner': 'Unknown Owner',
            'country': 'Unknown',
            'category': 'Unknown',
            'description': 'Aircraft information not available',
            'source': 'none',
            'last_updated': int(time.time())
        }

    def batch_lookup(self, icao_hex_list: list) -> Dict[str, Dict]:
        """
        Lookup multiple aircraft efficiently
        Returns dictionary with icao_hex as key and aircraft data as value
        """
        results = {}
        
        for icao_hex in icao_hex_list:
            if icao_hex:
                try:
                    results[icao_hex.lower()] = self.lookup_aircraft(icao_hex)
                except Exception as e:
                    logging.error(f"Error in batch lookup for {icao_hex}: {e}")
                    results[icao_hex.lower()] = self.create_unknown_aircraft(icao_hex)
        
        return results

    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache database"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM aircraft_cache')
            total_entries = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM aircraft_cache WHERE last_updated > ?', 
                          (time.time() - self.cache_duration,))
            valid_entries = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM aircraft_cache WHERE registration != ? AND registration IS NOT NULL', 
                          (f'Unknown',))
            known_aircraft = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'known_aircraft': known_aircraft,
                'cache_hit_rate': f"{(valid_entries/max(total_entries,1)*100):.1f}%"
            }
        except Exception as e:
            logging.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}

    def cleanup_cache(self, max_age_days=7):
        """Remove old entries from cache"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (max_age_days * 24 * 3600)
            cursor.execute('DELETE FROM aircraft_cache WHERE last_updated < ?', (cutoff_time,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logging.info(f"Cleaned up {deleted_count} old cache entries")
            return deleted_count
        except Exception as e:
            logging.error(f"Error cleaning up cache: {e}")
            return 0

# Example usage and testing
if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create lookup instance
    lookup = AircraftLookup()
    
    # Test with some ICAO codes
    test_icaos = ['ab4ea8', 'a9819b', 'ac3adf']
    
    print("Testing Aircraft Lookup System:")
    print("=" * 50)
    
    for icao in test_icaos:
        print(f"\nLooking up {icao.upper()}:")
        result = lookup.lookup_aircraft(icao)
        
        print(f"  Registration: {result.get('registration', 'N/A')}")
        print(f"  Type: {result.get('aircraft_type', 'N/A')}")
        print(f"  Manufacturer: {result.get('manufacturer', 'N/A')}")
        print(f"  Operator: {result.get('operator', 'N/A')}")
        print(f"  Country: {result.get('country', 'N/A')}")
        print(f"  Source: {result.get('source', 'N/A')}")
    
    # Show cache stats
    print(f"\nCache Statistics:")
    stats = lookup.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")