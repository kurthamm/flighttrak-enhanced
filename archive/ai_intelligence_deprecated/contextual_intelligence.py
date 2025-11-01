#!/usr/bin/env python3
"""
Contextual Intelligence Module for FlightTrak AI
Integrates external data sources to enhance event detection accuracy
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3
import feedparser
import re
from dataclasses import dataclass

@dataclass
class ContextualData:
    """Structured contextual information"""
    source: str
    data_type: str
    content: str
    timestamp: float
    relevance_score: float
    location: Optional[Tuple[float, float]]
    keywords: List[str]

class ContextualIntelligence:
    """Gathers and analyzes contextual data to enhance AI event detection"""
    
    def __init__(self, home_lat: float, home_lon: float):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.context_cache = {}
        self.init_context_db()
        
        # Emergency services keywords
        self.emergency_keywords = [
            'crash', 'accident', 'emergency', 'rescue', 'search', 'missing',
            'fire', 'explosion', 'derailment', 'collision', 'incident',
            'evacuation', 'manhunt', 'pursuit', 'lockdown', 'shooting',
            'hazmat', 'spill', 'leak', 'tornado', 'hurricane', 'flood'
        ]
        
        # Law enforcement keywords
        self.law_enforcement_keywords = [
            'police', 'sheriff', 'state trooper', 'fbi', 'dea', 'atf',
            'arrest', 'suspect', 'chase', 'raid', 'operation', 'investigation',
            'surveillance', 'warrant', 'swat', 'tactical'
        ]
        
        # Military keywords
        self.military_keywords = [
            'military', 'air force', 'navy', 'army', 'marines', 'exercise',
            'training', 'drill', 'deployment', 'mission', 'operation',
            'fighter', 'bomber', 'transport', 'refueling'
        ]
        
        logging.info("Contextual Intelligence system initialized")
    
    def init_context_db(self):
        """Initialize database for contextual data storage"""
        self.db_path = 'contextual_intelligence.db'
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contextual_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                data_type TEXT,
                content TEXT,
                timestamp REAL,
                relevance_score REAL,
                lat REAL,
                lon REAL,
                keywords TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS weather_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                severity TEXT,
                description TEXT,
                start_time REAL,
                end_time REAL,
                lat REAL,
                lon REAL,
                radius_miles REAL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aviation_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notice_type TEXT,
                title TEXT,
                description TEXT,
                start_time REAL,
                end_time REAL,
                lat REAL,
                lon REAL,
                altitude_min INTEGER,
                altitude_max INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles"""
        import math
        R = 3959  # Earth radius in miles
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 2 * R * math.asin(math.sqrt(a))
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        text_lower = text.lower()
        found_keywords = []
        
        all_keywords = (self.emergency_keywords + 
                       self.law_enforcement_keywords + 
                       self.military_keywords)
        
        for keyword in all_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def calculate_relevance_score(self, content: str, location: Optional[Tuple[float, float]] = None) -> float:
        """Calculate relevance score for contextual data"""
        score = 0.0
        
        # Keyword relevance
        keywords = self.extract_keywords(content)
        score += len(keywords) * 0.2
        
        # Location relevance
        if location:
            distance = self.haversine_distance(
                self.home_lat, self.home_lon, location[0], location[1]
            )
            if distance < 10:  # Very close
                score += 1.0
            elif distance < 25:  # Close
                score += 0.7
            elif distance < 50:  # Nearby
                score += 0.4
            elif distance < 100:  # Regional
                score += 0.2
        
        # Time relevance (recent is more relevant)
        # This would be calculated based on when the content was published
        
        # Content type relevance
        content_lower = content.lower()
        if any(word in content_lower for word in ['breaking', 'urgent', 'alert']):
            score += 0.5
        
        return min(score, 1.0)  # Cap at 1.0
    
    def fetch_news_feeds(self) -> List[ContextualData]:
        """Fetch relevant news from RSS feeds"""
        contextual_data = []
        
        # Local news feeds for Charlotte, NC area
        news_feeds = [
            'http://feeds.feedburner.com/charlotte-observer',
            'https://www.wsoctv.com/news/local/rss/',
            'https://www.wcnc.com/rss',
            'https://www.wbtv.com/rss/',
        ]
        
        for feed_url in news_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # Latest 10 entries
                    content = f"{entry.title} {getattr(entry, 'summary', '')}"
                    keywords = self.extract_keywords(content)
                    
                    if keywords:  # Only include if relevant keywords found
                        published_time = time.time()
                        try:
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                published_time = time.mktime(entry.published_parsed)
                        except:
                            pass
                        
                        relevance = self.calculate_relevance_score(content)
                        
                        if relevance > 0.3:  # Only include relevant content
                            contextual_data.append(ContextualData(
                                source=feed_url,
                                data_type='news',
                                content=content,
                                timestamp=published_time,
                                relevance_score=relevance,
                                location=None,  # Could be extracted from content
                                keywords=keywords
                            ))
                            
            except Exception as e:
                logging.warning(f"Error fetching news feed {feed_url}: {e}")
        
        return contextual_data
    
    def fetch_weather_alerts(self) -> List[ContextualData]:
        """Fetch weather alerts that might affect aviation"""
        contextual_data = []
        
        # National Weather Service API for alerts
        try:
            # Get alerts for North Carolina
            url = "https://api.weather.gov/alerts/active?area=NC"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            alerts = response.json()
            
            for alert in alerts.get('features', []):
                properties = alert.get('properties', {})
                alert_type = properties.get('event', '')
                severity = properties.get('severity', '')
                description = properties.get('description', '')
                
                # Check if weather alert might affect aviation
                aviation_relevant = any(word in alert_type.lower() for word in 
                                      ['tornado', 'thunderstorm', 'wind', 'fog', 'ice', 'snow'])
                
                if aviation_relevant:
                    content = f"Weather Alert: {alert_type} - {description}"
                    relevance = self.calculate_relevance_score(content)
                    
                    contextual_data.append(ContextualData(
                        source='weather.gov',
                        data_type='weather_alert',
                        content=content,
                        timestamp=time.time(),
                        relevance_score=relevance,
                        location=None,  # Could extract coordinates
                        keywords=[alert_type.lower(), severity.lower()]
                    ))
                    
        except Exception as e:
            logging.warning(f"Error fetching weather alerts: {e}")
        
        return contextual_data
    
    def fetch_aviation_notices(self) -> List[ContextualData]:
        """Fetch NOTAMs and other aviation notices"""
        contextual_data = []
        
        # This would integrate with FAA NOTAM system
        # For now, we'll create a placeholder structure
        
        try:
            # Simulated NOTAM data - in reality would fetch from FAA
            sample_notams = [
                {
                    'type': 'Temporary Flight Restriction',
                    'description': 'TFR for VIP movement',
                    'location': (35.0, -81.0),
                    'altitude_range': (0, 18000),
                    'start_time': time.time(),
                    'end_time': time.time() + 3600
                }
            ]
            
            for notam in sample_notams:
                content = f"NOTAM: {notam['type']} - {notam['description']}"
                relevance = self.calculate_relevance_score(content, notam['location'])
                
                contextual_data.append(ContextualData(
                    source='faa_notam',
                    data_type='aviation_notice',
                    content=content,
                    timestamp=time.time(),
                    relevance_score=relevance,
                    location=notam['location'],
                    keywords=['notam', notam['type'].lower()]
                ))
                
        except Exception as e:
            logging.warning(f"Error fetching aviation notices: {e}")
        
        return contextual_data
    
    def fetch_emergency_scanner_data(self) -> List[ContextualData]:
        """Fetch police/fire scanner data if available"""
        contextual_data = []
        
        # This would integrate with services like Broadcastify or local scanner feeds
        # For now, implementing a placeholder structure
        
        try:
            # Simulated scanner data - in reality would process audio feeds
            scanner_keywords = ['aircraft down', 'helicopter request', 'search and rescue', 
                              'multiple units', 'major incident', 'all units']
            
            # This is where real scanner integration would go
            
        except Exception as e:
            logging.warning(f"Error fetching scanner data: {e}")
        
        return contextual_data
    
    def analyze_social_media_trends(self) -> List[ContextualData]:
        """Analyze social media for aviation-related incidents"""
        contextual_data = []
        
        # This would integrate with Twitter API, Reddit, etc.
        # Looking for aviation-related trending topics
        
        try:
            # Placeholder for social media integration
            # Would search for terms like "helicopter", "aircraft", "emergency" with location
            pass
            
        except Exception as e:
            logging.warning(f"Error analyzing social media: {e}")
        
        return contextual_data
    
    def store_contextual_data(self, data: List[ContextualData]):
        """Store contextual data in database"""
        conn = sqlite3.connect(self.db_path)
        
        for item in data:
            lat, lon = item.location if item.location else (None, None)
            keywords_json = json.dumps(item.keywords)
            
            conn.execute('''
                INSERT INTO contextual_data (source, data_type, content, timestamp, 
                                           relevance_score, lat, lon, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.source, item.data_type, item.content, item.timestamp,
                item.relevance_score, lat, lon, keywords_json
            ))
        
        conn.commit()
        conn.close()
    
    def get_contextual_analysis(self, event_location: Tuple[float, float], 
                               event_time: float, radius_miles: float = 25) -> Dict:
        """Get contextual analysis for a specific event"""
        
        conn = sqlite3.connect(self.db_path)
        
        # Get recent contextual data near the event location
        recent_cutoff = event_time - 3600  # Last hour
        
        query = '''
            SELECT * FROM contextual_data 
            WHERE timestamp > ? AND relevance_score > 0.4
            ORDER BY relevance_score DESC, timestamp DESC
            LIMIT 20
        '''
        
        cursor = conn.execute(query, (recent_cutoff,))
        contextual_items = cursor.fetchall()
        
        analysis = {
            'relevant_news': [],
            'weather_factors': [],
            'aviation_notices': [],
            'context_score': 0.0,
            'explanatory_factors': []
        }
        
        for item in contextual_items:
            _, source, data_type, content, timestamp, relevance, lat, lon, keywords_json = item
            
            # Check location relevance if coordinates available
            if lat and lon:
                distance = self.haversine_distance(
                    event_location[0], event_location[1], lat, lon
                )
                if distance > radius_miles:
                    continue
            
            keywords = json.loads(keywords_json)
            
            if data_type == 'news':
                analysis['relevant_news'].append({
                    'content': content,
                    'relevance': relevance,
                    'keywords': keywords,
                    'timestamp': timestamp
                })
            elif data_type == 'weather_alert':
                analysis['weather_factors'].append({
                    'content': content,
                    'relevance': relevance,
                    'timestamp': timestamp
                })
            elif data_type == 'aviation_notice':
                analysis['aviation_notices'].append({
                    'content': content,
                    'relevance': relevance,
                    'timestamp': timestamp
                })
            
            analysis['context_score'] += relevance
        
        # Generate explanatory factors
        if analysis['relevant_news']:
            analysis['explanatory_factors'].append(
                f"Recent news activity in area ({len(analysis['relevant_news'])} items)"
            )
        
        if analysis['weather_factors']:
            analysis['explanatory_factors'].append(
                f"Active weather alerts ({len(analysis['weather_factors'])} alerts)"
            )
        
        if analysis['aviation_notices']:
            analysis['explanatory_factors'].append(
                f"Aviation notices in effect ({len(analysis['aviation_notices'])} notices)"
            )
        
        conn.close()
        return analysis
    
    def enhance_event_intelligence(self, event_data: Dict) -> Dict:
        """Enhance event intelligence with contextual data"""
        
        event_location = event_data.get('location', (self.home_lat, self.home_lon))
        event_time = event_data.get('timestamp', time.time())
        
        # Get contextual analysis
        context = self.get_contextual_analysis(event_location, event_time)
        
        # Enhance the event description
        enhanced_event = event_data.copy()
        enhanced_event['contextual_analysis'] = context
        
        # Adjust confidence based on context
        base_confidence = event_data.get('confidence', 0.5)
        context_boost = min(context['context_score'] * 0.1, 0.3)  # Max 30% boost
        enhanced_event['enhanced_confidence'] = min(base_confidence + context_boost, 1.0)
        
        # Add context to narrative
        if context['explanatory_factors']:
            context_narrative = "\n\n🔍 CONTEXTUAL FACTORS:\n"
            for factor in context['explanatory_factors']:
                context_narrative += f"• {factor}\n"
            
            enhanced_event['enhanced_narrative'] = (
                enhanced_event.get('narrative', '') + context_narrative
            )
        
        return enhanced_event
    
    def continuous_context_gathering(self, interval: int = 300):
        """Continuously gather contextual data"""
        logging.info("Starting continuous contextual data gathering...")
        
        while True:
            try:
                all_context_data = []
                
                # Gather from all sources
                all_context_data.extend(self.fetch_news_feeds())
                all_context_data.extend(self.fetch_weather_alerts())
                all_context_data.extend(self.fetch_aviation_notices())
                
                # Store in database
                if all_context_data:
                    self.store_contextual_data(all_context_data)
                    logging.info(f"Gathered {len(all_context_data)} contextual data items")
                
                time.sleep(interval)  # Default: every 5 minutes
                
            except Exception as e:
                logging.error(f"Error in contextual data gathering: {e}")
                time.sleep(60)  # Wait 1 minute on error

def main():
    """Test the contextual intelligence system"""
    context_intel = ContextualIntelligence(34.1133171, -80.9024019)
    
    # Test context gathering
    news_data = context_intel.fetch_news_feeds()
    weather_data = context_intel.fetch_weather_alerts()
    
    print(f"Found {len(news_data)} relevant news items")
    print(f"Found {len(weather_data)} weather alerts")
    
    if news_data:
        context_intel.store_contextual_data(news_data)
    if weather_data:
        context_intel.store_contextual_data(weather_data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()