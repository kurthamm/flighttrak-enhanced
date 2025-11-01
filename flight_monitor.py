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
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any, Tuple
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
    from twitter_poster import TwitterPoster
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    logging.warning("Twitter posting not available")


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
        
        # Smart alert system - track closest approach
        self.tracked_flybys = {}  # Track aircraft approaching/departing
        # Structure: {icao: {'first_seen': time, 'distances': [d1, d2, ...], 'closest_data': {...}, 'last_update': time}}
        self.recent_alerts = {}  # Track when we last alerted (for 24hr cooldown)
        self.alert_cooldown = 86400  # 24 hours between alerts for same aircraft
        self.flyby_timeout = 1800  # 30 minutes max tracking time before forcing alert

        # Health monitoring
        self.last_aircraft_seen = time.time()  # Track when we last saw ANY aircraft
        self.last_health_alert = 0  # Track when we last sent a health alert
        self.total_aircraft_seen = 0  # Count of all aircraft detected (for stats)
        
        # Anomaly alert rate limiting
        self.anomaly_alert_times = defaultdict(float)  # Track last alert time per aircraft/type
        self.anomaly_cooldown = 3600  # 1 hour cooldown for same anomaly type per aircraft
        self.max_anomaly_alerts_per_hour = 5  # Max alerts per aircraft per hour
        self.anomaly_alert_counts = defaultdict(lambda: defaultdict(int))  # Count per aircraft per hour
        
        # Load aircraft list
        self._load_aircraft_list()

        # Initialize optional modules
        self.anomaly_detector = None
        self.twitter_poster = None

        if ANOMALY_DETECTION_AVAILABLE and config.is_alert_enabled('anomaly'):
            try:
                self.anomaly_detector = FlightAnomalyDetector(self.home_lat, self.home_lon)
                logging.info("Anomaly detector initialized (emergency squawks only)")
            except Exception as e:
                logging.error(f"Failed to initialize anomaly detector: {e}")

        if TWITTER_AVAILABLE:
            try:
                self.twitter_poster = TwitterPoster()
                logging.info("Twitter poster initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Twitter poster: {e}")
        
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

            # Update health monitoring: if we see ANY aircraft, update the timestamp
            if aircraft_list:
                self.last_aircraft_seen = time.time()
                self.total_aircraft_seen += len(aircraft_list)

            return aircraft_list

        except Exception as e:
            logging.error(f"Error fetching aircraft data: {e}")
            return []
    
    def _check_tracked_aircraft(self, aircraft_list: List[Dict]) -> None:
        """Check for tracked aircraft with smart closest-approach alerting"""
        if not config.is_alert_enabled('tracked_aircraft'):
            return

        current_time = time.time()
        visible_tracked = set()  # Track which aircraft we see in this update

        # Process all visible tracked aircraft
        for aircraft in aircraft_list:
            icao = aircraft.get('hex', '').upper()

            if icao not in self.tracked_aircraft:
                continue

            visible_tracked.add(icao)

            # Get tracked aircraft info
            tracked_info = self.tracked_aircraft[icao]

            # Check 24-hour cooldown
            alert_key = f"tracked_{icao}"
            if alert_key in self.recent_alerts:
                if current_time - self.recent_alerts[alert_key] < self.alert_cooldown:
                    continue

            # Calculate distance
            distance = get_aircraft_distance(aircraft, self.home_lat, self.home_lon)
            if distance is None:
                continue

            # Initialize or update flyby tracking
            if icao not in self.tracked_flybys:
                # First detection - start tracking
                self.tracked_flybys[icao] = {
                    'first_seen': current_time,
                    'distances': [distance],
                    'closest_distance': distance,
                    'closest_data': {'aircraft': aircraft, 'distance': distance},
                    'last_update': current_time
                }
                logging.warning(f"STARTED TRACKING: {icao} ({tracked_info.get('description', 'Unknown')}) at {distance:.1f} miles")
            else:
                # Update existing tracking
                flyby = self.tracked_flybys[icao]
                flyby['distances'].append(distance)
                flyby['last_update'] = current_time

                # Update closest point if this is closer
                if distance < flyby['closest_distance']:
                    flyby['closest_distance'] = distance
                    flyby['closest_data'] = {'aircraft': aircraft, 'distance': distance}
                    logging.debug(f"New closest point for {icao}: {distance:.1f} miles")

        # Check for aircraft that have left visibility or need alerts
        for icao in list(self.tracked_flybys.keys()):
            flyby = self.tracked_flybys[icao]

            # Check if aircraft is still visible
            if icao in visible_tracked:
                # Still visible - check if we should alert due to timeout
                tracking_duration = current_time - flyby['first_seen']
                if tracking_duration > self.flyby_timeout:
                    # Timeout - send alert for closest point
                    logging.info(f"Flyby timeout for {icao}, sending alert at closest point: {flyby['closest_distance']:.1f} miles")
                    self._send_aircraft_alert(icao, flyby['closest_data'])
                    del self.tracked_flybys[icao]
                continue

            # Aircraft no longer visible - check if we should alert
            # Need at least 2 distance measurements to determine trend
            if len(flyby['distances']) < 2:
                # Only one measurement, send alert immediately
                logging.info(f"{icao} disappeared after 1 measurement, sending alert")
                self._send_aircraft_alert(icao, flyby['closest_data'])
                del self.tracked_flybys[icao]
                continue

            # Check if aircraft was approaching (getting closer) before disappearing
            # Compare first distance to closest distance
            was_approaching = flyby['distances'][0] > flyby['closest_distance']

            # Also check last few measurements to see if it was departing
            recent_distances = flyby['distances'][-3:]  # Last 3 measurements
            if len(recent_distances) >= 2:
                # If distance was increasing in recent measurements, it was departing
                was_departing = recent_distances[-1] > recent_distances[0]
            else:
                was_departing = False

            if was_approaching or was_departing:
                # Aircraft came closer then left, OR was moving away - send alert at closest point
                reason = "approached and departed" if was_approaching and was_departing else \
                         "approached" if was_approaching else "moved away"
                logging.info(f"{icao} {reason}, sending alert at closest point: {flyby['closest_distance']:.1f} miles")
                self._send_aircraft_alert(icao, flyby['closest_data'])
            else:
                # Aircraft stayed at similar distance then disappeared - still send alert
                logging.info(f"{icao} disappeared, sending alert at closest point: {flyby['closest_distance']:.1f} miles")
                self._send_aircraft_alert(icao, flyby['closest_data'])

            # Clean up
            del self.tracked_flybys[icao]

    def _send_aircraft_alert(self, icao: str, closest_data: Dict) -> None:
        """Send alert for a tracked aircraft at its closest approach point"""
        aircraft = closest_data['aircraft']
        distance = closest_data['distance']
        tracked_info = self.tracked_aircraft[icao]
        recipients = config.get_alert_recipients('tracked_aircraft')

        if not recipients:
            logging.error(f"ALERT BLOCKED: No recipients configured for {icao}")
            return

        logging.warning(f"SENDING ALERT: {icao} ({tracked_info.get('description', 'Unknown')}) at {distance:.1f} miles to {len(recipients)} recipients")

        # Send email alert
        success = self.email_service.send_aircraft_alert(
            aircraft, tracked_info, distance, recipients
        )

        if success:
            current_time = time.time()
            alert_key = f"tracked_{icao}"
            self.recent_alerts[alert_key] = current_time
            self.detected_aircraft.add(icao)

            # Log detection
            self._log_aircraft_detection(aircraft, tracked_info, distance)

            logging.warning(f"ALERT SENT SUCCESSFULLY: {icao} ({tracked_info.get('description', 'Unknown')}) at closest approach: {distance:.1f} miles")

            # Queue for Twitter posting (if enabled)
            if self.twitter_poster:
                self.twitter_poster.queue_post(aircraft, tracked_info, distance)
        else:
            logging.error(f"ALERT FAILED: Email send failed for {icao}")
    
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
                    current_time = time.time()

                    if alert_key in self.recent_alerts:
                        # Check if cooldown period has passed
                        if current_time - self.recent_alerts[alert_key] < self.alert_cooldown:
                            continue
                    
                    # Rate limiting checks
                    current_time = time.time()
                    current_hour = int(current_time // 3600)
                    
                    # Check cooldown for specific anomaly type
                    last_alert_time = self.anomaly_alert_times[alert_key]
                    if current_time - last_alert_time < self.anomaly_cooldown:
                        logging.debug(f"Anomaly alert rate limited (cooldown): {icao} - {anomaly_type}")
                        continue
                    
                    # Check hourly limit per aircraft
                    if self.anomaly_alert_counts[icao][current_hour] >= self.max_anomaly_alerts_per_hour:
                        logging.debug(f"Anomaly alert rate limited (hourly max): {icao}")
                        continue
                    
                    # Skip LOW severity anomalies if we've had recent alerts for this aircraft
                    if anomaly.get('severity') == 'LOW' and self.anomaly_alert_counts[icao][current_hour] > 2:
                        logging.debug(f"Skipping LOW severity anomaly due to recent alerts: {icao} - {anomaly_type}")
                        continue
                    
                    # Send alert
                    recipients = config.get_alert_recipients('anomaly')
                    if recipients:
                        # Send anomaly email alert
                        success = self.email_service.send_anomaly_alert(anomaly, recipients)

                        if success:
                            self.recent_alerts[alert_key] = current_time  # Store timestamp
                            self.anomaly_alert_times[alert_key] = current_time
                            self.anomaly_alert_counts[icao][current_hour] += 1

                            # Log emergency squawk events to file
                            if anomaly_type == 'EMERGENCY_SQUAWK':
                                self._log_emergency_event(anomaly)

                            logging.info(f"Anomaly alert sent: {icao} - {anomaly_type} ({anomaly.get('severity', 'UNKNOWN')})")
                            
            except Exception as e:
                logging.error(f"Error checking anomalies for {aircraft.get('hex', 'unknown')}: {e}")
    
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

    def _log_emergency_event(self, anomaly: Dict) -> None:
        """Log emergency squawk event to file"""
        try:
            aircraft = anomaly.get('aircraft', {})

            # Emergency type mapping
            emergency_types = {
                '7500': 'HIJACK',
                '7600': 'RADIO FAILURE',
                '7700': 'EMERGENCY',
                '7777': 'MILITARY INTERCEPT'
            }

            squawk = anomaly.get('squawk_code', '')

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'icao': aircraft.get('hex', '').upper(),
                'squawk': squawk,
                'type': emergency_types.get(squawk, 'UNKNOWN'),
                'description': anomaly.get('description', 'Unknown emergency'),
                'flight': aircraft.get('flight', 'N/A'),
                'altitude': aircraft.get('alt_baro', 'N/A'),
                'speed': aircraft.get('gs', 'N/A'),
                'lat': aircraft.get('lat', 'N/A'),
                'lon': aircraft.get('lon', 'N/A')
            }

            emergency_file = 'emergency_events.json'
            with open(emergency_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

            logging.info(f"Emergency event logged: {squawk} - {aircraft.get('hex', 'Unknown')}")

        except Exception as e:
            logging.error(f"Error logging emergency event: {e}")
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old alert keys to prevent memory buildup"""
        current_time = time.time()

        # Remove alerts older than cooldown period
        expired_keys = [
            key for key, timestamp in self.recent_alerts.items()
            if current_time - timestamp > self.alert_cooldown
        ]

        for key in expired_keys:
            del self.recent_alerts[key]

        if expired_keys:
            logging.debug(f"Cleaned up {len(expired_keys)} expired alert keys")
    
    def _run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics to identify specific problems"""
        diagnostics = {
            'network': {'status': 'unknown', 'details': ''},
            'planes_url': {'status': 'unknown', 'details': ''},
            'dump1090_service': {'status': 'unknown', 'details': ''},
            'dump1090_port': {'status': 'unknown', 'details': ''},
        }

        # 1. Test basic network connectivity
        try:
            response = requests.get('https://www.google.com', timeout=5)
            diagnostics['network']['status'] = 'ok'
            diagnostics['network']['details'] = 'Internet connectivity OK'
        except Exception as e:
            diagnostics['network']['status'] = 'failed'
            diagnostics['network']['details'] = f'No internet connectivity: {str(e)}'

        # 2. Test planes.hamm.me URL
        try:
            response = requests.get(self.planes_url, timeout=10)
            data = response.json()
            aircraft_count = len(data.get('aircraft', []))

            if response.status_code == 200:
                if aircraft_count == 0:
                    diagnostics['planes_url']['status'] = 'warning'
                    diagnostics['planes_url']['details'] = f'URL reachable but reporting 0 aircraft (dump1090 may be running but not receiving data)'
                else:
                    diagnostics['planes_url']['status'] = 'ok'
                    diagnostics['planes_url']['details'] = f'URL reachable, reporting {aircraft_count} aircraft'
            else:
                diagnostics['planes_url']['status'] = 'failed'
                diagnostics['planes_url']['details'] = f'HTTP {response.status_code}'
        except requests.exceptions.ConnectionError as e:
            diagnostics['planes_url']['status'] = 'failed'
            diagnostics['planes_url']['details'] = f'Cannot connect to {self.planes_url} (Cloudflare tunnel may be down)'
        except Exception as e:
            diagnostics['planes_url']['status'] = 'failed'
            diagnostics['planes_url']['details'] = f'Error: {str(e)}'

        # 3. Check dump1090 systemd service status
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'dump1090'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip() == 'active':
                diagnostics['dump1090_service']['status'] = 'ok'
                diagnostics['dump1090_service']['details'] = 'Service is active and running'
            else:
                diagnostics['dump1090_service']['status'] = 'failed'
                status = result.stdout.strip() or 'inactive'
                diagnostics['dump1090_service']['details'] = f'Service status: {status}'

                # Try to get more details
                try:
                    status_result = subprocess.run(
                        ['systemctl', 'status', 'dump1090'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # Extract the Active line
                    for line in status_result.stdout.split('\n'):
                        if 'Active:' in line:
                            diagnostics['dump1090_service']['details'] = line.strip()
                            break
                except (AttributeError, ValueError, IndexError):
                    pass

        except subprocess.TimeoutExpired:
            diagnostics['dump1090_service']['status'] = 'failed'
            diagnostics['dump1090_service']['details'] = 'systemctl command timed out'
        except FileNotFoundError:
            diagnostics['dump1090_service']['status'] = 'unknown'
            diagnostics['dump1090_service']['details'] = 'systemctl not available (not running as systemd?)'
        except Exception as e:
            diagnostics['dump1090_service']['status'] = 'unknown'
            diagnostics['dump1090_service']['details'] = f'Cannot check service: {str(e)}'

        # 4. Test dump1090 local port connectivity (if running locally)
        dump1090_port = config.get('monitoring.dump1090_port', 30002)
        dump1090_host = config.get('monitoring.dump1090_host', '127.0.0.1')

        # Only test if dump1090 is configured for local access
        if dump1090_host in ['127.0.0.1', 'localhost']:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((dump1090_host, dump1090_port))
                sock.close()

                if result == 0:
                    diagnostics['dump1090_port']['status'] = 'ok'
                    diagnostics['dump1090_port']['details'] = f'Port {dump1090_port} is open and listening'
                else:
                    diagnostics['dump1090_port']['status'] = 'failed'
                    diagnostics['dump1090_port']['details'] = f'Port {dump1090_port} is not accessible (receiver may not be running)'
            except Exception as e:
                diagnostics['dump1090_port']['status'] = 'failed'
                diagnostics['dump1090_port']['details'] = f'Cannot test port: {str(e)}'
        else:
            diagnostics['dump1090_port']['status'] = 'skipped'
            diagnostics['dump1090_port']['details'] = f'Using remote dump1090 via {self.planes_url}'

        return diagnostics

    def _check_system_health(self) -> None:
        """Check if system is healthy (seeing aircraft) and alert if not"""
        if not config.is_alert_enabled('health_monitoring'):
            return

        try:
            threshold_minutes = config.get('alerts.health_monitoring.no_aircraft_threshold_minutes', 60)
            alert_cooldown_hours = config.get('alerts.health_monitoring.alert_cooldown_hours', 4)

            current_time = time.time()
            time_since_aircraft = current_time - self.last_aircraft_seen
            time_since_last_alert = current_time - self.last_health_alert

            # Convert to minutes for comparison
            minutes_since_aircraft = time_since_aircraft / 60
            hours_since_alert = time_since_last_alert / 3600

            # Check if we should send an alert
            if minutes_since_aircraft > threshold_minutes and hours_since_alert > alert_cooldown_hours:
                recipients = config.get_alert_recipients('health_monitoring')
                if recipients:
                    logging.warning(f"Health check: No aircraft detected for {minutes_since_aircraft:.1f} minutes")
                    logging.info("Running system diagnostics...")

                    # Run diagnostics to identify the actual problem
                    diagnostics = self._run_diagnostics()

                    success = self.email_service.send_health_alert(
                        minutes_since_aircraft,
                        threshold_minutes,
                        diagnostics,
                        recipients
                    )

                    if success:
                        self.last_health_alert = current_time
                        logging.info(f"Health alert sent to {len(recipients)} recipients")

                        # Log diagnostic results
                        for check, result in diagnostics.items():
                            logging.info(f"  {check}: {result['status']} - {result['details']}")

        except Exception as e:
            logging.error(f"Error checking system health: {e}")

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
                    'anomaly_detection': self.anomaly_detector is not None
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

                    # Process Twitter posting queue (for delayed posts)
                    if self.twitter_poster:
                        self.twitter_poster.process_queue()

                    # Clean up old alerts periodically
                    self._cleanup_old_alerts()

                # Check system health (no aircraft detected)
                self._check_system_health()

                # Send alive notification (disabled temporarily)
                current_time = time.time()
                if current_time - last_alive > alive_interval:
                    # self._send_alive_notification()  # Disabled
                    logging.info("Alive notification skipped (disabled)")
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