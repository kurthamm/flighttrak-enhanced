#!/usr/bin/env python3
"""
Enhanced Intelligence Sources for FlightTrak
Multiple news sources, emergency feeds, and enhanced location intelligence
"""

import requests
import json
import time
import logging
import xml.etree.ElementTree as ET
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
import urllib.parse

@dataclass
class NewsStory:
    """Enhanced news story with more metadata"""
    title: str
    url: str
    source: str
    published: str
    description: str
    relevance_score: float
    story_type: str  # breaking, incident, emergency, local
    location_match: bool
    keywords: List[str]

@dataclass
class EmergencyFeed:
    """Emergency scanner/radio feed data"""
    feed_type: str  # police, fire, ems, aviation
    frequency: str
    description: str
    location: str
    activity_level: str  # high, medium, low
    recent_calls: List[Dict]

class EnhancedIntelligenceSources:
    """Enhanced multi-source intelligence gathering"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes for news
        self.location_cache_duration = 7200  # 2 hours for location data
        
        # Load intelligence configuration
        try:
            from intelligence_config import IntelligenceConfig
            self.intelligence_config = IntelligenceConfig()
        except ImportError:
            self.intelligence_config = None
            logging.warning("Intelligence configuration not available - using defaults")
        
        # API rate limiting
        self.api_limits = {
            'newsapi': {'calls': 0, 'reset_time': time.time() + 3600, 'limit': 500},
            'reddit': {'calls': 0, 'reset_time': time.time() + 3600, 'limit': 60},
            'mapbox': {'calls': 0, 'reset_time': time.time() + 3600, 'limit': 100000},
            'here': {'calls': 0, 'reset_time': time.time() + 3600, 'limit': 1000}
        }
        
        logging.info("Enhanced Intelligence Sources initialized")
    
    def get_comprehensive_location_intelligence(self, lat: float, lon: float) -> Dict:
        """Get location data from multiple enhanced sources"""
        cache_key = f"location_{lat:.4f}_{lon:.4f}"
        
        # Check cache
        if cache_key in self.cache:
            cached_data, cache_time = self.cache[cache_key]
            if time.time() - cache_time < self.location_cache_duration:
                return cached_data
        
        location_data = {
            'coordinates': (lat, lon),
            'primary_address': '',
            'detailed_address': {},
            'place_types': [],
            'landmarks': [],
            'risk_factors': [],
            'what3words': '',
            'timezone': '',
            'demographics': {},
            'infrastructure': []
        }
        
        try:
            # Get data from multiple sources
            osm_data = self.get_openstreetmap_data(lat, lon)
            mapbox_data = self.get_mapbox_data(lat, lon)
            here_data = self.get_here_maps_data(lat, lon)
            what3words_data = self.get_what3words_data(lat, lon)
            
            # Combine and enhance data
            location_data = self.merge_location_data(
                osm_data, mapbox_data, here_data, what3words_data, lat, lon
            )
            
            # Cache result
            self.cache[cache_key] = (location_data, time.time())
            
        except Exception as e:
            logging.error(f"Enhanced location intelligence failed: {e}")
        
        return location_data
    
    def get_openstreetmap_data(self, lat: float, lon: float) -> Dict:
        """Get basic location data from OpenStreetMap (free)"""
        try:
            # OpenStreetMap Nominatim API
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 18
            }
            
            headers = {'User-Agent': 'FlightTrak-Intelligence/1.0'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'display_name': data.get('display_name', ''),
                    'address': data.get('address', {}),
                    'place_type': data.get('type', ''),
                    'importance': data.get('importance', 0)
                }
            
        except Exception as e:
            logging.error(f"OpenStreetMap API error: {e}")
        
        return {}
    
    def merge_location_data(self, osm_data: Dict, mapbox_data: Dict, here_data: Dict, what3words_data: Dict, lat: float, lon: float) -> Dict:
        """Merge location data from multiple sources"""
        merged = {
            'coordinates': (lat, lon),
            'primary_address': '',
            'detailed_address': {},
            'place_types': [],
            'landmarks': [],
            'risk_factors': [],
            'what3words': what3words_data.get('what3words', ''),
            'timezone': '',
            'demographics': {},
            'infrastructure': []
        }
        
        # Use OSM as primary source
        if osm_data:
            merged['primary_address'] = osm_data.get('display_name', '')
            merged['detailed_address'] = osm_data.get('address', {})
            merged['place_types'].append(osm_data.get('place_type', ''))
        
        # Enhance with MapBox data
        if mapbox_data:
            merged['place_types'].extend(mapbox_data.get('types', []))
            merged['landmarks'].extend(mapbox_data.get('landmarks', []))
        
        # Enhance with HERE data
        if here_data:
            merged['place_types'].extend(here_data.get('types', []))
            merged['infrastructure'].extend(here_data.get('infrastructure', []))
        
        # Clean up duplicates
        merged['place_types'] = list(set(merged['place_types']))
        merged['landmarks'] = list(set(merged['landmarks']))
        
        return merged
    
    def check_rate_limit(self, service: str) -> bool:
        """Check if API rate limit allows request"""
        if service not in self.api_limits:
            return True
            
        limit_info = self.api_limits[service]
        current_time = time.time()
        
        # Reset counters if past reset time
        if current_time > limit_info['reset_time']:
            limit_info['calls'] = 0
            limit_info['reset_time'] = current_time + 3600  # Reset every hour
        
        # Check if under limit
        return limit_info['calls'] < limit_info['limit']
    
    def extract_enhanced_search_terms(self, location_data: Dict) -> List[str]:
        """Extract search terms from location data"""
        terms = []
        
        # Extract from address components
        address = location_data.get('detailed_address', {})
        for key, value in address.items():
            if key in ['city', 'town', 'village', 'county', 'state', 'neighbourhood']:
                if value:
                    terms.append(value)
        
        # Extract from place types
        place_types = location_data.get('place_types', [])
        for place_type in place_types:
            if place_type in ['hospital', 'airport', 'school', 'mall', 'factory', 'government']:
                terms.append(place_type)
        
        # Extract from landmarks
        landmarks = location_data.get('landmarks', [])
        terms.extend(landmarks[:3])  # Top 3 landmarks
        
        # If no terms, use general location terms
        if not terms:
            primary_address = location_data.get('primary_address', '')
            if primary_address:
                # Extract city/state from address
                parts = primary_address.split(',')
                if len(parts) >= 2:
                    terms.append(parts[-2].strip())  # City/town
                    terms.append(parts[-1].strip())  # State/country
        
        return list(set(terms))[:5]  # Unique terms, max 5
    
    def parse_mapbox_response(self, data: Dict) -> Dict:
        """Parse MapBox API response"""
        result = {'types': [], 'landmarks': []}
        
        features = data.get('features', [])
        for feature in features[:3]:  # Top 3 results
            properties = feature.get('properties', {})
            result['types'].append(properties.get('category', ''))
            result['landmarks'].append(properties.get('text', ''))
        
        return result
    
    def parse_here_response(self, data: Dict) -> Dict:
        """Parse HERE Maps API response"""
        result = {'types': [], 'infrastructure': []}
        
        items = data.get('items', [])
        for item in items[:3]:  # Top 3 results
            categories = item.get('categories', [])
            for category in categories:
                result['types'].append(category.get('name', ''))
        
        return result
    
    def get_comprehensive_news_intelligence(self, lat: float, lon: float, location_data: Dict) -> List[NewsStory]:
        """Get news from multiple enhanced sources"""
        cache_key = f"news_{lat:.3f}_{lon:.3f}"
        
        # Check cache
        if cache_key in self.cache:
            cached_stories, cache_time = self.cache[cache_key]
            if time.time() - cache_time < self.cache_duration:
                return cached_stories
        
        all_stories = []
        search_terms = self.extract_enhanced_search_terms(location_data)
        
        try:
            # Multiple news sources
            all_stories.extend(self.search_newsapi(search_terms, lat, lon))
            all_stories.extend(self.search_reddit_enhanced(search_terms, lat, lon))
            all_stories.extend(self.search_local_news_rss(search_terms, location_data))
            all_stories.extend(self.search_google_news_enhanced(search_terms))
            all_stories.extend(self.search_emergency_feeds(lat, lon, location_data))
            all_stories.extend(self.search_aviation_feeds(lat, lon))
            
            # Deduplicate and rank
            unique_stories = self.deduplicate_and_rank_stories(all_stories, search_terms)
            
            # Cache result
            self.cache[cache_key] = (unique_stories, time.time())
            
            return unique_stories[:10]  # Top 10 most relevant
            
        except Exception as e:
            logging.error(f"Enhanced news intelligence failed: {e}")
            return []
    
    def get_mapbox_data(self, lat: float, lon: float) -> Dict:
        """Get enhanced location data from MapBox (100k free/month)"""
        if not self.check_rate_limit('mapbox'):
            return {}
        
        try:
            # MapBox Geocoding API
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
            params = {
                'access_token': self.intelligence_config.get_api_key('mapbox') if self.intelligence_config else None,
                'types': 'poi,address,neighborhood,locality,place',
                'limit': 5
            }
            
            if not params['access_token']:
                return {}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.parse_mapbox_response(data)
            
        except Exception as e:
            logging.error(f"MapBox API error: {e}")
        
        return {}
    
    def get_here_maps_data(self, lat: float, lon: float) -> Dict:
        """Get location data from HERE Maps (free tier)"""
        if not self.check_rate_limit('here'):
            return {}
        
        try:
            # HERE Reverse Geocoding
            url = "https://revgeocode.search.hereapi.com/v1/revgeocode"
            params = {
                'at': f"{lat},{lon}",
                'apikey': self.intelligence_config.get_api_key('here') if self.intelligence_config else None,
                'lang': 'en-US',
                'limit': 5
            }
            
            if not params['apikey']:
                return {}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.parse_here_response(data)
            
        except Exception as e:
            logging.error(f"HERE Maps API error: {e}")
        
        return {}
    
    def get_what3words_data(self, lat: float, lon: float) -> Dict:
        """Get What3Words address (1k free/day)"""
        try:
            # What3Words API
            url = f"https://api.what3words.com/v3/convert-to-3wa"
            params = {
                'coordinates': f"{lat},{lon}",
                'key': self.intelligence_config.get_api_key('what3words') if self.intelligence_config else None,
                'format': 'json'
            }
            
            if not params['key']:
                return {}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {'what3words': data.get('words', '')}
            
        except Exception as e:
            logging.error(f"What3Words API error: {e}")
        
        return {}
    
    def search_newsapi(self, search_terms: List[str], lat: float, lon: float) -> List[NewsStory]:
        """Search NewsAPI.org (500 free requests/day)"""
        if not self.check_rate_limit('newsapi'):
            return []
        
        stories = []
        
        try:
            # Get location-based search terms
            location_query = " OR ".join(search_terms[:3])
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': self.intelligence_config.get_api_key('newsapi') if self.intelligence_config else None,
                'q': f'({location_query}) AND (emergency OR incident OR breaking OR alert)',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 20,
                'from': (datetime.now() - timedelta(days=1)).isoformat()
            }
            
            if not params['apiKey']:
                return []
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                for article in data.get('articles', [])[:10]:
                    story = NewsStory(
                        title=article.get('title', ''),
                        url=article.get('url', ''),
                        source=article.get('source', {}).get('name', 'NewsAPI'),
                        published=article.get('publishedAt', ''),
                        description=article.get('description', ''),
                        relevance_score=self.calculate_relevance(article, search_terms),
                        story_type='breaking',
                        location_match=True,
                        keywords=search_terms
                    )
                    stories.append(story)
            
            self.api_limits['newsapi']['calls'] += 1
            
        except Exception as e:
            logging.error(f"NewsAPI search error: {e}")
        
        return stories
    
    def search_reddit_enhanced(self, search_terms: List[str], lat: float, lon: float) -> List[NewsStory]:
        """Enhanced Reddit search with local subreddits"""
        if not self.check_rate_limit('reddit'):
            return []
        
        stories = []
        
        try:
            # Determine local subreddits based on location
            local_subreddits = self.get_local_subreddits(lat, lon)
            
            for subreddit in local_subreddits[:3]:  # Top 3 local subs
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    'q': " OR ".join(search_terms),
                    'sort': 'new',
                    'limit': 10,
                    't': 'day'  # Last day
                }
                
                headers = {'User-Agent': 'FlightTrak-Intelligence/1.0'}
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for post in data.get('data', {}).get('children', [])[:5]:
                        post_data = post.get('data', {})
                        
                        # Filter for emergency/incident keywords
                        title = post_data.get('title', '').lower()
                        if any(keyword in title for keyword in ['emergency', 'incident', 'breaking', 'alert', 'crash', 'fire']):
                            story = NewsStory(
                                title=post_data.get('title', ''),
                                url=f"https://reddit.com{post_data.get('permalink', '')}",
                                source=f"Reddit r/{subreddit}",
                                published=datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                description=post_data.get('selftext', '')[:200],
                                relevance_score=self.calculate_reddit_relevance(post_data, search_terms),
                                story_type='local',
                                location_match=True,
                                keywords=search_terms
                            )
                            stories.append(story)
            
            self.api_limits['reddit']['calls'] += 1
            
        except Exception as e:
            logging.error(f"Reddit enhanced search error: {e}")
        
        return stories
    
    def search_local_news_rss(self, search_terms: List[str], location_data: Dict) -> List[NewsStory]:
        """Search local news RSS feeds"""
        stories = []
        
        try:
            # Get local news sources based on location
            local_feeds = self.get_local_news_feeds(location_data)
            
            for feed_url in local_feeds[:5]:  # Top 5 local feeds
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:10]:
                        title = entry.get('title', '').lower()
                        description = entry.get('description', '').lower()
                        
                        # Check for relevant keywords
                        relevance = 0
                        for term in search_terms:
                            if term.lower() in title or term.lower() in description:
                                relevance += 0.3
                        
                        # Check for emergency keywords
                        emergency_keywords = ['emergency', 'incident', 'breaking', 'alert', 'crash', 'fire', 'police', 'ambulance']
                        for keyword in emergency_keywords:
                            if keyword in title or keyword in description:
                                relevance += 0.5
                        
                        if relevance > 0.3:  # Only include relevant stories
                            story = NewsStory(
                                title=entry.get('title', ''),
                                url=entry.get('link', ''),
                                source=feed.feed.get('title', 'Local News'),
                                published=entry.get('published', ''),
                                description=entry.get('description', ''),
                                relevance_score=relevance,
                                story_type='local',
                                location_match=True,
                                keywords=search_terms
                            )
                            stories.append(story)
                
                except Exception as e:
                    logging.error(f"RSS feed error for {feed_url}: {e}")
                    continue
            
        except Exception as e:
            logging.error(f"Local news RSS search error: {e}")
        
        return stories
    
    def search_emergency_feeds(self, lat: float, lon: float, location_data: Dict) -> List[NewsStory]:
        """Search emergency scanner feeds and dispatch logs"""
        stories = []
        
        try:
            # Emergency scanner feeds (simulated - would integrate with real services)
            scanner_feeds = self.get_emergency_scanner_data(lat, lon)
            
            for feed in scanner_feeds:
                if feed.activity_level in ['high', 'medium']:
                    for call in feed.recent_calls[:3]:
                        story = NewsStory(
                            title=f"{feed.feed_type.upper()} Activity: {call.get('type', 'Unknown')}",
                            url=f"https://scanner.local/{feed.frequency}",  # Would be real scanner URLs
                            source=f"Emergency Scanner ({feed.frequency})",
                            published=call.get('timestamp', datetime.now().isoformat()),
                            description=call.get('description', ''),
                            relevance_score=0.8 if feed.activity_level == 'high' else 0.6,
                            story_type='emergency',
                            location_match=True,
                            keywords=['emergency', 'scanner']
                        )
                        stories.append(story)
        
        except Exception as e:
            logging.error(f"Emergency feeds search error: {e}")
        
        return stories
    
    def search_aviation_feeds(self, lat: float, lon: float) -> List[NewsStory]:
        """Search aviation-specific feeds and NOTAMs"""
        stories = []
        
        try:
            # Aviation feeds (would integrate with real aviation data sources)
            # FAA NOTAMs, aviation weather, TFRs, etc.
            
            # Example: Check for nearby TFRs (Temporary Flight Restrictions)
            tfr_data = self.check_nearby_tfrs(lat, lon)
            
            for tfr in tfr_data:
                story = NewsStory(
                    title=f"TFR Active: {tfr.get('reason', 'Flight Restriction')}",
                    url=tfr.get('url', 'https://tfr.faa.gov'),
                    source="FAA TFR System",
                    published=tfr.get('start_time', datetime.now().isoformat()),
                    description=tfr.get('description', ''),
                    relevance_score=0.9,  # TFRs are highly relevant for aviation
                    story_type='aviation',
                    location_match=True,
                    keywords=['aviation', 'tfr', 'flight restriction']
                )
                stories.append(story)
        
        except Exception as e:
            logging.error(f"Aviation feeds search error: {e}")
        
        return stories
    
    # Helper methods
    def check_rate_limit(self, api_name: str) -> bool:
        """Check if API rate limit allows another call"""
        limit_info = self.api_limits.get(api_name, {})
        current_time = time.time()
        
        if current_time > limit_info.get('reset_time', 0):
            # Reset counter
            limit_info['calls'] = 0
            limit_info['reset_time'] = current_time + 3600
        
        return limit_info.get('calls', 0) < limit_info.get('limit', 1000)
    
    def extract_enhanced_search_terms(self, location_data: Dict) -> List[str]:
        """Extract comprehensive search terms from location data"""
        terms = []
        
        # Add address components
        if 'detailed_address' in location_data:
            addr = location_data['detailed_address']
            terms.extend([
                addr.get('city', ''),
                addr.get('neighborhood', ''),
                addr.get('county', ''),
                addr.get('road', '')
            ])
        
        # Add landmarks
        terms.extend(location_data.get('landmarks', []))
        
        # Add place types
        terms.extend(location_data.get('place_types', []))
        
        # Clean and filter terms
        terms = [term.strip() for term in terms if term and len(term) > 2]
        return list(set(terms))[:5]  # Unique terms, max 5
    
    def calculate_relevance(self, article: Dict, search_terms: List[str]) -> float:
        """Calculate story relevance score"""
        score = 0.0
        
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        
        # Location match
        for term in search_terms:
            if term.lower() in title:
                score += 0.3
            if term.lower() in description:
                score += 0.2
        
        # Emergency keywords
        emergency_words = ['emergency', 'breaking', 'incident', 'crash', 'fire', 'police', 'ambulance', 'evacuation']
        for word in emergency_words:
            if word in title:
                score += 0.4
            if word in description:
                score += 0.2
        
        # Recency bonus
        pub_date = article.get('publishedAt', '')
        if pub_date:
            try:
                pub_time = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                hours_ago = (datetime.now() - pub_time.replace(tzinfo=None)).total_seconds() / 3600
                if hours_ago < 6:  # Within 6 hours
                    score += 0.3
                elif hours_ago < 24:  # Within 24 hours
                    score += 0.1
            except:
                pass
        
        return min(score, 1.0)
    
    def get_local_subreddits(self, lat: float, lon: float) -> List[str]:
        """Get local subreddits based on coordinates"""
        # This would be enhanced with a database of geographic subreddits
        # For now, return some common patterns
        return ['news', 'local', 'breaking', 'emergency', 'police']
    
    def get_local_news_feeds(self, location_data: Dict) -> List[str]:
        """Get local news RSS feeds based on location"""
        feeds = []
        
        # This would be enhanced with a comprehensive database
        # of local news sources by geographic area
        
        # Example feeds (would be location-specific)
        feeds.extend([
            'https://feeds.nbcnews.com/nbcnews/public/news',
            'https://feeds.abcnews.com/abcnews/topstories',
            'https://feeds.cnn.com/rss/edition.rss'
        ])
        
        return feeds
    
    def get_emergency_scanner_data(self, lat: float, lon: float) -> List[EmergencyFeed]:
        """Get emergency scanner feed data (simulated)"""
        # This would integrate with real scanner APIs like:
        # - Broadcastify API
        # - Scanner Radio APIs
        # - Local dispatch systems
        
        feeds = [
            EmergencyFeed(
                feed_type='police',
                frequency='154.755',
                description='Local Police Dispatch',
                location=f"Area near {lat:.2f}, {lon:.2f}",
                activity_level='medium',
                recent_calls=[
                    {'type': 'Traffic Stop', 'timestamp': datetime.now().isoformat(), 'description': 'Vehicle stop on Main St'},
                    {'type': 'Welfare Check', 'timestamp': datetime.now().isoformat(), 'description': 'Check on resident'}
                ]
            )
        ]
        
        return feeds
    
    def check_nearby_tfrs(self, lat: float, lon: float) -> List[Dict]:
        """Check for nearby Temporary Flight Restrictions"""
        # This would integrate with FAA TFR APIs
        # For now, return empty list
        return []
    
    def deduplicate_and_rank_stories(self, stories: List[NewsStory], search_terms: List[str]) -> List[NewsStory]:
        """Remove duplicates and rank stories by relevance"""
        # Remove duplicates based on title similarity
        unique_stories = []
        seen_titles = set()
        
        for story in stories:
            title_key = story.title.lower()[:50]  # First 50 chars
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_stories.append(story)
        
        # Sort by relevance score (descending)
        unique_stories.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return unique_stories
    
    def search_local_news_rss(self, search_terms: List[str], location_data: Dict) -> List[NewsStory]:
        """Search local news RSS feeds"""
        # Placeholder for local news RSS feed search
        return []
    
    def search_google_news_enhanced(self, search_terms: List[str]) -> List[NewsStory]:
        """Enhanced Google News search"""
        stories = []
        try:
            # Use Google News RSS
            query = "+".join([urllib.parse.quote(term) for term in search_terms[:3] if term])
            url = f"https://news.google.com/rss/search?q={query}"
            
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                story = NewsStory(
                    title=entry.title,
                    url=entry.link,
                    source="Google News",
                    published=entry.published,
                    description=entry.summary,
                    relevance_score=0.5,
                    story_type='news',
                    location_match=True,
                    keywords=search_terms
                )
                stories.append(story)
        except Exception as e:
            logging.error(f"Google News RSS error: {e}")
        
        return stories
    
    def search_emergency_feeds(self, lat: float, lon: float, location_data: Dict) -> List[NewsStory]:
        """Search emergency scanner feeds"""
        # Placeholder for emergency feed search
        return []
    
    def search_aviation_feeds(self, lat: float, lon: float) -> List[NewsStory]:
        """Search aviation-specific feeds"""
        # Placeholder for aviation feed search
        return []
    
    def deduplicate_and_rank_stories(self, stories: List[NewsStory], search_terms: List[str]) -> List[NewsStory]:
        """Remove duplicates and rank stories by relevance"""
        # Simple deduplication by URL
        seen_urls = set()
        unique_stories = []
        
        for story in stories:
            if story.url not in seen_urls:
                seen_urls.add(story.url)
                unique_stories.append(story)
        
        # Sort by relevance score
        unique_stories.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return unique_stories
    
    def calculate_reddit_relevance(self, post_data: Dict, search_terms: List[str]) -> float:
        """Calculate Reddit post relevance"""
        score = 0.0
        
        title = post_data.get('title', '').lower()
        
        # Search term matches
        for term in search_terms:
            if term.lower() in title:
                score += 0.3
        
        # Emergency keywords
        emergency_words = ['emergency', 'breaking', 'incident', 'crash', 'fire', 'police']
        for word in emergency_words:
            if word in title:
                score += 0.4
        
        # Upvote bonus
        upvotes = post_data.get('ups', 0)
        if upvotes > 50:
            score += 0.2
        elif upvotes > 10:
            score += 0.1
        
        return min(score, 1.0)

def main():
    """Test enhanced intelligence sources"""
    intel = EnhancedIntelligenceSources()
    
    # Test location
    test_lat, test_lon = 37.7749, -122.4194  # San Francisco
    
    print("Testing enhanced location intelligence...")
    location_data = intel.get_comprehensive_location_intelligence(test_lat, test_lon)
    print(f"Location: {location_data}")
    
    print("\nTesting enhanced news intelligence...")
    news_stories = intel.get_comprehensive_news_intelligence(test_lat, test_lon, location_data)
    for story in news_stories[:3]:
        print(f"- {story.title} ({story.source}) - Score: {story.relevance_score}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()