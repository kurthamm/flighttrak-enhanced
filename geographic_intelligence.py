#!/usr/bin/env python3
"""
Geographic Intelligence Module for FlightTrak
Identifies locations, nearby landmarks, and correlates with news sources
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class LocationIntelligence:
    """Geographic intelligence about a location"""
    coordinates: Tuple[float, float]
    address: str
    place_type: str
    nearby_landmarks: List[str]
    location_description: str
    news_stories: List[Dict]
    risk_assessment: str

class GeographicIntelligence:
    """Geographic intelligence and news correlation system"""
    
    def __init__(self):
        self.cache = {}  # Cache results to avoid repeated API calls
        self.cache_duration = 3600  # 1 hour cache
        
        # Rate limiting
        self.last_api_call = 0
        self.min_api_interval = 1.0  # 1 second between API calls
        
        logging.info("Geographic Intelligence system initialized")
    
    def analyze_location(self, lat: float, lon: float) -> LocationIntelligence:
        """Complete geographic analysis of a location"""
        
        # Check cache first
        cache_key = f"{lat:.4f},{lon:.4f}"
        if cache_key in self.cache:
            cached_result, cache_time = self.cache[cache_key]
            if time.time() - cache_time < self.cache_duration:
                return cached_result
        
        # Rate limiting
        time_since_last = time.time() - self.last_api_call
        if time_since_last < self.min_api_interval:
            time.sleep(self.min_api_interval - time_since_last)
        
        try:
            # Get location details
            location_data = self.reverse_geocode(lat, lon)
            
            # Get nearby landmarks and points of interest
            landmarks = self.get_nearby_landmarks(lat, lon)
            
            # Search for relevant news
            news_stories = self.search_location_news(lat, lon, location_data.get('address', ''))
            
            # Create intelligence report
            intel = LocationIntelligence(
                coordinates=(lat, lon),
                address=location_data.get('address', 'Unknown location'),
                place_type=location_data.get('place_type', 'unknown'),
                nearby_landmarks=landmarks,
                location_description=self.generate_location_description(location_data, landmarks),
                news_stories=news_stories,
                risk_assessment=self.assess_location_risk(location_data, landmarks)
            )
            
            # Cache result
            self.cache[cache_key] = (intel, time.time())
            self.last_api_call = time.time()
            
            return intel
            
        except Exception as e:
            logging.error(f"Error analyzing location {lat}, {lon}: {e}")
            # Return basic intelligence
            return LocationIntelligence(
                coordinates=(lat, lon),
                address=f"Location near {lat:.3f}, {lon:.3f}",
                place_type="unknown",
                nearby_landmarks=[],
                location_description="Location details unavailable",
                news_stories=[],
                risk_assessment="unknown"
            )
    
    def reverse_geocode(self, lat: float, lon: float) -> Dict:
        """Get location details from coordinates using OpenStreetMap Nominatim"""
        try:
            # Using OpenStreetMap Nominatim (free)
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,
                'addressdetails': 1,
                'extratags': 1
            }
            headers = {
                'User-Agent': 'FlightTrak-Intelligence/1.0'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            address_components = data.get('address', {})
            
            # Determine place type from the response
            place_type = self.determine_place_type(data)
            
            return {
                'address': data.get('display_name', 'Unknown location'),
                'place_type': place_type,
                'city': address_components.get('city', address_components.get('town', address_components.get('village', ''))),
                'state': address_components.get('state', ''),
                'country': address_components.get('country', ''),
                'postcode': address_components.get('postcode', ''),
                'raw_data': data
            }
            
        except Exception as e:
            logging.error(f"Reverse geocoding error: {e}")
            return {'address': f"Location near {lat:.3f}, {lon:.3f}", 'place_type': 'unknown'}
    
    def determine_place_type(self, geocode_data: Dict) -> str:
        """Determine the type of place from geocoding data"""
        category = geocode_data.get('category', '')
        type_field = geocode_data.get('type', '')
        class_field = geocode_data.get('class', '')
        
        # Map OSM categories to readable place types
        place_mappings = {
            'aeroway': 'airport',
            'amenity': {
                'hospital': 'hospital',
                'school': 'school',
                'university': 'university',
                'police': 'police_station',
                'fire_station': 'fire_station',
                'fuel': 'gas_station',
                'parking': 'parking',
                'restaurant': 'restaurant',
                'bank': 'bank',
                'pharmacy': 'pharmacy',
                'place_of_worship': 'religious_site'
            },
            'building': 'building',
            'highway': 'road',
            'landuse': {
                'industrial': 'industrial_area',
                'commercial': 'commercial_area',
                'residential': 'residential_area',
                'retail': 'shopping_area',
                'cemetery': 'cemetery',
                'military': 'military_facility'
            },
            'leisure': {
                'park': 'park',
                'sports_centre': 'sports_facility',
                'stadium': 'stadium',
                'golf_course': 'golf_course'
            },
            'shop': 'retail_store',
            'tourism': 'tourist_attraction',
            'natural': 'natural_feature'
        }
        
        if category in place_mappings:
            if isinstance(place_mappings[category], dict):
                return place_mappings[category].get(type_field, category)
            else:
                return place_mappings[category]
        
        return type_field or 'unknown'
    
    def get_nearby_landmarks(self, lat: float, lon: float, radius_km: float = 2.0) -> List[str]:
        """Get nearby landmarks and points of interest"""
        try:
            # Using Overpass API to get nearby notable places
            overpass_url = "http://overpass-api.de/api/interpreter"
            
            # Query for notable places within radius
            query = f"""
            [out:json][timeout:25];
            (
              node["amenity"~"^(hospital|school|university|police|fire_station)$"](around:{radius_km*1000},{lat},{lon});
              node["landuse"~"^(industrial|commercial|military)$"](around:{radius_km*1000},{lat},{lon});
              node["leisure"~"^(stadium|sports_centre|park)$"](around:{radius_km*1000},{lat},{lon});
              node["aeroway"="aerodrome"](around:{radius_km*1000},{lat},{lon});
              node["tourism"](around:{radius_km*1000},{lat},{lon});
              way["amenity"~"^(hospital|school|university|police|fire_station)$"](around:{radius_km*1000},{lat},{lon});
              way["landuse"~"^(industrial|commercial|military)$"](around:{radius_km*1000},{lat},{lon});
            );
            out geom;
            """
            
            response = requests.post(overpass_url, data=query, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            landmarks = []
            for element in data.get('elements', [])[:10]:  # Limit to 10 closest
                tags = element.get('tags', {})
                name = tags.get('name', '')
                amenity = tags.get('amenity', '')
                landuse = tags.get('landuse', '')
                leisure = tags.get('leisure', '')
                
                if name:
                    if amenity:
                        landmarks.append(f"{name} ({amenity})")
                    elif landuse:
                        landmarks.append(f"{name} ({landuse})")
                    elif leisure:
                        landmarks.append(f"{name} ({leisure})")
                    else:
                        landmarks.append(name)
            
            return landmarks[:5]  # Return top 5
            
        except Exception as e:
            logging.error(f"Error getting landmarks: {e}")
            return []
    
    def search_location_news(self, lat: float, lon: float, address: str) -> List[Dict]:
        """Search for recent news stories related to this location"""
        try:
            news_stories = []
            
            # Extract location keywords for news search
            search_terms = self.extract_location_keywords(address)
            
            if not search_terms:
                return []
            
            # Search multiple news sources
            news_stories.extend(self.search_google_news(search_terms))
            news_stories.extend(self.search_reddit_local(lat, lon, search_terms))
            
            # Filter and rank by relevance and recency
            filtered_stories = self.filter_relevant_news(news_stories, search_terms)
            
            return filtered_stories[:3]  # Return top 3 most relevant
            
        except Exception as e:
            logging.error(f"Error searching location news: {e}")
            return []
    
    def extract_location_keywords(self, address: str) -> List[str]:
        """Extract searchable keywords from address"""
        keywords = []
        
        # Common address components to search for
        components = address.split(',')
        for component in components:
            component = component.strip()
            # Skip very generic terms
            if len(component) > 3 and component not in ['USA', 'United States']:
                keywords.append(component)
        
        return keywords[:3]  # Limit to avoid overly complex searches
    
    def search_google_news(self, search_terms: List[str]) -> List[Dict]:
        """Search Google News RSS (free but limited)"""
        try:
            stories = []
            
            for term in search_terms[:2]:  # Limit searches
                # Google News RSS search
                url = f"https://news.google.com/rss/search"
                params = {
                    'q': f"{term} incident OR emergency OR breaking",
                    'hl': 'en-US',
                    'gl': 'US',
                    'ceid': 'US:en'
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                # Parse RSS would need additional parsing, for now return basic structure
                # This is a simplified version - full implementation would parse RSS
                if "incident" in response.text.lower() or "emergency" in response.text.lower():
                    stories.append({
                        'title': f"Potential news activity near {term}",
                        'source': 'Google News',
                        'url': f"https://news.google.com/search?q={term}+incident",
                        'published': datetime.now().isoformat(),
                        'relevance': 0.7
                    })
            
            return stories
            
        except Exception as e:
            logging.error(f"Google News search error: {e}")
            return []
    
    def search_reddit_local(self, lat: float, lon: float, search_terms: List[str]) -> List[Dict]:
        """Search Reddit for local mentions (using their API)"""
        try:
            # This would integrate with Reddit API to search local subreddits
            # For now, return empty list - full implementation would require Reddit API setup
            return []
            
        except Exception as e:
            logging.error(f"Reddit search error: {e}")
            return []
    
    def filter_relevant_news(self, stories: List[Dict], search_terms: List[str]) -> List[Dict]:
        """Filter and rank news stories by relevance"""
        # Simple relevance scoring
        for story in stories:
            relevance = 0.0
            title_lower = story.get('title', '').lower()
            
            # Boost for emergency keywords
            emergency_keywords = ['emergency', 'incident', 'crash', 'fire', 'accident', 'breaking']
            for keyword in emergency_keywords:
                if keyword in title_lower:
                    relevance += 0.3
            
            # Boost for location match
            for term in search_terms:
                if term.lower() in title_lower:
                    relevance += 0.2
            
            story['relevance'] = relevance
        
        # Sort by relevance and recency
        return sorted(stories, key=lambda x: x.get('relevance', 0), reverse=True)
    
    def generate_location_description(self, location_data: Dict, landmarks: List[str]) -> str:
        """Generate human-readable location description"""
        place_type = location_data.get('place_type', 'unknown')
        address = location_data.get('address', '')
        
        # Generate contextual description
        if place_type == 'hospital':
            description = f"Medical facility area - {address}"
        elif place_type == 'airport':
            description = f"Aviation facility - {address}"
        elif place_type == 'industrial_area':
            description = f"Industrial zone - {address}"
        elif place_type == 'residential_area':
            description = f"Residential neighborhood - {address}"
        elif place_type == 'commercial_area':
            description = f"Commercial district - {address}"
        elif place_type == 'school' or place_type == 'university':
            description = f"Educational institution area - {address}"
        elif landmarks:
            description = f"Area near {landmarks[0]} - {address}"
        else:
            description = address
        
        return description
    
    def assess_location_risk(self, location_data: Dict, landmarks: List[str]) -> str:
        """Assess potential risk level of location"""
        place_type = location_data.get('place_type', 'unknown')
        
        # Risk assessment based on location type
        high_risk_types = ['hospital', 'airport', 'military_facility', 'police_station', 'industrial_area']
        medium_risk_types = ['school', 'university', 'commercial_area', 'stadium']
        
        if place_type in high_risk_types:
            return 'HIGH'
        elif place_type in medium_risk_types:
            return 'MEDIUM'
        elif any('hospital' in landmark.lower() or 'airport' in landmark.lower() for landmark in landmarks):
            return 'MEDIUM'
        else:
            return 'LOW'

def main():
    """Test the geographic intelligence system"""
    geo_intel = GeographicIntelligence()
    
    # Test with a location
    test_lat, test_lon = 37.7749, -122.4194  # San Francisco
    result = geo_intel.analyze_location(test_lat, test_lon)
    
    print(f"Location: {result.location_description}")
    print(f"Place Type: {result.place_type}")
    print(f"Risk Level: {result.risk_assessment}")
    print(f"Nearby: {result.nearby_landmarks}")
    if result.news_stories:
        print("Recent News:")
        for story in result.news_stories:
            print(f"  - {story['title']}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()