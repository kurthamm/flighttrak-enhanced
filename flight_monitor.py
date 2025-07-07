#!/usr/bin/env python3
"""
Unified Flight Monitoring Service for FlightTrak
Consolidates aircraft tracking, anomaly detection, and AI intelligence
"""

import logging
import time
import threading
import signal
import sys
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any
import requests
import json

# Import our modules
from config_manager import config
from email_service import EmailService
from utils import (
    haversine_distance, 
    format_aircraft_info, 
    get_aircraft_distance,
    is_emergency_squawk,
    get_squawk_description,
    rotate_log_file,
    load_json_config
)

# Import optional modules
try:
    from anomaly_detector import FlightAnomalyDetector
    ANOMALY_DETECTION_AVAILABLE = True
except ImportError:
    ANOMALY_DETECTION_AVAILABLE = False
    logging.warning("Anomaly detection not available")

try:
    from ai_event_intelligence import AIEventDetector
    AI_INTELLIGENCE_AVAILABLE = True
except ImportError:
    AI_INTELLIGENCE_AVAILABLE = False
    logging.warning("AI intelligence not available")

try:
    from contextual_intelligence import ContextualIntelligence
    CONTEXTUAL_INTELLIGENCE_AVAILABLE = True
except ImportError:
    CONTEXTUAL_INTELLIGENCE_AVAILABLE = False
    logging.warning("Contextual intelligence not available")


class FlightMonitor:
    """Unified flight monitoring service"""
    
    def __init__(self):
        self.running = False
        self.threads = []
        
        # Configuration
        self.home_lat, self.home_lon = config.get_home_coordinates()
        self.planes_url = config.get('monitoring.planes_url')
        self.check_interval = config.get('monitoring.check_interval', 15)
        
        # Email service
        self.email_service = EmailService(config.get_email_config())
        
        # Aircraft tracking
        self.tracked_aircraft = {}
        self.detected_aircraft = set()
        self.aircraft_stats = defaultdict(lambda: {
            'positions': deque(maxlen=50),
            'altitudes': deque(maxlen=20),
            'speeds': deque(maxlen=20),
            'first_seen': None,
            'last_seen': None,
            'callsigns': set(),
            'squawks': set(),
            'rapid_changes': 0
        })
        
        # Alert deduplication
        self.recent_alerts = set()
        self.alert_cooldown = 300  # 5 minutes
        
        # Load aircraft list
        self._load_aircraft_list()
        
        # Initialize optional modules
        self.anomaly_detector = None
        self.ai_detector = None
        self.contextual_intel = None
        
        if ANOMALY_DETECTION_AVAILABLE and config.is_alert_enabled('anomaly'):
            try:
                self.anomaly_detector = FlightAnomalyDetector(self.home_lat, self.home_lon)
                logging.info("Anomaly detector initialized")
            except Exception as e:
                logging.error(f"Failed to initialize anomaly detector: {e}")
        
        if AI_INTELLIGENCE_AVAILABLE and config.is_alert_enabled('ai_intelligence'):
            try:
                self.ai_detector = AIEventDetector(self.home_lat, self.home_lon, config._config)
                logging.info("AI event detector initialized")
            except Exception as e:
                logging.error(f"Failed to initialize AI detector: {e}")
        
        if CONTEXTUAL_INTELLIGENCE_AVAILABLE:
            try:
                self.contextual_intel = ContextualIntelligence(self.home_lat, self.home_lon)
                logging.info("Contextual intelligence initialized")
            except Exception as e:
                logging.error(f"Failed to initialize contextual intelligence: {e}")
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logging.info("FlightTrak Unified Monitor initialized")
    
    def _load_aircraft_list(self) -> None:
        """Load tracked aircraft list"""
        try:
            aircraft_file = config.get('files.aircraft_list')
            aircraft_data = load_json_config(str(aircraft_file))
            
            self.tracked_aircraft = {
                aircraft['icao'].upper(): aircraft 
                for aircraft in aircraft_data.get('aircraft_to_detect', [])
            }
            
            logging.info(f"Loaded {len(self.tracked_aircraft)} tracked aircraft")
            
        except Exception as e:
            logging.error(f"Failed to load aircraft list: {e}")
            self.tracked_aircraft = {}
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals"""
        logging.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def _get_aircraft_data(self) -> List[Dict]:
        """Fetch current aircraft data"""
        try:
            response = requests.get(self.planes_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            aircraft_list = data.get('aircraft', [])
            logging.debug(f"Fetched {len(aircraft_list)} aircraft")
            
            return aircraft_list
            
        except Exception as e:
            logging.error(f"Error fetching aircraft data: {e}")
            return []
    
    def _check_tracked_aircraft(self, aircraft_list: List[Dict]) -> None:
        """Check for tracked aircraft and send alerts"""
        if not config.is_alert_enabled('tracked_aircraft'):
            return
        
        for aircraft in aircraft_list:
            icao = aircraft.get('hex', '').upper()
            
            if icao in self.tracked_aircraft:
                # Check if we've already alerted on this aircraft recently
                alert_key = f"tracked_{icao}"
                if alert_key in self.recent_alerts:
                    continue
                
                # Calculate distance
                distance = get_aircraft_distance(aircraft, self.home_lat, self.home_lon)
                if distance is None:
                    continue
                
                # Send alert
                tracked_info = self.tracked_aircraft[icao]
                recipients = config.get_alert_recipients('tracked_aircraft')
                
                if recipients:
                    success = self.email_service.send_aircraft_alert(
                        aircraft, tracked_info, distance, recipients
                    )
                    
                    if success:
                        self.recent_alerts.add(alert_key)
                        self.detected_aircraft.add(icao)
                        
                        # Log detection
                        self._log_aircraft_detection(aircraft, tracked_info, distance)
                        
                        logging.info(f"Tracked aircraft alert sent: {icao} "
                                   f"({tracked_info.get('description', 'Unknown')})")
    
    def _check_anomalies(self, aircraft_list: List[Dict]) -> None:
        """Check for aircraft anomalies"""
        if not self.anomaly_detector or not config.is_alert_enabled('anomaly'):
            return
        
        for aircraft in aircraft_list:
            try:
                anomalies = self.anomaly_detector.analyze_aircraft(aircraft)
                
                for anomaly in anomalies:
                    # Check alert deduplication
                    icao = aircraft.get('hex', '').upper()
                    anomaly_type = anomaly.get('type', 'unknown')
                    alert_key = f"anomaly_{icao}_{anomaly_type}"
                    
                    if alert_key in self.recent_alerts:
                        continue
                    
                    # Send alert
                    recipients = config.get_alert_recipients('anomaly')
                    if recipients:
                        success = self.email_service.send_anomaly_alert(anomaly, recipients)
                        
                        if success:
                            self.recent_alerts.add(alert_key)
                            logging.info(f"Anomaly alert sent: {icao} - {anomaly_type}")
                            
            except Exception as e:
                logging.error(f"Error checking anomalies for {aircraft.get('hex', 'unknown')}: {e}")
    
    def _check_ai_intelligence(self, aircraft_list: List[Dict]) -> None:
        """Check for AI intelligence events"""
        if not self.ai_detector or not config.is_alert_enabled('ai_intelligence'):
            return
        
        try:
            events = self.ai_detector.analyze_aircraft_data(aircraft_list)
            
            for event in events:
                # Check confidence threshold
                min_confidence = config.get('alerts.ai_intelligence.min_confidence', 0.6)
                if event.confidence < min_confidence:
                    continue
                
                # Check for duplicates
                if self.ai_detector.is_duplicate_event(event):
                    continue
                
                # Store event
                self.ai_detector.store_event_intelligence(event)
                
                # Send alert
                recipients = config.get_alert_recipients('ai_intelligence')
                if recipients:
                    event_data = {
                        'event_type': event.event_type,
                        'confidence': event.confidence,
                        'severity': event.severity,
                        'description': event.narrative,
                        'aircraft_involved': event.aircraft_involved,
                        'location': event.location,
                        'timestamp': event.timestamp
                    }
                    
                    success = self.email_service.send_ai_intelligence_alert(event_data, recipients)
                    
                    if success:
                        logging.info(f"AI intelligence alert sent: {event.event_type} "
                                   f"({event.confidence:.1%} confidence)")
                        
        except Exception as e:
            logging.error(f"Error in AI intelligence analysis: {e}")
    
    def _update_aircraft_stats(self, aircraft_list: List[Dict]) -> None:
        """Update aircraft statistics for pattern analysis"""
        current_time = time.time()
        
        for aircraft in aircraft_list:
            icao = aircraft.get('hex', '').upper()
            if not icao:
                continue
            
            stats = self.aircraft_stats[icao]
            
            # Update position history
            lat = aircraft.get('lat')
            lon = aircraft.get('lon')
            if lat is not None and lon is not None:
                stats['positions'].append((lat, lon, current_time))
            
            # Update altitude history
            altitude = aircraft.get('alt_baro')
            if altitude is not None:
                stats['altitudes'].append((altitude, current_time))
            
            # Update speed history
            speed = aircraft.get('gs')
            if speed is not None:
                stats['speeds'].append((speed, current_time))
            
            # Update metadata
            if stats['first_seen'] is None:
                stats['first_seen'] = current_time
            stats['last_seen'] = current_time
            
            # Track callsigns
            flight = aircraft.get('flight')
            if flight:
                stats['callsigns'].add(flight.strip())
            
            # Track squawks
            squawk = aircraft.get('squawk')
            if squawk:
                stats['squawks'].add(squawk)
    
    def _log_aircraft_detection(self, aircraft: Dict, tracked_info: Dict, distance: float) -> None:
        """Log aircraft detection to file"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'icao': aircraft.get('hex', '').upper(),
                'registration': tracked_info.get('tail_number', 'N/A'),
                'description': tracked_info.get('description', 'Unknown'),
                'flight': aircraft.get('flight', 'N/A'),
                'altitude': aircraft.get('alt_baro', 'N/A'),
                'speed': aircraft.get('gs', 'N/A'),
                'distance': round(distance, 2),
                'squawk': aircraft.get('squawk', 'N/A')
            }
            
            detected_file = config.get('files.detected_aircraft')
            with open(detected_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logging.error(f"Error logging aircraft detection: {e}")
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old alert keys to prevent memory buildup"""
        current_time = time.time()
        
        # Remove alerts older than cooldown period
        # This is a simplified cleanup - in production you'd want timestamped keys
        if len(self.recent_alerts) > 1000:  # Prevent unlimited growth
            self.recent_alerts.clear()
            logging.info("Cleared old alert keys")
    
    def _send_alive_notification(self) -> None:
        """Send periodic alive notification"""
        try:
            notification_email = config.get('email.notification_email')
            if not notification_email:
                return
            
            stats = {
                'tracked_aircraft': len(self.tracked_aircraft),
                'detected_today': len(self.detected_aircraft),
                'active_patterns': len(self.aircraft_stats),
                'modules_active': {
                    'anomaly_detection': self.anomaly_detector is not None,
                    'ai_intelligence': self.ai_detector is not None,
                    'contextual_intel': self.contextual_intel is not None
                }
            }
            
            success = self.email_service.send_service_notification(
                'FlightTrak Monitor', 'alive', notification_email, stats
            )
            
            if success:
                logging.info("Alive notification sent")
                
        except Exception as e:
            logging.error(f"Error sending alive notification: {e}")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        last_alive = time.time()
        alive_interval = config.get('monitoring.alive_interval', 86400)
        
        while self.running:
            try:
                # Get aircraft data
                aircraft_list = self._get_aircraft_data()
                
                if aircraft_list:
                    # Update statistics
                    self._update_aircraft_stats(aircraft_list)
                    
                    # Check for tracked aircraft
                    self._check_tracked_aircraft(aircraft_list)
                    
                    # Check for anomalies
                    self._check_anomalies(aircraft_list)
                    
                    # Check AI intelligence
                    self._check_ai_intelligence(aircraft_list)
                    
                    # Clean up old alerts periodically
                    self._cleanup_old_alerts()
                
                # Send alive notification
                current_time = time.time()
                if current_time - last_alive > alive_interval:
                    self._send_alive_notification()
                    last_alive = current_time
                
                # Rotate log files if needed
                log_file = config.get('files.log_file')
                rotate_log_file(str(log_file))
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                if self.running:
                    time.sleep(30)  # Wait longer on error
    
    def _contextual_intelligence_loop(self) -> None:
        """Run contextual intelligence gathering"""
        if not self.contextual_intel:
            return
        
        while self.running:
            try:
                self.contextual_intel.continuous_context_gathering(interval=300)
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Error in contextual intelligence: {e}")
                time.sleep(60)
    
    def start(self) -> None:
        """Start the monitoring service"""
        if self.running:
            logging.warning("Monitor already running")
            return
        
        self.running = True
        
        # Send startup notification
        notification_email = config.get('email.notification_email')
        if notification_email:
            self.email_service.send_service_notification(
                'FlightTrak Monitor', 'started', notification_email
            )
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        self.threads.append(monitor_thread)
        
        # Start contextual intelligence thread
        if self.contextual_intel:
            context_thread = threading.Thread(target=self._contextual_intelligence_loop, daemon=True)
            context_thread.start()
            self.threads.append(context_thread)
        
        logging.info("FlightTrak Monitor started")
        
        # Main thread loop
        try:
            while self.running:
                time.sleep(1)
                
                # Check thread health
                alive_threads = [t for t in self.threads if t.is_alive()]
                if len(alive_threads) < len(self.threads):
                    logging.warning(f"Thread health: {len(alive_threads)}/{len(self.threads)} alive")
                
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the monitoring service"""
        if not self.running:
            return
        
        logging.info("Stopping FlightTrak Monitor...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        # Send shutdown notification
        notification_email = config.get('email.notification_email')
        if notification_email:
            self.email_service.send_service_notification(
                'FlightTrak Monitor', 'stopped', notification_email
            )
        
        logging.info("FlightTrak Monitor stopped")


def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler('flighttrak_monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    logging.info("Starting FlightTrak Unified Monitor")
    
    try:
        monitor = FlightMonitor()
        monitor.start()
        return 0
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())