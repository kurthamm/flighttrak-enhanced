#!/usr/bin/env python3
"""
Weather Integration for FlightTrak
Context-aware anomaly detection considering weather conditions
"""

import json
import time
import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3

@dataclass
class WeatherCondition:
    """Weather condition data"""
    timestamp: float
    temperature_f: float
    humidity: float
    pressure_mb: float
    wind_speed_kt: float
    wind_direction: float
    visibility_mi: float
    precipitation_type: str  # "none", "rain", "snow", "ice"
    precipitation_intensity: str  # "light", "moderate", "heavy"
    cloud_cover: str  # "clear", "few", "scattered", "broken", "overcast"
    ceiling_ft: Optional[int]
    weather_phenomena: List[str]  # fog, mist, thunderstorm, etc.

@dataclass
class FlightContext:
    """Flight context considering weather"""
    normal_operations: bool
    weather_factor: float  # 0.0 = severe weather, 1.0 = perfect conditions
    alerts_suppressed: List[str]
    weather_explanation: str

class WeatherDetector:
    """Weather-aware flight anomaly detection"""
    
    def __init__(self, home_lat=34.1133171, home_lon=-80.9024019):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.db_path = 'weather_data.db'
        self.init_database()
        self.weather_cache = {}
        self.cache_duration = 600  # 10 minutes
        
        # Weather impact rules
        self.weather_rules = self._initialize_weather_rules()
    
    def init_database(self):
        """Initialize weather database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    temperature_f REAL,
                    humidity REAL,
                    pressure_mb REAL,
                    wind_speed_kt REAL,
                    wind_direction REAL,
                    visibility_mi REAL,
                    precipitation_type TEXT,
                    precipitation_intensity TEXT,
                    cloud_cover TEXT,
                    ceiling_ft INTEGER,
                    weather_phenomena TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_timestamp ON weather_data(timestamp)')
            
            conn.commit()
            conn.close()
            logging.info("Weather database initialized")
        except Exception as e:
            logging.error(f"Failed to initialize weather database: {e}")
    
    def _initialize_weather_rules(self) -> Dict:
        """Initialize weather impact rules"""
        return {
            'low_visibility': {
                'visibility_threshold': 3.0,  # miles
                'suppresses': ['low_altitude', 'slow_speed'],
                'explanation': 'Low visibility conditions - aircraft flying lower and slower for safety'
            },
            'strong_winds': {
                'wind_threshold': 25.0,  # knots
                'suppresses': ['unstable_flight', 'altitude_changes'],
                'explanation': 'Strong winds causing flight instability and altitude adjustments'
            },
            'precipitation': {
                'types': ['rain', 'snow', 'ice'],
                'suppresses': ['low_altitude', 'circling', 'slow_speed'],
                'explanation': 'Precipitation affecting flight operations and approach patterns'
            },
            'low_ceiling': {
                'ceiling_threshold': 1000,  # feet
                'suppresses': ['low_altitude', 'approach_patterns'],
                'explanation': 'Low cloud ceiling requiring instrument approaches and lower altitudes'
            },
            'thunderstorms': {
                'phenomena': ['thunderstorm', 'convective'],
                'suppresses': ['altitude_changes', 'course_deviations', 'circling'],
                'explanation': 'Thunderstorm activity causing weather avoidance maneuvers'
            },
            'fog': {
                'phenomena': ['fog', 'mist'],
                'visibility_threshold': 1.0,
                'suppresses': ['low_altitude', 'slow_speed', 'approach_patterns'],
                'explanation': 'Fog conditions requiring reduced visibility operations'
            }
        }
    
    def get_weather_data(self, use_mock=True) -> Optional[WeatherCondition]:
        """Get current weather data (mock implementation for demo)"""
        if use_mock:
            return self._get_mock_weather()
        
        # In production, this would connect to a real weather API
        # such as OpenWeatherMap, Aviation Weather Center, or METAR data
        return self._fetch_real_weather()
    
    def _get_mock_weather(self) -> WeatherCondition:
        """Generate mock weather data for demonstration"""
        import random
        
        # Simulate various weather conditions
        weather_scenarios = [
            # Good weather
            {
                'visibility_mi': 10.0,
                'wind_speed_kt': 8.0,
                'precipitation_type': 'none',
                'cloud_cover': 'few',
                'ceiling_ft': None,
                'weather_phenomena': []
            },
            # Low visibility
            {
                'visibility_mi': 2.0,
                'wind_speed_kt': 12.0,
                'precipitation_type': 'rain',
                'precipitation_intensity': 'moderate',
                'cloud_cover': 'overcast',
                'ceiling_ft': 800,
                'weather_phenomena': ['mist']
            },
            # Strong winds
            {
                'visibility_mi': 8.0,
                'wind_speed_kt': 35.0,
                'precipitation_type': 'none',
                'cloud_cover': 'scattered',
                'ceiling_ft': 2500,
                'weather_phenomena': []
            },
            # Thunderstorms
            {
                'visibility_mi': 4.0,
                'wind_speed_kt': 20.0,
                'precipitation_type': 'rain',
                'precipitation_intensity': 'heavy',
                'cloud_cover': 'overcast',
                'ceiling_ft': 1200,
                'weather_phenomena': ['thunderstorm']
            }
        ]
        
        # Select scenario based on time (for demo consistency)
        scenario_index = int(time.time() / 3600) % len(weather_scenarios)
        scenario = weather_scenarios[scenario_index]
        
        return WeatherCondition(
            timestamp=time.time(),
            temperature_f=72.0 + random.uniform(-10, 15),
            humidity=60.0 + random.uniform(-20, 30),
            pressure_mb=1013.25 + random.uniform(-10, 10),
            wind_speed_kt=scenario['wind_speed_kt'],
            wind_direction=random.uniform(0, 360),
            visibility_mi=scenario['visibility_mi'],
            precipitation_type=scenario['precipitation_type'],
            precipitation_intensity=scenario.get('precipitation_intensity', 'none'),
            cloud_cover=scenario['cloud_cover'],
            ceiling_ft=scenario['ceiling_ft'],
            weather_phenomena=scenario['weather_phenomena']
        )
    
    def _fetch_real_weather(self) -> Optional[WeatherCondition]:
        """Fetch real weather data from external API"""
        # This would implement actual weather API calls
        # Examples: OpenWeatherMap, Aviation Weather Center, etc.
        
        # Mock implementation - replace with real API
        try:
            # Example API call structure (not functional without API key)
            # url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.home_lat}&lon={self.home_lon}&appid=YOUR_API_KEY"
            # response = requests.get(url, timeout=10)
            # data = response.json()
            
            # For now, return mock data
            return self._get_mock_weather()
        except Exception as e:
            logging.error(f"Failed to fetch weather data: {e}")
            return None
    
    def save_weather_data(self, weather: WeatherCondition):
        """Save weather data to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO weather_data 
                (timestamp, temperature_f, humidity, pressure_mb, wind_speed_kt, 
                 wind_direction, visibility_mi, precipitation_type, precipitation_intensity,
                 cloud_cover, ceiling_ft, weather_phenomena)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                weather.timestamp, weather.temperature_f, weather.humidity, 
                weather.pressure_mb, weather.wind_speed_kt, weather.wind_direction,
                weather.visibility_mi, weather.precipitation_type, weather.precipitation_intensity,
                weather.cloud_cover, weather.ceiling_ft, json.dumps(weather.weather_phenomena)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Failed to save weather data: {e}")
    
    def get_recent_weather(self, hours_back: int = 2) -> List[WeatherCondition]:
        """Get recent weather data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (hours_back * 3600)
            cursor.execute('''
                SELECT timestamp, temperature_f, humidity, pressure_mb, wind_speed_kt,
                       wind_direction, visibility_mi, precipitation_type, precipitation_intensity,
                       cloud_cover, ceiling_ft, weather_phenomena
                FROM weather_data
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_time,))
            
            weather_data = []
            for row in cursor.fetchall():
                weather_data.append(WeatherCondition(
                    timestamp=row[0],
                    temperature_f=row[1],
                    humidity=row[2],
                    pressure_mb=row[3],
                    wind_speed_kt=row[4],
                    wind_direction=row[5],
                    visibility_mi=row[6],
                    precipitation_type=row[7],
                    precipitation_intensity=row[8],
                    cloud_cover=row[9],
                    ceiling_ft=row[10],
                    weather_phenomena=json.loads(row[11]) if row[11] else []
                ))
            
            conn.close()
            return weather_data
        except Exception as e:
            logging.error(f"Failed to get recent weather: {e}")
            return []
    
    def analyze_weather_impact(self, weather: WeatherCondition) -> FlightContext:
        """Analyze weather impact on flight operations"""
        suppressed_alerts = []
        weather_explanations = []
        weather_factor = 1.0  # Start with perfect conditions
        
        # Check each weather rule
        for rule_name, rule in self.weather_rules.items():
            rule_triggered = False
            
            if rule_name == 'low_visibility':
                if weather.visibility_mi <= rule['visibility_threshold']:
                    rule_triggered = True
                    weather_factor *= 0.6  # Reduce by 40%
            
            elif rule_name == 'strong_winds':
                if weather.wind_speed_kt >= rule['wind_threshold']:
                    rule_triggered = True
                    weather_factor *= 0.7  # Reduce by 30%
            
            elif rule_name == 'precipitation':
                if weather.precipitation_type in rule['types'] and weather.precipitation_intensity != 'light':
                    rule_triggered = True
                    weather_factor *= 0.5  # Reduce by 50%
            
            elif rule_name == 'low_ceiling':
                if weather.ceiling_ft and weather.ceiling_ft <= rule['ceiling_threshold']:
                    rule_triggered = True
                    weather_factor *= 0.6  # Reduce by 40%
            
            elif rule_name == 'thunderstorms':
                if any(phenom in weather.weather_phenomena for phenom in rule['phenomena']):
                    rule_triggered = True
                    weather_factor *= 0.3  # Reduce by 70%
            
            elif rule_name == 'fog':
                if any(phenom in weather.weather_phenomena for phenom in rule['phenomena']):
                    if weather.visibility_mi <= rule['visibility_threshold']:
                        rule_triggered = True
                        weather_factor *= 0.4  # Reduce by 60%
            
            if rule_triggered:
                suppressed_alerts.extend(rule['suppresses'])
                weather_explanations.append(rule['explanation'])
        
        # Remove duplicates
        suppressed_alerts = list(set(suppressed_alerts))
        
        # Determine if operations are normal
        normal_operations = weather_factor > 0.7
        
        # Create explanation
        if weather_explanations:
            explanation = "; ".join(weather_explanations)
        else:
            explanation = "Good weather conditions - normal flight operations expected"
        
        return FlightContext(
            normal_operations=normal_operations,
            weather_factor=weather_factor,
            alerts_suppressed=suppressed_alerts,
            weather_explanation=explanation
        )
    
    def should_suppress_alert(self, alert_type: str, weather: WeatherCondition = None) -> Tuple[bool, str]:
        """Determine if an alert should be suppressed due to weather"""
        if not weather:
            weather = self.get_weather_data()
        
        if not weather:
            return False, "No weather data available"
        
        context = self.analyze_weather_impact(weather)
        
        if alert_type in context.alerts_suppressed:
            return True, f"Alert suppressed due to weather: {context.weather_explanation}"
        
        return False, "Weather conditions do not justify suppressing this alert"
    
    def get_weather_summary(self) -> Dict:
        """Get current weather summary for dashboard"""
        weather = self.get_weather_data()
        if not weather:
            return {"error": "Weather data unavailable"}
        
        context = self.analyze_weather_impact(weather)
        
        # Determine weather status
        if context.weather_factor > 0.8:
            status = "GOOD"
            status_color = "green"
        elif context.weather_factor > 0.6:
            status = "FAIR"
            status_color = "yellow"
        elif context.weather_factor > 0.4:
            status = "POOR"
            status_color = "orange"
        else:
            status = "SEVERE"
            status_color = "red"
        
        return {
            "status": status,
            "status_color": status_color,
            "weather_factor": context.weather_factor,
            "visibility_mi": weather.visibility_mi,
            "wind_speed_kt": weather.wind_speed_kt,
            "wind_direction": weather.wind_direction,
            "precipitation": weather.precipitation_type,
            "ceiling_ft": weather.ceiling_ft,
            "explanation": context.weather_explanation,
            "suppressed_alerts": context.alerts_suppressed,
            "normal_operations": context.normal_operations
        }
    
    def cleanup_old_weather(self, days_to_keep: int = 7):
        """Remove old weather data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)
            cursor.execute('DELETE FROM weather_data WHERE timestamp < ?', (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logging.info(f"Cleaned up {deleted_count} old weather records")
            return deleted_count
        except Exception as e:
            logging.error(f"Failed to cleanup weather data: {e}")
            return 0

# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    detector = WeatherDetector()
    
    print("Testing weather integration...")
    
    # Get current weather
    weather = detector.get_weather_data()
    if weather:
        print(f"\nCurrent Weather:")
        print(f"  Visibility: {weather.visibility_mi} miles")
        print(f"  Wind: {weather.wind_speed_kt} kt @ {weather.wind_direction}°")
        print(f"  Precipitation: {weather.precipitation_type}")
        print(f"  Cloud Cover: {weather.cloud_cover}")
        print(f"  Ceiling: {weather.ceiling_ft} ft" if weather.ceiling_ft else "  Ceiling: Unlimited")
        print(f"  Phenomena: {weather.weather_phenomena}")
        
        # Save to database
        detector.save_weather_data(weather)
        
        # Analyze impact
        context = detector.analyze_weather_impact(weather)
        print(f"\nWeather Impact:")
        print(f"  Normal Operations: {context.normal_operations}")
        print(f"  Weather Factor: {context.weather_factor:.2f}")
        print(f"  Suppressed Alerts: {context.alerts_suppressed}")
        print(f"  Explanation: {context.weather_explanation}")
        
        # Test alert suppression
        test_alerts = ['low_altitude', 'slow_speed', 'circling', 'altitude_changes']
        print(f"\nAlert Suppression Tests:")
        for alert in test_alerts:
            suppress, reason = detector.should_suppress_alert(alert, weather)
            print(f"  {alert}: {'SUPPRESSED' if suppress else 'ACTIVE'} - {reason}")
        
        # Get weather summary
        summary = detector.get_weather_summary()
        print(f"\nWeather Summary:")
        print(f"  Status: {summary['status']}")
        print(f"  Impact Factor: {summary['weather_factor']:.2f}")
        print(f"  Active Suppressions: {len(summary['suppressed_alerts'])}")