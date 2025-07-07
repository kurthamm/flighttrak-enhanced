#!/usr/bin/env python3
"""
AI-Powered Event Intelligence System for FlightTrak
Advanced pattern recognition and event detection using machine learning
"""

import json
import time
import requests
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import logging
import math
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import threading
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import pickle
import os

try:
    from geographic_intelligence import GeographicIntelligence
    GEO_INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Geographic intelligence not available: {e}")
    GEO_INTELLIGENCE_AVAILABLE = False

try:
    from enhanced_intelligence_sources import EnhancedIntelligenceSources
    from intelligence_config import IntelligenceConfig
    ENHANCED_INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced intelligence not available: {e}")
    ENHANCED_INTELLIGENCE_AVAILABLE = False

@dataclass
class EventIntelligence:
    """Structured event intelligence report"""
    event_id: str
    timestamp: float
    event_type: str
    severity: str
    confidence: float
    location: Tuple[float, float]
    description: str
    narrative: str
    aircraft_involved: List[str]
    pattern_signature: Dict
    context_data: Dict
    predicted_duration: Optional[int]
    historical_matches: List[str]
    location_intelligence: Optional[Dict] = None
    news_stories: Optional[List[Dict]] = None

class AIEventDetector:
    """Advanced AI-powered event detection system"""
    
    def __init__(self, home_lat: float, home_lon: float, config: dict):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.config = config
        
        # Initialize Claude AI enhancement if API key available
        self.claude_enhancer = None
        if config.get('claude_api_key'):
            try:
                from claude_intelligence_enhancement import ClaudeIntelligenceEnhancer
                self.claude_enhancer = ClaudeIntelligenceEnhancer(config['claude_api_key'])
                logging.info("Claude AI enhancement enabled")
            except ImportError as e:
                logging.warning(f"Claude enhancement not available: {e}")
            except Exception as e:
                logging.error(f"Failed to initialize Claude enhancement: {e}")
        else:
            logging.info("No Claude API key provided - using basic narrative generation")
        
        # Initialize Geographic Intelligence
        self.geo_intelligence = None
        self.enhanced_intelligence = None
        self.intelligence_config = None
        
        if GEO_INTELLIGENCE_AVAILABLE:
            try:
                self.geo_intelligence = GeographicIntelligence()
                logging.info("Geographic Intelligence system enabled")
            except Exception as e:
                logging.error(f"Failed to initialize Geographic Intelligence: {e}")
        else:
            logging.info("Geographic Intelligence not available")
        
        # Initialize Enhanced Intelligence Sources
        if ENHANCED_INTELLIGENCE_AVAILABLE:
            try:
                self.intelligence_config = IntelligenceConfig()
                self.enhanced_intelligence = EnhancedIntelligenceSources()
                
                # Log available services
                services = self.intelligence_config.get_available_services()
                active_services = [name for name, active in services.items() if active]
                logging.info(f"Enhanced Intelligence enabled with {len(active_services)} services: {', '.join(active_services)}")
                
            except Exception as e:
                logging.error(f"Failed to initialize Enhanced Intelligence: {e}")
        else:
            logging.info("Enhanced Intelligence not available")
        
        # Aircraft tracking
        self.aircraft_tracks = defaultdict(lambda: {
            'positions': deque(maxlen=100),
            'altitudes': deque(maxlen=50),
            'speeds': deque(maxlen=50),
            'headings': deque(maxlen=50),
            'first_seen': None,
            'last_seen': None,
            'aircraft_type': None,
            'operator': None,
            'patterns': []
        })
        
        # Event detection
        self.active_events = {}
        self.event_history = deque(maxlen=1000)
        self.pattern_library = {}
        
        # AI Models
        self.clustering_model = DBSCAN(eps=0.02, min_samples=3)  # For spatial clustering
        self.scaler = StandardScaler()
        
        # Intelligence database
        self.init_intelligence_db()
        
        # Pattern signatures for known events
        self.load_pattern_signatures()
        
        # Known news aircraft patterns (common tail numbers/operators for news helicopters)
        self.news_aircraft_indicators = {
            'operators': ['KTVU', 'KPIX', 'KGO', 'ABC7', 'NBC Bay Area', 'CBS', 'ABC', 'NBC', 'FOX', 'CNN'],
            'common_types': ['AS350', 'MD500', 'R44', 'Bell 206', 'Eurocopter'],
            'typical_patterns': ['orbiting', 'loitering', 'circling'],
            'altitude_preference': (800, 2000),  # Typical news helicopter altitude
            'speed_preference': (50, 100)  # Slower speeds for stable shots
        }
        
        logging.info("AI Event Intelligence System initialized")
    
    def init_intelligence_db(self):
        """Initialize SQLite database for intelligence storage"""
        self.db_path = 'intelligence.db'
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                timestamp REAL,
                event_type TEXT,
                severity TEXT,
                confidence REAL,
                lat REAL,
                lon REAL,
                description TEXT,
                narrative TEXT,
                aircraft_count INTEGER,
                pattern_data TEXT,
                context_data TEXT,
                location_intelligence TEXT,
                news_stories TEXT,
                outcome TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aircraft_intelligence (
                hex_code TEXT,
                timestamp REAL,
                registration TEXT,
                aircraft_type TEXT,
                operator TEXT,
                mission_type TEXT,
                behavior_score REAL,
                PRIMARY KEY (hex_code, timestamp)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pattern_learning (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                signature_data TEXT,
                confidence_score REAL,
                success_rate REAL,
                false_positive_rate REAL,
                last_updated REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Intelligence database initialized")
    
    def load_pattern_signatures(self):
        """Load known event pattern signatures"""
        self.pattern_signatures = {
            'search_rescue': {
                'aircraft_types': ['helicopter', 'light_aircraft'],
                'min_aircraft': 3,
                'pattern_type': 'converging_search',
                'altitude_range': (500, 3000),
                'speed_range': (40, 120),
                'duration_min': 30
            },
            'law_enforcement': {
                'aircraft_types': ['helicopter', 'surveillance'],
                'min_aircraft': 2,
                'pattern_type': 'pursuit_following',
                'altitude_range': (500, 2000),
                'speed_range': (20, 150),
                'duration_min': 15
            },
            'emergency_medical': {
                'aircraft_types': ['medical_helicopter'],
                'min_aircraft': 1,
                'pattern_type': 'point_to_point_shuttle',
                'altitude_range': (200, 2500),
                'speed_range': (80, 180),
                'duration_min': 10
            },
            'military_exercise': {
                'aircraft_types': ['military', 'fighter', 'transport'],
                'min_aircraft': 4,
                'pattern_type': 'formation_training',
                'altitude_range': (1000, 40000),
                'speed_range': (200, 800),
                'duration_min': 60
            },
            'vip_protection': {
                'aircraft_types': ['helicopter', 'government', 'fighter'],
                'min_aircraft': 2,
                'pattern_type': 'escort_formation',
                'altitude_range': (1000, 25000),
                'speed_range': (150, 600),
                'duration_min': 20
            },
            'wildfire_response': {
                'aircraft_types': ['helicopter', 'tanker', 'surveillance'],
                'min_aircraft': 3,
                'pattern_type': 'water_bombing_circuit',
                'altitude_range': (200, 5000),
                'speed_range': (60, 200),
                'duration_min': 120
            },
            'news_media_response': {
                'aircraft_types': ['helicopter', 'light_aircraft'],
                'min_aircraft': 2,
                'pattern_type': 'news_coverage_orbit',
                'altitude_range': (500, 3000),
                'speed_range': (40, 120),
                'duration_min': 15
            }
        }
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles"""
        R = 3959  # Earth radius in miles
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return 2 * R * math.asin(math.sqrt(a))
    
    def extract_aircraft_features(self, aircraft: dict) -> np.ndarray:
        """Extract feature vector from aircraft data for ML analysis"""
        features = []
        
        # Basic flight parameters
        features.extend([
            aircraft.get('lat', 0),
            aircraft.get('lon', 0),
            aircraft.get('alt_baro', 0) / 1000,  # Normalize altitude
            aircraft.get('gs', 0) / 100,  # Normalize ground speed
            aircraft.get('track', 0) / 360,  # Normalize heading
            aircraft.get('baro_rate', 0) / 1000  # Normalize climb rate
        ])
        
        # Distance from home
        if aircraft.get('lat') and aircraft.get('lon'):
            distance = self.haversine_distance(
                self.home_lat, self.home_lon,
                aircraft['lat'], aircraft['lon']
            )
            features.append(distance / 100)  # Normalize distance
        else:
            features.append(0)
        
        # Time-based features
        hour = datetime.now().hour
        features.extend([
            hour / 24,  # Hour of day normalized
            int(datetime.now().weekday() < 5),  # Weekday vs weekend
        ])
        
        return np.array(features)
    
    def detect_spatial_clusters(self, aircraft_list: List[dict]) -> List[List[dict]]:
        """Use DBSCAN to find spatial clusters of aircraft"""
        if len(aircraft_list) < 3:
            return []
        
        # Extract positions
        positions = []
        valid_aircraft = []
        
        for aircraft in aircraft_list:
            if aircraft.get('lat') and aircraft.get('lon'):
                positions.append([aircraft['lat'], aircraft['lon']])
                valid_aircraft.append(aircraft)
        
        if len(positions) < 3:
            return []
        
        # Cluster aircraft by position
        positions_array = np.array(positions)
        clusters = self.clustering_model.fit_predict(positions_array)
        
        # Group aircraft by cluster
        clustered_aircraft = defaultdict(list)
        for i, cluster_id in enumerate(clusters):
            if cluster_id != -1:  # Ignore noise points
                clustered_aircraft[cluster_id].append(valid_aircraft[i])
        
        # Return clusters with at least 3 aircraft
        return [aircraft_group for aircraft_group in clustered_aircraft.values() 
                if len(aircraft_group) >= 3]
    
    def analyze_movement_patterns(self, aircraft_group: List[dict]) -> Dict:
        """Analyze movement patterns within a group of aircraft"""
        if len(aircraft_group) < 2:
            return {}
        
        patterns = {
            'cluster_center': None,
            'spread_radius': 0,
            'avg_altitude': 0,
            'avg_speed': 0,
            'heading_variance': 0,
            'formation_type': 'scattered'
        }
        
        # Calculate cluster center
        lats = [a['lat'] for a in aircraft_group if a.get('lat')]
        lons = [a['lon'] for a in aircraft_group if a.get('lon')]
        
        if lats and lons:
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            patterns['cluster_center'] = (center_lat, center_lon)
            
            # Calculate spread radius
            distances = [self.haversine_distance(center_lat, center_lon, lat, lon) 
                        for lat, lon in zip(lats, lons)]
            patterns['spread_radius'] = max(distances) if distances else 0
        
        # Calculate averages
        altitudes = [a.get('alt_baro', 0) for a in aircraft_group]
        speeds = [a.get('gs', 0) for a in aircraft_group]
        headings = [a.get('track', 0) for a in aircraft_group if a.get('track')]
        
        patterns['avg_altitude'] = sum(altitudes) / len(altitudes) if altitudes else 0
        patterns['avg_speed'] = sum(speeds) / len(speeds) if speeds else 0
        
        # Analyze heading variance
        if headings:
            heading_variance = np.var(headings)
            patterns['heading_variance'] = heading_variance
            
            # Determine formation type
            if heading_variance < 100:  # Similar headings
                if patterns['spread_radius'] < 2:  # Close together
                    patterns['formation_type'] = 'tight_formation'
                else:
                    patterns['formation_type'] = 'loose_formation'
            elif patterns['spread_radius'] < 5:  # Close but different headings
                patterns['formation_type'] = 'search_pattern'
            else:
                patterns['formation_type'] = 'converging'
        
        return patterns
    
    def classify_event_type(self, aircraft_group: List[dict], patterns: Dict) -> Tuple[str, float]:
        """Use AI to classify the type of event based on aircraft and patterns"""
        
        # Extract aircraft types and operators
        aircraft_types = []
        operators = []
        
        for aircraft in aircraft_group:
            # This would integrate with your aircraft lookup system
            aircraft_type = aircraft.get('aircraft_type', 'unknown')
            operator = aircraft.get('operator', 'unknown')
            aircraft_types.append(aircraft_type)
            operators.append(operator)
        
        best_match = None
        best_confidence = 0
        
        # Match against known patterns
        for event_type, signature in self.pattern_signatures.items():
            confidence = self.calculate_pattern_match(
                aircraft_group, patterns, signature
            )
            
            # Boost confidence for news aircraft if we detect news indicators
            if event_type == 'news_media_response':
                news_confidence = self.detect_news_aircraft_indicators(aircraft_group)
                confidence = max(confidence, news_confidence)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = event_type
        
        return best_match or 'unknown_activity', best_confidence
    
    def calculate_pattern_match(self, aircraft_group: List[dict], 
                               patterns: Dict, signature: Dict) -> float:
        """Calculate how well observed patterns match a known signature"""
        score = 0.0
        max_score = 6.0  # Maximum possible score
        
        # Check aircraft count
        if len(aircraft_group) >= signature.get('min_aircraft', 1):
            score += 1.0
        
        # Check altitude range
        avg_alt = patterns.get('avg_altitude', 0)
        alt_min, alt_max = signature.get('altitude_range', (0, 50000))
        if alt_min <= avg_alt <= alt_max:
            score += 1.0
        
        # Check speed range
        avg_speed = patterns.get('avg_speed', 0)
        speed_min, speed_max = signature.get('speed_range', (0, 1000))
        if speed_min <= avg_speed <= speed_max:
            score += 1.0
        
        # Check formation type
        formation = patterns.get('formation_type', '')
        if signature.get('pattern_type', '') in formation:
            score += 1.0
        
        # Check spread radius
        spread = patterns.get('spread_radius', 0)
        if spread < 10:  # Reasonable clustering
            score += 1.0
        
        # Time of day factor
        hour = datetime.now().hour
        if event_type == 'search_rescue' and (hour < 6 or hour > 20):
            score += 0.5  # More likely during off hours
        elif event_type == 'military_exercise' and 8 <= hour <= 17:
            score += 0.5  # More likely during business hours
        elif event_type == 'news_media_response' and 6 <= hour <= 22:
            score += 0.5  # News coverage during daytime/evening hours
        
        # News-specific pattern detection
        if event_type == 'news_media_response':
            # Check for orbital/circling patterns typical of news helicopters
            if formation == 'search_pattern' or 'circling' in formation:
                score += 0.5
            # Multiple aircraft hovering in area suggests major story
            if len(aircraft_group) >= 2 and spread < 3:
                score += 0.5
        
        return min(score / max_score, 1.0)
    
    def detect_news_aircraft_indicators(self, aircraft_group: List[dict]) -> float:
        """Detect likelihood that this is news aircraft coverage"""
        news_score = 0.0
        
        for aircraft in aircraft_group:
            # Check for news-related callsigns or registrations
            flight = aircraft.get('flight', '').upper()
            if any(news_org in flight for news_org in ['NEWS', 'KTVU', 'ABC', 'CBS', 'NBC', 'FOX', 'CNN']):
                news_score += 0.3
            
            # Check altitude (news helicopters often fly at specific altitudes)
            alt = aircraft.get('alt_baro', 0)
            if 800 <= alt <= 2000:
                news_score += 0.2
            
            # Check speed (news helicopters often fly slower for stable shots)
            speed = aircraft.get('gs', 0)
            if 50 <= speed <= 100:
                news_score += 0.2
        
        # Normalize by aircraft count
        if len(aircraft_group) > 0:
            news_score = news_score / len(aircraft_group)
        
        return min(news_score, 1.0)
    
    def generate_event_narrative(self, event_intel: EventIntelligence) -> str:
        """Generate natural language narrative for the event"""
        aircraft_count = len(event_intel.aircraft_involved)
        
        # Use location intelligence for better description
        if event_intel.location_intelligence:
            location_desc = event_intel.location_intelligence.get('location_description', 
                                f"near {event_intel.location[0]:.3f}, {event_intel.location[1]:.3f}")
            place_type = event_intel.location_intelligence.get('place_type', 'unknown')
            
            # Enhance location description with context
            if place_type in ['hospital', 'medical']:
                location_desc += " (medical facility area)"
            elif place_type in ['airport', 'aeroway']:
                location_desc += " (aviation facility)"
            elif place_type in ['industrial_area', 'industrial']:
                location_desc += " (industrial zone)"
            elif place_type in ['school', 'university']:
                location_desc += " (educational institution)"
        else:
            location_desc = f"near {event_intel.location[0]:.3f}, {event_intel.location[1]:.3f}"
        
        narratives = {
            'search_rescue': f"""
🚁 SEARCH & RESCUE OPERATION DETECTED
{aircraft_count} aircraft converging on rural area {location_desc}. Pattern analysis indicates coordinated search operation, likely for missing person(s) or downed aircraft. 

Aircraft deployment suggests serious situation requiring multi-agency response. Expect operation duration of 2-6 hours based on historical patterns.

Intelligence Assessment: High-priority emergency response in progress.
            """.strip(),
            
            'law_enforcement': f"""
🚔 LAW ENFORCEMENT OPERATION DETECTED  
{aircraft_count} aircraft exhibiting pursuit/surveillance patterns {location_desc}. Coordinated air support suggests active law enforcement operation - possible manhunt, drug interdiction, or high-risk arrest.

Flight patterns indicate ground units being supported from air. Operation appears tactical in nature.

Intelligence Assessment: Active law enforcement engagement.
            """.strip(),
            
            'emergency_medical': f"""
🚑 MAJOR MEDICAL EMERGENCY DETECTED
Medical helicopter(s) responding to {location_desc}. Flight pattern suggests mass casualty incident or critical patient transport requiring immediate air medical response.

Multiple aircraft deployment indicates serious situation requiring advanced medical intervention.

Intelligence Assessment: Critical medical emergency in progress.
            """.strip(),
            
            'military_exercise': f"""
✈️ MILITARY TRAINING EXERCISE DETECTED
{aircraft_count} military aircraft conducting coordinated operations {location_desc}. Formation patterns and aircraft types suggest planned training exercise or readiness demonstration.

Flight profiles consistent with air-to-air combat training or tactical maneuvering exercises.

Intelligence Assessment: Scheduled military training activity.
            """.strip(),
            
            'vip_protection': f"""
🛡️ VIP MOVEMENT DETECTED
{aircraft_count} aircraft in protective formation {location_desc}. Flight patterns indicate high-value individual transport with security escort.

Coordinated movement suggests dignitary, government official, or other protected person transit.

Intelligence Assessment: Secured VIP transportation in progress.
            """.strip(),
            
            'wildfire_response': f"""
🔥 WILDFIRE RESPONSE DETECTED
{aircraft_count} aircraft conducting firefighting operations {location_desc}. Flight patterns indicate active fire suppression with water bombers and command aircraft.

Sustained circuit patterns suggest significant fire requiring aerial intervention.

Intelligence Assessment: Active wildfire suppression operation.
            """.strip(),
            
            'news_media_response': f"""
📺 NEWS MEDIA COVERAGE DETECTED
{aircraft_count} news aircraft orbiting {location_desc}. Flight patterns indicate media helicopters covering breaking news event or significant story.

Sustained orbital patterns suggest ongoing newsworthy event requiring aerial coverage. Likely major incident, celebrity event, or developing story.

Intelligence Assessment: Active news media coverage operation.
            """.strip()
        }
        
        base_narrative = narratives.get(event_intel.event_type, f"""
🔍 UNUSUAL AIRCRAFT ACTIVITY DETECTED
{aircraft_count} aircraft exhibiting coordinated behavior {location_desc}. Pattern analysis suggests organized operation of unknown type.

Flight characteristics indicate purposeful activity requiring investigation.

Intelligence Assessment: Unclassified coordinated aircraft operation.
        """.strip())
        
        # Add confidence and timing information
        confidence_desc = "HIGH" if event_intel.confidence > 0.8 else "MEDIUM" if event_intel.confidence > 0.6 else "LOW"
        
        full_narrative = f"{base_narrative}\n\n"
        full_narrative += f"📊 CONFIDENCE LEVEL: {confidence_desc} ({event_intel.confidence:.2f})\n"
        full_narrative += f"⏰ DETECTED: {datetime.fromtimestamp(event_intel.timestamp).strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if event_intel.predicted_duration:
            full_narrative += f"⏱️ PREDICTED DURATION: {event_intel.predicted_duration} minutes\n"
        
        return full_narrative
    
    def send_intelligence_alert(self, event_intel: EventIntelligence):
        """Send AI-generated intelligence alert to Kurt with Claude enhancement"""
        email_cfg = self.config['email_config']
        
        # Use Claude AI for enhanced analysis if available
        if self.claude_enhancer:
            try:
                event_data = {
                    'event_type': event_intel.event_type,
                    'confidence': event_intel.confidence,
                    'severity': event_intel.severity,
                    'location': event_intel.location,
                    'timestamp': event_intel.timestamp,
                    'aircraft_involved': event_intel.aircraft_involved,
                    'pattern_signature': event_intel.pattern_signature,
                    'contextual_analysis': event_intel.context_data
                }
                
                # Get Claude's enhanced analysis
                claude_analysis = self.claude_enhancer.enhance_event_analysis(event_data)
                
                # Generate enhanced email with Claude's analysis
                html_content = self.claude_enhancer.generate_enhanced_alert_email(event_data, claude_analysis)
                
                # Update narrative with Claude's enhanced version
                event_intel.narrative = claude_analysis.narrative
                
            except Exception as e:
                logging.error(f"Claude enhancement failed, using fallback: {e}")
                html_content = self.generate_fallback_email(event_intel)
        else:
            # Use fallback email generation
            html_content = self.generate_fallback_email(event_intel)
        
        subject = f"🧠 FlightTrak AI Alert: {event_intel.event_type.replace('_', ' ').title()} [{event_intel.severity}]"
        if self.claude_enhancer:
            subject += " - Enhanced by Claude AI"
        
        message = Mail(
            from_email=email_cfg['sender'],
            to_emails='kurt@hamm.me',  # Your dedicated intelligence alerts
            subject=subject,
            html_content=html_content
        )
        
        try:
            sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
            resp = sg.send(message)
            logging.info(f"AI Intelligence alert sent: {event_intel.event_id} (status {resp.status_code})")
        except Exception as e:
            logging.error(f"Error sending AI intelligence alert: {e}")
    
    def generate_fallback_email(self, event_intel: EventIntelligence):
        """Generate fallback email when Claude is unavailable"""
        # Generate severity color
        severity_colors = {
            'CRITICAL': '#ff4757',
            'HIGH': '#ff6b6b',
            'MEDIUM': '#ffa502',
            'LOW': '#3742fa'
        }
        
        color = severity_colors.get(event_intel.severity, '#666')
        
        # Create rich HTML email (original format as fallback)
        html_content = f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
            <div style='max-width:800px;margin:0 auto;background:#1a1f3a;padding:25px;border-radius:12px;border:1px solid #2a3f5f;box-shadow:0 4px 6px rgba(0,0,0,0.3);'>
                
                <!-- Header -->
                <div style='text-align:center;margin-bottom:25px;padding-bottom:20px;border-bottom:2px solid #2a3f5f;'>
                    <h1 style='color:{color};margin:0;font-size:24px;'>🧠 FlightTrak AI Intelligence Alert</h1>
                    <h2 style='color:#4fc3f7;margin:10px 0;font-size:18px;'>{event_intel.event_type.replace('_', ' ').title()}</h2>
                    <p style='color:#feca57;font-size:14px;margin:5px 0;'>Event ID: {event_intel.event_id}</p>
                </div>
                
                <!-- AI Narrative -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>🤖 AI Analysis</h3>
                    <div style='white-space: pre-line; color:#e0e6ed; line-height: 1.6;'>{event_intel.narrative}</div>
                </div>
                
                {self.generate_location_intelligence_html(event_intel)}
                {self.generate_news_stories_html(event_intel)}
                
                <!-- Footer -->
                <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #2a3f5f;'>
                    <p style='font-size:12px;color:#8892b0;margin:5px 0;'>
                        FlightTrak AI Event Intelligence System
                    </p>
                </div>
            </div>
        </body></html>
        """
        
        return html_content
    
    def generate_location_intelligence_html(self, event_intel: EventIntelligence) -> str:
        """Generate HTML section for location intelligence"""
        if not event_intel.location_intelligence:
            return ""
        
        loc_intel = event_intel.location_intelligence
        
        # Risk color coding
        risk_colors = {
            'HIGH': '#ff4757',
            'MEDIUM': '#ffa502', 
            'LOW': '#3742fa'
        }
        risk_color = risk_colors.get(loc_intel.get('risk_assessment', 'LOW'), '#666')
        
        html = f"""
                <!-- Location Intelligence -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>📍 Location Intelligence</h3>
                    <div style='color:#e0e6ed;'>
                        <p><strong>Location:</strong> {loc_intel.get('location_description', 'Unknown')}</p>
                        <p><strong>Place Type:</strong> {loc_intel.get('place_type', 'Unknown').replace('_', ' ').title()}</p>
                        <p><strong>Risk Assessment:</strong> <span style='color:{risk_color};font-weight:bold;'>{loc_intel.get('risk_assessment', 'UNKNOWN')}</span></p>
        """
        
        # Add nearby landmarks if available
        landmarks = loc_intel.get('nearby_landmarks', [])
        if landmarks:
            html += f"""
                        <p><strong>Nearby Landmarks:</strong></p>
                        <ul style='margin:5px 0 0 20px;'>
            """
            for landmark in landmarks[:3]:  # Show top 3
                html += f"<li>{landmark}</li>"
            html += "</ul>"
        
        # Add What3Words if available
        what3words = loc_intel.get('what3words', '')
        if what3words:
            html += f"""
                        <p><strong>What3Words:</strong> <code style='background:#1a1f3a;padding:2px 4px;border-radius:3px;'>{what3words}</code></p>
            """
        
        # Add infrastructure info if available
        infrastructure = loc_intel.get('infrastructure', [])
        if infrastructure:
            html += f"""
                        <p><strong>Infrastructure:</strong> {', '.join(infrastructure[:3])}</p>
            """
        
        html += """
                    </div>
                </div>
        """
        
        return html
    
    def generate_news_stories_html(self, event_intel: EventIntelligence) -> str:
        """Generate HTML section for related news stories"""
        if not event_intel.news_stories:
            return ""
        
        html = """
                <!-- Related News -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>📰 Related News</h3>
                    <div style='color:#e0e6ed;'>
        """
        
        for story in event_intel.news_stories[:3]:  # Show top 3 stories
            # Story type emoji
            type_emoji = {
                'breaking': '🚨',
                'emergency': '🚑',
                'local': '📍',
                'aviation': '✈️',
                'incident': '⚠️'
            }.get(story.get('type', 'news'), '📰')
            
            relevance = story.get('relevance', 0)
            relevance_text = f"(Relevance: {relevance:.1f})" if relevance > 0 else ""
            
            html += f"""
                        <div style='margin:10px 0;padding:10px;background:#1a1f3a;border-radius:5px;border-left:3px solid #4fc3f7;'>
                            <p style='margin:0 0 5px 0;'><strong>{type_emoji} {story.get('title', 'News Story')}</strong></p>
                            <p style='margin:0;font-size:12px;color:#8892b0;'>
                                Source: {story.get('source', 'Unknown')} {relevance_text}<br>
                                <a href='{story.get('url', '#')}' style='color:#4fc3f7;text-decoration:none;'>🔗 Read Full Article</a>
                            </p>
                        </div>
            """
        
        html += """
                    </div>
                </div>
        """
        
        return html
    
    def store_event_intelligence(self, event_intel: EventIntelligence):
        """Store event in intelligence database for learning"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute('''
            INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_intel.event_id,
            event_intel.timestamp,
            event_intel.event_type,
            event_intel.severity,
            event_intel.confidence,
            event_intel.location[0],
            event_intel.location[1],
            event_intel.description,
            event_intel.narrative,
            len(event_intel.aircraft_involved),
            json.dumps(event_intel.pattern_signature),
            json.dumps(event_intel.context_data),
            json.dumps(event_intel.location_intelligence) if event_intel.location_intelligence else None,
            json.dumps(event_intel.news_stories) if event_intel.news_stories else None,
            None  # outcome - to be filled later
        ))
        
        conn.commit()
        conn.close()
    
    def analyze_aircraft_data(self, aircraft_data: List[dict]) -> List[EventIntelligence]:
        """Main AI analysis pipeline"""
        events_detected = []
        
        if len(aircraft_data) < 2:
            return events_detected
        
        # Step 1: Find spatial clusters
        clusters = self.detect_spatial_clusters(aircraft_data)
        
        # Step 2: Analyze each cluster
        for cluster in clusters:
            if len(cluster) < 3:  # Minimum aircraft for event
                continue
            
            # Analyze movement patterns
            patterns = self.analyze_movement_patterns(cluster)
            
            # Classify event type
            event_type, confidence = self.classify_event_type(cluster, patterns)
            
            # Only alert on high-confidence events
            if confidence < 0.6:
                continue
            
            # Determine severity
            severity = 'CRITICAL' if confidence > 0.9 else 'HIGH' if confidence > 0.8 else 'MEDIUM'
            
            # Get location intelligence
            location_intel = None
            news_stories = []
            cluster_location = patterns.get('cluster_center', (0, 0))
            
            if cluster_location != (0, 0):
                try:
                    # Try enhanced intelligence first, fallback to basic
                    if self.enhanced_intelligence:
                        # Get comprehensive location and news intelligence
                        comprehensive_location = self.enhanced_intelligence.get_comprehensive_location_intelligence(
                            cluster_location[0], cluster_location[1]
                        )
                        enhanced_news = self.enhanced_intelligence.get_comprehensive_news_intelligence(
                            cluster_location[0], cluster_location[1], comprehensive_location
                        )
                        
                        location_intel = {
                            'address': comprehensive_location.get('primary_address', 'Unknown'),
                            'place_type': ', '.join(comprehensive_location.get('place_types', ['unknown'])),
                            'location_description': comprehensive_location.get('detailed_address', {}).get('display_name', 'Unknown location'),
                            'nearby_landmarks': comprehensive_location.get('landmarks', []),
                            'risk_assessment': 'HIGH' if comprehensive_location.get('risk_factors') else 'MEDIUM',
                            'what3words': comprehensive_location.get('what3words', ''),
                            'infrastructure': comprehensive_location.get('infrastructure', [])
                        }
                        
                        # Convert enhanced news stories to basic format
                        news_stories = []
                        for story in enhanced_news[:5]:
                            news_stories.append({
                                'title': story.title,
                                'url': story.url,
                                'source': story.source,
                                'published': story.published,
                                'relevance': story.relevance_score,
                                'type': story.story_type
                            })
                        
                        logging.info(f"Enhanced intelligence gathered: {len(news_stories)} stories, {len(location_intel.get('landmarks', []))} landmarks")
                        
                    elif self.geo_intelligence:
                        # Fallback to basic geographic intelligence
                        location_analysis = self.geo_intelligence.analyze_location(
                            cluster_location[0], cluster_location[1]
                        )
                        location_intel = {
                            'address': location_analysis.address,
                            'place_type': location_analysis.place_type,
                            'location_description': location_analysis.location_description,
                            'nearby_landmarks': location_analysis.nearby_landmarks,
                            'risk_assessment': location_analysis.risk_assessment
                        }
                        news_stories = location_analysis.news_stories
                    
                    # Enhance confidence based on location risk
                    if location_intel and location_intel.get('risk_assessment') == 'HIGH':
                        confidence = min(confidence + 0.1, 1.0)
                    
                except Exception as e:
                    logging.error(f"Location analysis failed: {e}")
            
            # Create event intelligence
            event_intel = EventIntelligence(
                event_id=f"AI_{int(time.time())}_{len(cluster)}",
                timestamp=time.time(),
                event_type=event_type,
                severity=severity,
                confidence=confidence,
                location=cluster_location,
                description=f"{len(cluster)} aircraft in {event_type.replace('_', ' ')} pattern",
                narrative="",  # Will be filled by generate_event_narrative
                aircraft_involved=[a.get('hex', 'unknown') for a in cluster],
                pattern_signature=patterns,
                context_data={
                    'detection_time': datetime.now().isoformat(),
                    'cluster_size': len(cluster),
                    'analysis_confidence': confidence
                },
                predicted_duration=self.pattern_signatures.get(event_type, {}).get('duration_min'),
                historical_matches=[],
                location_intelligence=location_intel,
                news_stories=news_stories
            )
            
            # Generate narrative
            event_intel.narrative = self.generate_event_narrative(event_intel)
            
            events_detected.append(event_intel)
        
        return events_detected
    
    def continuous_intelligence_monitoring(self, planes_url: str, interval: int = 10):
        """Run continuous AI-powered intelligence monitoring"""
        logging.info("Starting AI Event Intelligence monitoring...")
        
        while True:
            try:
                # Fetch current aircraft data
                response = requests.get(planes_url, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                aircraft_list = data.get('aircraft', [])
                
                # Run AI analysis
                events = self.analyze_aircraft_data(aircraft_list)
                
                # Process detected events
                for event in events:
                    # Check if we've already alerted on this event recently
                    if not self.is_duplicate_event(event):
                        # Store in database
                        self.store_event_intelligence(event)
                        
                        # Send alert
                        self.send_intelligence_alert(event)
                        
                        # Add to active events
                        self.active_events[event.event_id] = event
                        
                        logging.info(f"AI Event detected: {event.event_type} with {len(event.aircraft_involved)} aircraft")
                
                time.sleep(interval)
                
            except Exception as e:
                logging.error(f"Error in AI intelligence monitoring: {e}")
                time.sleep(30)  # Wait longer on error
    
    def is_duplicate_event(self, event: EventIntelligence) -> bool:
        """Check if this event is too similar to recent events (prevent spam)"""
        current_time = time.time()
        
        for active_event in self.active_events.values():
            # If same event type within 30 minutes and close location
            time_diff = current_time - active_event.timestamp
            if time_diff < 1800:  # 30 minutes
                distance = self.haversine_distance(
                    event.location[0], event.location[1],
                    active_event.location[0], active_event.location[1]
                )
                if distance < 5 and event.event_type == active_event.event_type:
                    return True
        
        # Clean up old events
        self.active_events = {
            k: v for k, v in self.active_events.items()
            if current_time - v.timestamp < 3600  # Keep for 1 hour
        }
        
        return False

def main():
    """Initialize and run AI Event Intelligence System"""
    # Load config
    with open('config.json') as f:
        config = json.load(f)
    
    home_lat = config['home']['lat']
    home_lon = config['home']['lon']
    
    # Initialize AI system
    ai_detector = AIEventDetector(home_lat, home_lon, config)
    
    # Start continuous monitoring
    planes_url = "https://planes.hamm.me/data/aircraft.json"
    ai_detector.continuous_intelligence_monitoring(planes_url, interval=15)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler('ai_intelligence.log'),
            logging.StreamHandler()
        ]
    )
    
    main()
