#!/usr/bin/env python3
"""
Shared utilities for FlightTrak
Common functions used across multiple modules
"""

import math
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth
    
    Args:
        lat1, lon1: Latitude and longitude of first point
        lat2, lon2: Latitude and longitude of second point
        
    Returns:
        Distance in miles
    """
    R = 3959  # Earth radius in miles
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def load_json_config(file_path: str) -> Dict:
    """
    Load JSON configuration file with error handling
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing configuration
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in configuration file {file_path}: {e}")
        raise


def save_json_config(file_path: str, config: Dict) -> bool:
    """
    Save configuration to JSON file
    
    Args:
        file_path: Path to save file
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving configuration to {file_path}: {e}")
        return False


def format_aircraft_info(aircraft: Dict) -> str:
    """
    Format aircraft information for logging
    
    Args:
        aircraft: Aircraft data dictionary
        
    Returns:
        Formatted string
    """
    hex_code = aircraft.get('hex', 'N/A').upper()
    flight = aircraft.get('flight', 'N/A').strip()
    altitude = aircraft.get('alt_baro', 'N/A')
    speed = aircraft.get('gs', 'N/A')
    squawk = aircraft.get('squawk', 'N/A')
    
    return f"ICAO:{hex_code} Flight:{flight} Alt:{altitude}ft Speed:{speed}kt Squawk:{squawk}"


def get_aircraft_distance(aircraft: Dict, home_lat: float, home_lon: float) -> Optional[float]:
    """
    Calculate distance from aircraft to home location
    
    Args:
        aircraft: Aircraft data dictionary
        home_lat: Home latitude
        home_lon: Home longitude
        
    Returns:
        Distance in miles, or None if position data unavailable
    """
    lat = aircraft.get('lat')
    lon = aircraft.get('lon')
    
    if lat is None or lon is None:
        return None
    
    return haversine_distance(home_lat, home_lon, lat, lon)


def is_emergency_squawk(squawk: str) -> bool:
    """
    Check if squawk code indicates emergency
    
    Args:
        squawk: Squawk code as string
        
    Returns:
        True if emergency squawk code
    """
    emergency_codes = {'7500', '7600', '7700'}
    return str(squawk) in emergency_codes


def get_squawk_description(squawk: str) -> str:
    """
    Get description for squawk code
    
    Args:
        squawk: Squawk code as string
        
    Returns:
        Description of squawk code
    """
    squawk_descriptions = {
        '7500': 'Hijacking',
        '7600': 'Communication Failure',
        '7700': 'General Emergency',
        '1200': 'VFR',
        '1000': 'Mode C Veil',
        '0000': 'No Transponder'
    }
    
    return squawk_descriptions.get(str(squawk), 'Unknown')


def rotate_log_file(file_path: str, max_size_mb: int = 10) -> bool:
    """
    Rotate log file if it exceeds maximum size
    
    Args:
        file_path: Path to log file
        max_size_mb: Maximum size in MB
        
    Returns:
        True if rotation performed, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            # Create backup with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{file_path}.{timestamp}"
            
            os.rename(file_path, backup_path)
            
            # Create new empty file
            with open(file_path, 'w') as f:
                f.write('')
            
            logging.info(f"Log file rotated: {file_path} -> {backup_path}")
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Error rotating log file {file_path}: {e}")
        return False


def cleanup_old_files(directory: str, pattern: str, max_age_days: int = 7) -> int:
    """
    Clean up old files matching pattern
    
    Args:
        directory: Directory to search
        pattern: File pattern to match
        max_age_days: Maximum age in days
        
    Returns:
        Number of files deleted
    """
    try:
        import glob
        
        files_deleted = 0
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        pattern_path = os.path.join(directory, pattern)
        
        for file_path in glob.glob(pattern_path):
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                files_deleted += 1
                logging.info(f"Cleaned up old file: {file_path}")
        
        return files_deleted
        
    except Exception as e:
        logging.error(f"Error cleaning up files in {directory}: {e}")
        return 0


def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing between two points
    
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Ending point coordinates
        
    Returns:
        Bearing in degrees (0-360)
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


def get_cardinal_direction(bearing: float) -> str:
    """
    Convert bearing to cardinal direction
    
    Args:
        bearing: Bearing in degrees
        
    Returns:
        Cardinal direction (N, NE, E, SE, S, SW, W, NW)
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]


def format_time_delta(seconds: float) -> str:
    """
    Format time delta in human-readable format
    
    Args:
        seconds: Time difference in seconds
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude coordinates
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if valid coordinates
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def get_flight_level(altitude: int) -> Optional[str]:
    """
    Convert altitude to flight level
    
    Args:
        altitude: Altitude in feet
        
    Returns:
        Flight level string or None if below FL transition
    """
    if altitude >= 18000:
        fl = altitude // 100
        return f"FL{fl:03d}"
    return None


def parse_aircraft_data(raw_data: str) -> Optional[Dict]:
    """
    Parse raw aircraft data from dump1090
    
    Args:
        raw_data: Raw data string
        
    Returns:
        Parsed aircraft dictionary or None if invalid
    """
    try:
        # Expected format: MSG,3,111,11111,3C4DD9,111111,2010/11/25,18:58:41.153,2010/11/25,18:58:41.153,,33000,,,42.81956,-81.41675,,,0,0,0,0
        parts = raw_data.strip().split(',')
        
        if len(parts) < 22 or parts[0] != 'MSG':
            return None
        
        # Extract relevant fields
        aircraft = {
            'hex': parts[4],
            'flight': parts[10].strip() if parts[10] else None,
            'alt_baro': int(parts[11]) if parts[11] else None,
            'gs': int(parts[12]) if parts[12] else None,
            'track': float(parts[13]) if parts[13] else None,
            'lat': float(parts[14]) if parts[14] else None,
            'lon': float(parts[15]) if parts[15] else None,
            'vert_rate': int(parts[16]) if parts[16] else None,
            'squawk': parts[17] if parts[17] else None,
        }
        
        # Remove None values
        return {k: v for k, v in aircraft.items() if v is not None}
        
    except (ValueError, IndexError) as e:
        logging.debug(f"Error parsing aircraft data: {e}")
        return None


def get_system_stats() -> Dict:
    """
    Get system statistics
    
    Returns:
        Dictionary with system stats
    """
    try:
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'uptime': time.time() - psutil.boot_time(),
            'timestamp': datetime.now().isoformat()
        }
    except ImportError:
        return {
            'cpu_percent': None,
            'memory_percent': None,
            'disk_percent': None,
            'uptime': None,
            'timestamp': datetime.now().isoformat()
        }


def create_backup(file_path: str) -> Optional[str]:
    """
    Create backup of file with timestamp
    
    Args:
        file_path: Path to file to backup
        
    Returns:
        Path to backup file or None if failed
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup_{timestamp}"
        
        import shutil
        shutil.copy2(file_path, backup_path)
        
        logging.info(f"Created backup: {backup_path}")
        return backup_path
        
    except Exception as e:
        logging.error(f"Error creating backup of {file_path}: {e}")
        return None