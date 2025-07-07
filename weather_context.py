#!/usr/bin/env python3
"""
Weather Context Integration for FlightTrak
Provides weather-aware anomaly detection and context for flight behavior
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import math

@dataclass
class WeatherCondition:
    """Current weather conditions"""
    location: str
    lat: float
    lon: float
    temperature_f: float
    humidity: float
    pressure_mb: float
    wind_speed_mph: float
    wind_direction: int
    visibility_miles: float
    cloud_ceiling_ft: Optional[int]
    weather_description: str
    precipitation: bool
    storm_activity: bool
    turbulence_risk: str  # LOW, MEDIUM, HIGH
    updated_at: float

@dataclass 
class WeatherImpact:
    """Weather impact on flight operations"""
    condition: WeatherCondition
    flight_impact_level: str  # NONE, LOW, MEDIUM, HIGH, SEVERE
    reasons: List[str]
    recommended_actions: List[str]
    altitude_effects: Dict[str, str]
    visibility_effects: str

class WeatherContextProvider:
    """Provides weather context for flight anomaly analysis"""
    
    def __init__(self, api_key: Optional[str] = None, home_lat: float = 34.1133171, home_lon: float = -80.9024019):
        self.api_key = api_key
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.weather_cache = {}
        self.cache_duration = 600  # 10 minutes
        
        # Weather station locations around Charlotte, NC
        self.weather_stations = {
            'KCLT': {'lat': 35.214, 'lon': -80.943, 'name': 'Charlotte Douglas Intl'},
            'KGSO': {'lat': 36.098, 'lon': -79.937, 'name': 'Greensboro'},
            'KRDU': {'lat': 35.878, 'lon': -78.788, 'name': 'Raleigh-Durham'},
            'KAVL': {'lat': 35.436, 'lon': -82.542, 'name': 'Asheville'},
            'KCAE': {'lat': 33.939, 'lon': -81.120, 'name': 'Columbia SC'}
        }
        
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
    
    def get_weather_data_openweather(self, lat: float, lon: float) -> Optional[WeatherCondition]:
        """Get weather data from OpenWeatherMap API (if API key available)"""
        if not self.api_key:
            return None
            
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract weather information
            main = data.get('main', {})
            wind = data.get('wind', {})
            weather = data.get('weather', [{}])[0]
            visibility = data.get('visibility', 10000) * 0.000621371  # meters to miles
            
            # Determine conditions
            weather_desc = weather.get('description', 'unknown')
            has_precipitation = any(x in weather_desc.lower() for x in ['rain', 'snow', 'drizzle', 'shower'])
            has_storms = any(x in weather_desc.lower() for x in ['thunder', 'storm'])
            
            # Assess turbulence risk
            wind_speed = wind.get('speed', 0)
            turbulence = 'LOW'
            if wind_speed > 25:
                turbulence = 'HIGH'
            elif wind_speed > 15:
                turbulence = 'MEDIUM'
            
            return WeatherCondition(
                location=f"{lat:.3f},{lon:.3f}",
                lat=lat,
                lon=lon,
                temperature_f=main.get('temp', 70),
                humidity=main.get('humidity', 50),
                pressure_mb=main.get('pressure', 1013),
                wind_speed_mph=wind_speed,
                wind_direction=wind.get('deg', 0),
                visibility_miles=visibility,
                cloud_ceiling_ft=None,  # Not directly available
                weather_description=weather_desc,
                precipitation=has_precipitation,
                storm_activity=has_storms,
                turbulence_risk=turbulence,
                updated_at=time.time()
            )
            
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}")
            return None
    
    def get_weather_data_nws(self, lat: float, lon: float) -> Optional[WeatherCondition]:
        """Get weather data from National Weather Service API (free, no key required)"""
        try:
            # Get grid point for location
            grid_url = f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"
            headers = {'User-Agent': 'FlightTrak Weather Monitor'}
            
            response = requests.get(grid_url, headers=headers, timeout=10)
            response.raise_for_status()
            grid_data = response.json()
            
            # Get current observations URL
            stations_url = grid_data['properties']['observationStations']
            response = requests.get(stations_url, headers=headers, timeout=10)
            response.raise_for_status()
            stations_data = response.json()
            
            if not stations_data['features']:
                return None
            
            # Get observations from first available station
            station_id = stations_data['features'][0]['properties']['stationIdentifier']
            obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
            
            response = requests.get(obs_url, headers=headers, timeout=10)
            response.raise_for_status()
            obs_data = response.json()
            
            props = obs_data['properties']
            
            # Convert units
            temp_c = props.get('temperature', {}).get('value')
            temp_f = (temp_c * 9/5) + 32 if temp_c else 70
            
            wind_speed_ms = props.get('windSpeed', {}).get('value')
            wind_speed_mph = wind_speed_ms * 2.237 if wind_speed_ms else 0
            
            visibility_m = props.get('visibility', {}).get('value')
            visibility_miles = visibility_m * 0.000621371 if visibility_m else 10
            
            pressure_pa = props.get('barometricPressure', {}).get('value')
            pressure_mb = pressure_pa / 100 if pressure_pa else 1013
            
            # Parse weather description
            weather_desc = props.get('textDescription', 'clear')
            has_precipitation = any(x in weather_desc.lower() for x in ['rain', 'snow', 'drizzle', 'shower'])
            has_storms = any(x in weather_desc.lower() for x in ['thunder', 'storm'])
            
            # Assess turbulence
            turbulence = 'LOW'
            if wind_speed_mph > 25:
                turbulence = 'HIGH'
            elif wind_speed_mph > 15:
                turbulence = 'MEDIUM'
            
            return WeatherCondition(
                location=station_id,
                lat=lat,
                lon=lon,
                temperature_f=temp_f,
                humidity=props.get('relativeHumidity', {}).get('value', 50),
                pressure_mb=pressure_mb,
                wind_speed_mph=wind_speed_mph,
                wind_direction=props.get('windDirection', {}).get('value', 0),
                visibility_miles=visibility_miles,
                cloud_ceiling_ft=None,  # Would need to parse cloud layers
                weather_description=weather_desc,
                precipitation=has_precipitation,
                storm_activity=has_storms,
                turbulence_risk=turbulence,
                updated_at=time.time()
            )
            
        except Exception as e:
            logging.error(f"Error fetching NWS weather data: {e}")
            return None
    
    def get_synthetic_weather(self, lat: float, lon: float) -> WeatherCondition:
        """Generate synthetic weather data based on location and time (fallback)"""
        # Simple model based on geography and season
        now = datetime.now()
        
        # Base conditions for Charlotte, NC area
        base_temp = 70
        if now.month in [12, 1, 2]:  # Winter
            base_temp = 45
        elif now.month in [6, 7, 8]:  # Summer
            base_temp = 85
        elif now.month in [3, 4, 5]:  # Spring
            base_temp = 65
        else:  # Fall
            base_temp = 60
        
        # Add daily variation
        hour_factor = math.sin((now.hour - 6) * math.pi / 12)  # Peak at 2pm
        temp = base_temp + (hour_factor * 15)
        
        # Simple wind model
        wind_speed = 5 + (hash(f"{lat}{lon}{now.day}") % 20)
        wind_dir = hash(f"{lat}{lon}{now.hour}") % 360
        
        # Precipitation chance based on season
        precip_chance = 0.2 if now.month in [6, 7, 8] else 0.1
        has_precip = (hash(f"{lat}{lon}{now.date()}") % 100) < (precip_chance * 100)
        
        turbulence = 'LOW'
        if wind_speed > 25:
            turbulence = 'HIGH'
        elif wind_speed > 15:
            turbulence = 'MEDIUM'
        
        weather_desc = 'clear' if not has_precip else 'light rain'
        
        return WeatherCondition(
            location=f"Synthetic-{lat:.2f},{lon:.2f}",
            lat=lat,
            lon=lon,
            temperature_f=temp,
            humidity=60,
            pressure_mb=1013,
            wind_speed_mph=wind_speed,
            wind_direction=wind_dir,
            visibility_miles=10 if not has_precip else 5,
            cloud_ceiling_ft=None,
            weather_description=weather_desc,
            precipitation=has_precip,
            storm_activity=False,
            turbulence_risk=turbulence,
            updated_at=time.time()
        )
    
    def get_weather_for_location(self, lat: float, lon: float) -> WeatherCondition:
        """Get weather data with fallback strategy"""
        cache_key = f"{lat:.3f},{lon:.3f}"
        
        # Check cache
        if cache_key in self.weather_cache:
            cached_weather, cache_time = self.weather_cache[cache_key]
            if time.time() - cache_time < self.cache_duration:
                return cached_weather
        
        # Try NWS first (free, reliable for US)
        weather = self.get_weather_data_nws(lat, lon)
        
        # Try OpenWeatherMap if NWS fails and we have API key
        if not weather and self.api_key:
            weather = self.get_weather_data_openweather(lat, lon)
        
        # Fall back to synthetic data
        if not weather:
            weather = self.get_synthetic_weather(lat, lon)
        
        # Cache result
        self.weather_cache[cache_key] = (weather, time.time())
        
        return weather
    
    def assess_weather_impact(self, weather: WeatherCondition, aircraft_altitude: int) -> WeatherImpact:
        """Assess how weather conditions impact flight operations"""
        impact_level = "NONE"
        reasons = []
        recommendations = []
        altitude_effects = {}
        
        # Visibility impacts
        if weather.visibility_miles < 1:
            impact_level = "SEVERE"
            reasons.append(f"Very low visibility: {weather.visibility_miles:.1f} miles")
            recommendations.append("IFR conditions - visual flight prohibited")
        elif weather.visibility_miles < 3:
            impact_level = max(impact_level, "HIGH", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
            reasons.append(f"Low visibility: {weather.visibility_miles:.1f} miles")
            recommendations.append("Reduced visibility - exercise caution")
        elif weather.visibility_miles < 5:
            impact_level = max(impact_level, "MEDIUM", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
            reasons.append(f"Moderate visibility: {weather.visibility_miles:.1f} miles")
        
        visibility_effect = f"Visibility: {weather.visibility_miles:.1f} miles"
        
        # Wind impacts
        if weather.wind_speed_mph > 35:
            impact_level = max(impact_level, "HIGH", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
            reasons.append(f"High winds: {weather.wind_speed_mph:.0f} mph")
            recommendations.append("Strong wind conditions - expect turbulence")
        elif weather.wind_speed_mph > 20:
            impact_level = max(impact_level, "MEDIUM", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
            reasons.append(f"Moderate winds: {weather.wind_speed_mph:.0f} mph")
            recommendations.append("Moderate winds - possible turbulence")
        
        # Precipitation impacts
        if weather.precipitation:
            if "heavy" in weather.weather_description:
                impact_level = max(impact_level, "HIGH", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
                reasons.append("Heavy precipitation")
                recommendations.append("Heavy precipitation - reduced performance")
            else:
                impact_level = max(impact_level, "MEDIUM", key=lambda x: ["NONE", "LOW", "MEDIUM", "HIGH", "SEVERE"].index(x))
                reasons.append("Precipitation present")
                recommendations.append("Wet conditions - exercise caution")
        
        # Storm activity
        if weather.storm_activity:
            impact_level = "SEVERE"
            reasons.append("Thunderstorm activity")
            recommendations.append("Thunderstorms present - avoid area")
        
        # Temperature effects on altitude
        if weather.temperature_f > 90:
            altitude_effects["high_temp"] = "Reduced aircraft performance due to high temperature"
        elif weather.temperature_f < 20:
            altitude_effects["low_temp"] = "Cold temperature - possible icing conditions"
        
        # Pressure effects
        if weather.pressure_mb < 1000:
            altitude_effects["low_pressure"] = "Low pressure system - altimeter reads higher than actual"
        elif weather.pressure_mb > 1030:
            altitude_effects["high_pressure"] = "High pressure system - altimeter reads lower than actual"
        
        return WeatherImpact(
            condition=weather,
            flight_impact_level=impact_level,
            reasons=reasons,
            recommended_actions=recommendations,
            altitude_effects=altitude_effects,
            visibility_effects=visibility_effect
        )
    
    def explain_aircraft_behavior(self, aircraft_data: Dict, weather_impact: WeatherImpact) -> List[str]:
        """Provide weather-based explanations for aircraft behavior"""
        explanations = []
        
        altitude = aircraft_data.get('alt_baro', aircraft_data.get('alt_geom', 0))
        speed = aircraft_data.get('gs', 0)
        
        # Low altitude explanations
        if altitude < 2000:
            if weather_impact.condition.visibility_miles < 3:
                explanations.append("Low altitude flight may be due to poor visibility conditions")
            if weather_impact.condition.wind_speed_mph > 25:
                explanations.append("Low altitude may be to avoid strong winds aloft")
            if weather_impact.condition.storm_activity:
                explanations.append("Low altitude likely due to storm avoidance")
        
        # Speed explanations
        if speed < 100:
            if weather_impact.condition.wind_speed_mph > 20:
                explanations.append("Reduced ground speed likely due to headwinds")
            if weather_impact.condition.turbulence_risk == 'HIGH':
                explanations.append("Reduced speed may be due to turbulent conditions")
        
        # Circling explanations
        if weather_impact.condition.visibility_miles < 1:
            explanations.append("Circling pattern may be due to poor visibility - holding for conditions to improve")
        
        # Route deviations
        if weather_impact.condition.storm_activity:
            explanations.append("Route deviations expected due to thunderstorm activity")
        
        return explanations
    
    def should_suppress_alert(self, aircraft_data: Dict, alert_type: str) -> Tuple[bool, str]:
        """Determine if weather conditions justify suppressing an alert"""
        lat = aircraft_data.get('lat')
        lon = aircraft_data.get('lon')
        
        if not lat or not lon:
            return False, "No position data"
        
        weather = self.get_weather_for_location(lat, lon)
        impact = self.assess_weather_impact(weather, aircraft_data.get('alt_baro', 0))
        
        # Low altitude alerts
        if alert_type == 'LOW_ALTITUDE':
            if impact.flight_impact_level in ['HIGH', 'SEVERE']:
                return True, f"Severe weather conditions justify low altitude: {', '.join(impact.reasons)}"
            if weather.storm_activity:
                return True, "Thunderstorm activity - low altitude for storm avoidance"
            if weather.visibility_miles < 2:
                return True, f"Poor visibility ({weather.visibility_miles:.1f} mi) may require low altitude flight"
        
        # Speed alerts
        if alert_type == 'LOW_SPEED':
            if weather.wind_speed_mph > 25:
                return True, f"Strong headwinds ({weather.wind_speed_mph:.0f} mph) causing reduced ground speed"
            if weather.turbulence_risk == 'HIGH':
                return True, "High turbulence conditions may require reduced speed"
        
        # Circling alerts
        if alert_type == 'CIRCLING':
            if weather.visibility_miles < 1:
                return True, f"Very poor visibility ({weather.visibility_miles:.1f} mi) - likely holding pattern"
            if weather.storm_activity:
                return True, "Storm activity - aircraft may be in holding pattern"
        
        return False, "Weather does not explain behavior"

# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test weather system
    weather_provider = WeatherContextProvider()
    
    # Test locations
    test_locations = [
        (34.1133171, -80.9024019, "Charlotte, NC"),
        (35.214, -80.943, "CLT Airport"),
        (36.098, -79.937, "Greensboro, NC")
    ]
    
    for lat, lon, name in test_locations:
        print(f"\nWeather for {name}:")
        weather = weather_provider.get_weather_for_location(lat, lon)
        impact = weather_provider.assess_weather_impact(weather, 2000)
        
        print(f"  Conditions: {weather.weather_description}")
        print(f"  Temperature: {weather.temperature_f:.0f}°F")
        print(f"  Wind: {weather.wind_speed_mph:.0f} mph from {weather.wind_direction}°")
        print(f"  Visibility: {weather.visibility_miles:.1f} miles")
        print(f"  Flight Impact: {impact.flight_impact_level}")
        if impact.reasons:
            print(f"  Reasons: {', '.join(impact.reasons)}")
        
        # Test alert suppression
        test_aircraft = {'lat': lat, 'lon': lon, 'alt_baro': 800, 'gs': 60}
        suppress, reason = weather_provider.should_suppress_alert(test_aircraft, 'LOW_ALTITUDE')
        print(f"  Suppress low altitude alert: {suppress} - {reason}")