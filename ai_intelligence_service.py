#!/usr/bin/env python3
"""
FlightTrak AI Intelligence Service
Integrated launcher for the complete AI-powered event intelligence system
"""

import sys
import os
import time
import threading
import logging
import signal
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_event_intelligence import AIEventDetector
    from contextual_intelligence import ContextualIntelligence
    import json
    import requests
    import math
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required dependencies are installed:")
    print("pip install scikit-learn numpy requests feedparser")
    sys.exit(1)

# Import our unified modules
from config_manager import config
from email_service import EmailService
from utils import haversine_distance, load_json_config
import time

class AIIntelligenceService:
    """Main service coordinator for AI intelligence systems"""
    
    def __init__(self):
        self.running = True
        self.threads = []
        
        # Use unified configuration
        self.home_lat, self.home_lon = config.get_home_coordinates()
        
        # Initialize email service
        self.email_service = EmailService(config.get_email_config())
        
        # Initialize AI systems
        self.ai_detector = AIEventDetector(self.home_lat, self.home_lon, config._config)
        self.context_intel = ContextualIntelligence(self.home_lat, self.home_lon)
        
        # Load aircraft tracking list
        self.load_aircraft_list()
        self.detected_aircraft = set()  # Track recently detected aircraft
        self.recent_anomalies = set()  # Track recent anomaly alerts to prevent spam
        self.recent_ai_alerts = set()  # Track recent AI intelligence alerts to prevent spam
        
        # Initialize anomaly detector if enabled
        self.anomaly_detector = None
        if config.is_alert_enabled('anomaly'):
            try:
                from anomaly_detector import FlightAnomalyDetector
                self.anomaly_detector = FlightAnomalyDetector(self.home_lat, self.home_lon)
                logging.info("Anomaly detection system initialized")
            except ImportError as e:
                logging.warning(f"Anomaly detection disabled: {e}")
            except Exception as e:
                logging.error(f"Failed to initialize anomaly detector: {e}")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logging.info("FlightTrak AI Intelligence Service initialized")
    
    def load_aircraft_list(self):
        """Load the aircraft tracking list"""
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
    
    
    def check_tracked_aircraft(self, aircraft_list: list):
        """Check for tracked aircraft and send alerts if enabled"""
        # Check if tracked aircraft alerts are enabled
        if not config.is_alert_enabled('tracked_aircraft'):
            return
        
        for aircraft in aircraft_list:
            icao = aircraft.get('hex', '').upper()
            if icao in self.tracked_aircraft and icao not in self.detected_aircraft:
                # Calculate distance from home
                lat, lon = aircraft.get('lat'), aircraft.get('lon')
                if lat and lon:
                    distance = self.haversine_distance(self.home_lat, self.home_lon, lat, lon)
                    
                    # Send alert to configured recipients
                    self.send_tracked_aircraft_alert(aircraft, self.tracked_aircraft[icao], distance)
                    self.detected_aircraft.add(icao)
                    
                    logging.info(f"Tracked aircraft detected: {icao} ({self.tracked_aircraft[icao].get('description', 'Unknown')})")
    
    def send_tracked_aircraft_alert(self, aircraft: dict, tracked_info: dict, distance: float):
        """Send aircraft detection alert to configured recipients"""
        try:
            recipients = config.get_alert_recipients('tracked_aircraft')
            
            if not recipients:
                logging.warning("No recipients configured for tracked aircraft alerts")
                return
            
            # Use unified email service
            success = self.email_service.send_aircraft_alert(aircraft, tracked_info, distance, recipients)
            
            if success:
                logging.info(f"Tracked aircraft alert sent to {len(recipients)} recipients")
            else:
                logging.error("Failed to send tracked aircraft alert")
            
        except Exception as e:
            logging.error(f"Error sending tracked aircraft alert: {e}")
    
    def generate_tracked_aircraft_email(self, aircraft: dict, tracked_info: dict, distance: float) -> str:
        """Generate HTML email for tracked aircraft detection"""
        html_content = f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:700px;margin:0 auto;background:white;padding:25px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);'>
                
                <!-- Header -->
                <div style='text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid #4CAF50;'>
                    <h1 style='color:#4CAF50;margin:0;font-size:24px;'>✈️ FlightTrak Aircraft Alert</h1>
                    <h2 style='color:#333;margin:10px 0;font-size:18px;'>{tracked_info.get('description', 'Tracked Aircraft')} Detected</h2>
                </div>
                
                <!-- Aircraft Info -->
                <div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#4CAF50;margin:0 0 15px 0;'>Aircraft Details</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:5px;font-weight:bold;'>ICAO:</td><td style='padding:5px;'>{aircraft.get('hex', 'N/A').upper()}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Registration:</td><td style='padding:5px;'>{tracked_info.get('tail_number', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Aircraft:</td><td style='padding:5px;'>{tracked_info.get('model', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Owner:</td><td style='padding:5px;'>{tracked_info.get('owner', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Flight:</td><td style='padding:5px;'>{aircraft.get('flight', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Altitude:</td><td style='padding:5px;'>{aircraft.get('alt_baro', 'N/A')} ft</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Speed:</td><td style='padding:5px;'>{aircraft.get('gs', 'N/A')} kt</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Distance:</td><td style='padding:5px;'>{distance:.1f} miles from home</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Squawk:</td><td style='padding:5px;'>{aircraft.get('squawk', 'N/A')}</td></tr>
                    </table>
                </div>
                
                <!-- Flight Tracking Link -->
                <div style='text-align:center;margin:20px 0;'>
                    <a href='https://flightaware.com/live/flight/{aircraft.get("hex", "").upper()}' 
                       style='background:#4CAF50;color:white;padding:12px 25px;text-decoration:none;border-radius:5px;font-weight:bold;'>
                        Track on FlightAware
                    </a>
                </div>
                
                <!-- Footer -->
                <div style='text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #ddd;'>
                    <p style='font-size:12px;color:#666;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        FlightTrak Enhanced Alert System
                    </p>
                </div>
            </div>
        </body></html>
        """
        
        return html_content
    
    def send_ai_intelligence_alert(self, event_intel):
        """Send AI intelligence alert to configured recipients"""
        try:
            recipients = config.get_alert_recipients('ai_intelligence')
            
            if not recipients:
                logging.warning("No recipients configured for AI intelligence alerts")
                return
            
            # Prepare event data for email service
            event_data = {
                'event_type': event_intel.event_type,
                'confidence': event_intel.confidence,
                'severity': event_intel.severity,
                'location': getattr(event_intel, 'location', 'Unknown'),
                'description': getattr(event_intel, 'narrative', 'AI intelligence event detected'),
                'aircraft_involved': getattr(event_intel, 'aircraft_involved', []),
                'timestamp': getattr(event_intel, 'timestamp', time.time())
            }
            
            # Use unified email service
            success = self.email_service.send_ai_intelligence_alert(event_data, recipients)
            
            if success:
                logging.info(f"AI Intelligence alert sent to {len(recipients)} recipients: {event_intel.event_type}")
            else:
                logging.error("Failed to send AI intelligence alert")
            
        except Exception as e:
            logging.error(f"Error sending AI intelligence alert: {e}")
    
    def send_anomaly_alert(self, anomaly: dict):
        """Send anomaly alert to configured recipients"""
        try:
            if not config.is_alert_enabled('anomaly'):
                return
            
            recipients = config.get_alert_recipients('anomaly')
            if not recipients:
                logging.warning("No recipients configured for anomaly alerts")
                return
            
            # Use unified email service
            success = self.email_service.send_anomaly_alert(anomaly, recipients)
            
            if success:
                logging.info(f"Anomaly alert sent to {len(recipients)} recipients: {anomaly.get('type', 'unknown')}")
            else:
                logging.error("Failed to send anomaly alert")
            
        except Exception as e:
            logging.error(f"Error sending anomaly alert: {e}")
    
    def generate_anomaly_email(self, anomaly: dict, aircraft: dict) -> str:
        """Generate HTML email for anomaly alert"""
        severity_colors = {
            'CRITICAL': '#ff4757',
            'HIGH': '#ff6b6b', 
            'MEDIUM': '#ffa502',
            'LOW': '#3742fa'
        }
        
        color = severity_colors.get(anomaly['severity'], '#666')
        
        html_content = f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:700px;margin:0 auto;background:white;padding:25px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);'>
                
                <!-- Header -->
                <div style='text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid {color};'>
                    <h1 style='color:{color};margin:0;font-size:24px;'>⚠️ FlightTrak Anomaly Alert</h1>
                    <h2 style='color:#333;margin:10px 0;font-size:18px;'>{anomaly["type"].replace("_", " ").title()}: {anomaly["description"]}</h2>
                    <p style='color:{color};font-size:16px;margin:5px 0;font-weight:bold;'>Severity: {anomaly["severity"]}</p>
                </div>
                
                <!-- Aircraft Details -->
                <div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#333;margin:0 0 15px 0;'>Aircraft Details:</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:5px;font-weight:bold;'>ICAO:</td><td style='padding:5px;'>{aircraft.get('hex', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Flight:</td><td style='padding:5px;'>{aircraft.get('flight', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Altitude:</td><td style='padding:5px;'>{aircraft.get('alt_baro', 'N/A')} ft</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Speed:</td><td style='padding:5px;'>{aircraft.get('gs', 'N/A')} kt</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Vertical Rate:</td><td style='padding:5px;'>{aircraft.get('baro_rate', 'N/A')} ft/min</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Track:</td><td style='padding:5px;'>{aircraft.get('track', 'N/A')}°</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Squawk:</td><td style='padding:5px;'>{aircraft.get('squawk', 'N/A')}</td></tr>
                    </table>
                </div>
                
                <!-- Flight Tracking Link -->
                <div style='text-align:center;margin:20px 0;'>
                    <a href='https://flightaware.com/live/flight/{aircraft.get("hex", "").upper()}' 
                       style='background:{color};color:white;padding:12px 25px;text-decoration:none;border-radius:5px;font-weight:bold;'>
                        Track on FlightAware
                    </a>
                </div>
                
                <!-- Footer -->
                <div style='text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #ddd;'>
                    <p style='font-size:12px;color:#666;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        FlightTrak Enhanced Alert System
                    </p>
                </div>
            </div>
        </body></html>
        """
        
        return html_content
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def start_integrated_monitoring(self):
        """Start integrated monitoring for both tracked aircraft and AI intelligence"""
        def run_integrated_monitoring():
            planes_url = "https://planes.hamm.me/data/aircraft.json"
            while self.running:
                try:
                    # Fetch current aircraft data
                    response = requests.get(planes_url, timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    aircraft_list = data.get('aircraft', [])
                    
                    # Check for tracked aircraft (original system)
                    self.check_tracked_aircraft(aircraft_list)
                    
                    # Run AI intelligence analysis (if enabled)
                    if config.is_alert_enabled('ai_intelligence'):
                        events = self.ai_detector.analyze_aircraft_data(aircraft_list)
                        
                        # Process detected AI events
                        for event in events:
                            # Check confidence threshold
                            min_confidence = config.get('alerts.ai_intelligence.min_confidence', 0.6)
                            if event.confidence < min_confidence:
                                continue
                                
                            # Create unique key for this event type
                            event_key = f"{event.event_type}_{int(time.time() // 1800)}"  # 30-minute windows
                            
                            # Check if we've already alerted on this event recently (double check)
                            if (not self.ai_detector.is_duplicate_event(event) and 
                                event_key not in self.recent_ai_alerts):
                                
                                # Store in database
                                self.ai_detector.store_event_intelligence(event)
                                
                                # Send AI intelligence alert to configured recipients
                                self.send_ai_intelligence_alert(event)
                                
                                # Add to deduplication tracking
                                self.recent_ai_alerts.add(event_key)
                                self.ai_detector.active_events[event.event_id] = event
                                
                                logging.info(f"AI Event detected: {event.event_type} with {len(event.aircraft_involved)} aircraft")
                            else:
                                logging.debug(f"AI Event {event.event_type} skipped - duplicate or recent")
                    
                    # Run anomaly detection (if enabled)
                    if self.anomaly_detector:
                        for aircraft in aircraft_list:
                            anomalies = self.anomaly_detector.analyze_aircraft(aircraft)
                            for anomaly in anomalies:
                                # Create unique key to prevent duplicate alerts
                                anomaly_key = f"{anomaly['aircraft'].get('hex', '')}_{anomaly['type']}_{int(time.time() // 300)}"  # 5-minute windows
                                if anomaly_key not in self.recent_anomalies:
                                    self.send_anomaly_alert(anomaly)
                                    self.recent_anomalies.add(anomaly_key)
                                    
                        # Clean up old alert keys (keep only last 2 hours)
                        current_window = int(time.time() // 300)
                        self.recent_anomalies = {key for key in self.recent_anomalies if int(key.split('_')[-1]) > current_window - 24}
                        
                        # Clean up old AI alert keys (keep only last 2 hours)
                        current_ai_window = int(time.time() // 1800)
                        self.recent_ai_alerts = {key for key in self.recent_ai_alerts if int(key.split('_')[-1]) > current_ai_window - 4}
                    
                    time.sleep(15)  # Check every 15 seconds
                    
                except Exception as e:
                    logging.error(f"Error in integrated monitoring: {e}")
                    if self.running:
                        time.sleep(30)  # Wait longer on error
        
        thread = threading.Thread(target=run_integrated_monitoring, daemon=True)
        thread.start()
        self.threads.append(thread)
        logging.info("Integrated Monitoring system started")
    
    def start_contextual_intelligence(self):
        """Start contextual intelligence gathering"""
        def run_context_gathering():
            while self.running:
                try:
                    self.context_intel.continuous_context_gathering(interval=300)  # Every 5 minutes
                except Exception as e:
                    logging.error(f"Error in contextual intelligence: {e}")
                    if self.running:
                        time.sleep(60)  # Wait before retrying
        
        thread = threading.Thread(target=run_context_gathering, daemon=True)
        thread.start()
        self.threads.append(thread)
        logging.info("Contextual Intelligence system started")
    
    def start_enhanced_analysis(self):
        """Start enhanced analysis that combines AI detection with contextual data"""
        def run_enhanced_analysis():
            while self.running:
                try:
                    # This could be expanded to periodically enhance events with context
                    time.sleep(60)  # Check every minute
                    
                    # Get recent events and enhance them with contextual data
                    # This is where we'd integrate the two systems more tightly
                    
                except Exception as e:
                    logging.error(f"Error in enhanced analysis: {e}")
                    if self.running:
                        time.sleep(30)
        
        thread = threading.Thread(target=run_enhanced_analysis, daemon=True)
        thread.start()
        self.threads.append(thread)
        logging.info("Enhanced Analysis system started")
    
    def send_startup_notification(self):
        """Send notification that AI Intelligence system has started"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            email_cfg = self.config['email_config']
            
            html_content = f"""
            <html><body style='font-family:Arial,sans-serif;background:#0a0e27;color:#e0e6ed;padding:20px;'>
                <div style='max-width:600px;margin:0 auto;background:#1a1f3a;padding:20px;border-radius:10px;'>
                    <h2 style='color:#4fc3f7;'>🧠 FlightTrak AI Intelligence Service</h2>
                    <h3 style='color:#feca57;'>System Activated</h3>
                    
                    <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                        <h4 style='color:#4fc3f7;margin:0 0 10px 0;'>Active Systems:</h4>
                        <ul style='color:#e0e6ed;margin:0;'>
                            <li>✈️ Tracked Aircraft Monitoring (Group Alerts)</li>
                            <li>🎯 Advanced Pattern Recognition</li>
                            <li>🔍 Contextual Intelligence Gathering</li>
                            <li>📊 Machine Learning Event Classification</li>
                            <li>📰 Multi-Source Context Integration</li>
                            <li>🚨 Intelligent Alert Generation</li>
                        </ul>
                    </div>
                    
                    <div style='background:#2a3f5f;padding:15px;border-radius:8px;margin:15px 0;'>
                        <h4 style='color:#4fc3f7;margin:0 0 10px 0;'>Intelligence Capabilities:</h4>
                        <ul style='color:#e0e6ed;margin:0;'>
                            <li>🔄 Real-time aircraft behavior analysis</li>
                            <li>🗞️ News feed integration and correlation</li>
                            <li>🌤️ Weather alert contextual awareness</li>
                            <li>✈️ Aviation NOTAM monitoring</li>
                            <li>🎯 Event type prediction and confidence scoring</li>
                            <li>📝 Natural language intelligence reports</li>
                        </ul>
                    </div>
                    
                    <p style='color:#feca57;text-align:center;margin:20px 0;'>
                        <strong>📧 Tracked aircraft alerts → Group recipients<br>
                        🧠 AI intelligence alerts → kurt@hamm.me</strong>
                    </p>
                    
                    <p style='font-size:12px;color:#8892b0;text-align:center;'>
                        Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        FlightTrak AI Intelligence v1.0
                    </p>
                </div>
            </body></html>
            """
            
            message = Mail(
                from_email=email_cfg['sender'],
                to_emails='kurt@hamm.me',
                subject='🧠 FlightTrak AI Intelligence Service Activated',
                html_content=html_content
            )
            
            sg = SendGridAPIClient(email_cfg['sendgrid_api_key'])
            resp = sg.send(message)
            logging.info(f"AI Intelligence startup notification sent (status {resp.status_code})")
            
        except Exception as e:
            logging.error(f"Error sending startup notification: {e}")
    
    def monitor_system_health(self):
        """Monitor the health of all AI systems"""
        def health_monitor():
            while self.running:
                try:
                    # Check if all threads are alive
                    alive_threads = [t for t in self.threads if t.is_alive()]
                    
                    if len(alive_threads) != len(self.threads):
                        logging.warning(f"Thread health check: {len(alive_threads)}/{len(self.threads)} threads alive")
                    
                    # Log system status
                    if len(alive_threads) == len(self.threads):
                        logging.info("AI Intelligence systems: All systems operational")
                    
                    time.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    logging.error(f"Error in health monitoring: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=health_monitor, daemon=True)
        thread.start()
        self.threads.append(thread)
        logging.info("System health monitoring started")
    
    def run(self):
        """Main service runner"""
        logging.info("Starting FlightTrak AI Intelligence Service...")
        
        # Send startup notification
        self.send_startup_notification()
        
        # Start all AI systems
        self.start_contextual_intelligence()
        time.sleep(2)  # Stagger startup
        
        self.start_integrated_monitoring()
        time.sleep(2)
        
        self.start_enhanced_analysis()
        time.sleep(2)
        
        self.monitor_system_health()
        
        logging.info("All AI Intelligence systems started successfully")
        
        # Main service loop
        try:
            while self.running:
                time.sleep(10)  # Main thread sleep
                
                # Check if we need to restart any failed threads
                for i, thread in enumerate(self.threads):
                    if not thread.is_alive() and self.running:
                        logging.warning(f"Thread {i} died, restarting services...")
                        # In a production system, you'd restart individual threads here
                        break
                        
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all systems gracefully"""
        logging.info("Shutting down AI Intelligence Service...")
        self.running = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logging.info("AI Intelligence Service shutdown complete")

def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s]: %(message)s',
        handlers=[
            logging.FileHandler('ai_intelligence_service.log'),
            logging.StreamHandler()
        ]
    )
    
    # Check dependencies
    try:
        import sklearn
        import numpy
        import feedparser
        logging.info("All AI dependencies available")
    except ImportError as e:
        logging.error(f"Missing AI dependencies: {e}")
        print("\nPlease install required packages:")
        print("pip install scikit-learn numpy feedparser")
        return 1
    
    # Start service
    service = AIIntelligenceService()
    
    try:
        service.run()
        return 0
    except Exception as e:
        logging.error(f"Fatal error in AI Intelligence Service: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())