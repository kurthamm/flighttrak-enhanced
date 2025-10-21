#!/usr/bin/env python3
"""
Unified Email Service for FlightTrak
Handles all email communications with Gmail SMTP
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Union, Dict, Optional

# Import FlightAware lookup (optional)
try:
    from flightaware_lookup import get_flightaware_lookup
    FLIGHTAWARE_AVAILABLE = True
except ImportError:
    FLIGHTAWARE_AVAILABLE = False
    logging.debug("FlightAware lookup not available")


class EmailService:
    """Centralized email service for FlightTrak"""
    
    def __init__(self, config: Dict):
        """Initialize with email configuration"""
        self.config = config
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.sender = config.get('sender')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', True)
        
        if not self.sender or not self.password:
            raise ValueError("Email sender and password are required")
    
    def send_email(self, to_emails: Union[str, List[str]], subject: str, 
                   html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Send email via Gmail SMTP
        
        Args:
            to_emails: Single email or list of emails
            subject: Email subject
            html_content: HTML body content
            text_content: Optional plain text content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender
            msg['Subject'] = subject
            
            # Handle recipients
            if isinstance(to_emails, str):
                recipients = [to_emails]
                msg['To'] = to_emails
            else:
                recipients = to_emails
                msg['To'] = ', '.join(to_emails)
            
            # Attach content
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg, to_addrs=recipients)
            
            logging.info(f"Email sent successfully to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logging.error(f"Error sending email: {e}")
            return False
    
    def send_html_email(self, recipients: List[str], subject: str,
                        html_content: str) -> bool:
        """
        Convenience method to send HTML email

        Args:
            recipients: List of email addresses
            subject: Email subject
            html_content: HTML body content

        Returns:
            bool: True if successful, False otherwise
        """
        return self.send_email(recipients, subject, html_content)

    def send_aircraft_alert(self, aircraft: Dict, tracked_info: Dict,
                           distance: float, recipients: List[str]) -> bool:
        """Send aircraft detection alert"""
        # Lookup flight plan info if available
        flight_plan = None
        if FLIGHTAWARE_AVAILABLE:
            try:
                flightaware = get_flightaware_lookup()
                icao = aircraft.get('hex', '').upper()
                callsign = aircraft.get('flight', '').strip() if aircraft.get('flight') else None
                flight_plan = flightaware.get_flight_info_by_icao(icao, callsign)
            except Exception as e:
                logging.debug(f"Could not fetch flight plan: {e}")

        html_content = self._generate_aircraft_alert_html(aircraft, tracked_info, distance, flight_plan)
        subject = f"✈️ FlightTrak Alert: {tracked_info.get('description', 'Tracked Aircraft')} Detected"

        return self.send_email(recipients, subject, html_content)
    
    def send_anomaly_alert(self, anomaly: Dict, recipients: List[str]) -> bool:
        """Send anomaly detection alert"""
        # Lookup flight plan info if available
        flight_plan = None
        if FLIGHTAWARE_AVAILABLE:
            try:
                flightaware = get_flightaware_lookup()
                aircraft = anomaly.get('aircraft', {})
                icao = aircraft.get('hex', '').upper()
                callsign = aircraft.get('flight', '').strip() if aircraft.get('flight') else None
                flight_plan = flightaware.get_flight_info_by_icao(icao, callsign)
            except Exception as e:
                logging.debug(f"Could not fetch flight plan: {e}")

        html_content = self._generate_anomaly_alert_html(anomaly, flight_plan)
        
        severity_emoji = {
            'CRITICAL': '🚨', 
            'HIGH': '⚠️', 
            'MEDIUM': '⚡', 
            'LOW': '🔍'
        }.get(anomaly.get('severity', 'MEDIUM'), '⚠️')
        
        subject = f"{severity_emoji} FlightTrak Anomaly Alert: {anomaly.get('type', 'Unknown').replace('_', ' ').title()}"
        
        return self.send_email(recipients, subject, html_content)
    
    def send_ai_intelligence_alert(self, event_data: Dict, recipients: List[str]) -> bool:
        """Send AI intelligence alert"""
        html_content = self._generate_ai_intelligence_html(event_data)
        
        subject = f"🧠 FlightTrak AI Alert: {event_data.get('event_type', 'Unknown').replace('_', ' ').title()}"
        if event_data.get('severity'):
            subject += f" [{event_data['severity']}]"
        
        return self.send_email(recipients, subject, html_content)
    
    def send_health_alert(self, minutes_since_aircraft: float,
                         threshold_minutes: int, diagnostics: Dict,
                         recipients: List[str]) -> bool:
        """Send health monitoring alert when no aircraft detected"""
        html_content = self._generate_health_alert_html(minutes_since_aircraft, threshold_minutes, diagnostics)
        subject = f"⚠️ FlightTrak Health Alert: No Aircraft Detected for {int(minutes_since_aircraft)} Minutes"

        return self.send_email(recipients, subject, html_content)

    def send_service_notification(self, service_name: str, status: str,
                                 recipient: str, details: Optional[Dict] = None) -> bool:
        """Send service status notification"""
        html_content = self._generate_service_notification_html(service_name, status, details)

        status_emoji = {
            'started': '✅',
            'stopped': '🔴',
            'alive': '💚',
            'error': '❌'
        }.get(status.lower(), '📢')

        subject = f"{status_emoji} FlightTrak Service: {service_name} {status.title()}"

        return self.send_email(recipient, subject, html_content)
    
    def _generate_aircraft_alert_html(self, aircraft: Dict, tracked_info: Dict, distance: float, flight_plan: Optional[Dict] = None) -> str:
        """Generate HTML for aircraft alert"""
        # Get additional flight data
        icao = aircraft.get('hex', '').upper()
        tail = tracked_info.get('tail_number', 'N/A')
        lat = aircraft.get('lat', 0)
        lon = aircraft.get('lon', 0)
        heading = aircraft.get('track', 'N/A')
        vert_rate = aircraft.get('baro_rate', 0)

        # Calculate heading direction
        if isinstance(heading, (int, float)):
            directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            heading_text = f"{heading}° ({directions[int((heading + 22.5) % 360 / 45)]})"
        else:
            heading_text = 'N/A'

        # Vertical rate text
        if isinstance(vert_rate, (int, float)) and vert_rate != 0:
            vert_text = f"{'Climbing' if vert_rate > 0 else 'Descending'} at {abs(vert_rate):,} ft/min"
        else:
            vert_text = "Level flight"

        # Description with fallback
        description = tracked_info.get('description', tracked_info.get('owner', 'Tracked Aircraft'))

        # Generate flight plan HTML section if available
        flight_plan_html = ''
        if flight_plan:
            origin = flight_plan.get('origin', {})
            destination = flight_plan.get('destination', {})
            flight_plan_html = f"""
                <div style='background:#e3f2fd;padding:25px;border-radius:8px;margin:20px 0;border-left:5px solid #2196F3;'>
                    <h3 style='color:#1565c0;margin:0 0 20px 0;border-bottom:2px solid #bbdefb;padding-bottom:10px;'>✈️ Flight Plan</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>From:</td><td style='padding:8px;'><strong>{origin.get('code', 'N/A')}</strong> - {origin.get('name', 'Unknown')}<br><span style='color:#666;font-size:13px;'>{origin.get('city', '')}</span></td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>To:</td><td style='padding:8px;'><strong>{destination.get('code', 'N/A')}</strong> - {destination.get('name', 'Unknown')}<br><span style='color:#666;font-size:13px;'>{destination.get('city', '')}</span></td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Departure:</td><td style='padding:8px;'>{flight_plan.get('departure_time', 'N/A')}</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Estimated Arrival:</td><td style='padding:8px;'>{flight_plan.get('arrival_time', 'N/A')}</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Status:</td><td style='padding:8px;'><span style='color:#1565c0;font-weight:bold;'>{flight_plan.get('status', 'Unknown').upper()}</span></td></tr>
                    </table>
                </div>
            """

        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.6;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:750px;margin:0 auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.15);'>

                <div style='text-align:center;margin-bottom:30px;padding-bottom:20px;border-bottom:3px solid #4CAF50;'>
                    <h1 style='color:#4CAF50;margin:0;font-size:28px;'>✈️ FlightTrak Detection</h1>
                    <h2 style='color:#333;margin:15px 0;font-size:20px;'>{description}</h2>
                    <p style='color:#666;font-size:16px;margin:10px 0;'><strong style='font-size:24px;color:#4CAF50;'>{distance:.1f} miles</strong> from home</p>
                </div>

                <div style='background:#f9f9f9;padding:25px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4CAF50;margin:0 0 20px 0;border-bottom:2px solid #e0e0e0;padding-bottom:10px;'>Aircraft Information</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>Owner:</td><td style='padding:8px;'>{tracked_info.get('owner', 'N/A')}</td></tr>
                        <tr style='background:#fff;'><td style='padding:8px;font-weight:bold;'>Aircraft Type:</td><td style='padding:8px;'>{tracked_info.get('model', 'N/A')}</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Registration:</td><td style='padding:8px;font-family:monospace;'>{tail}</td></tr>
                        <tr style='background:#fff;'><td style='padding:8px;font-weight:bold;'>ICAO Hex:</td><td style='padding:8px;font-family:monospace;'>{icao}</td></tr>
                    </table>
                </div>

                <div style='background:#e8f5e9;padding:25px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#2e7d32;margin:0 0 20px 0;border-bottom:2px solid #c8e6c9;padding-bottom:10px;'>Current Flight Status</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>Callsign:</td><td style='padding:8px;font-family:monospace;'>{aircraft.get('flight', 'N/A').strip() if aircraft.get('flight') else 'N/A'}</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Altitude:</td><td style='padding:8px;'>{aircraft.get('alt_baro', 'N/A'):,} ft</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Ground Speed:</td><td style='padding:8px;'>{aircraft.get('gs', 'N/A')} knots</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Heading:</td><td style='padding:8px;'>{heading_text}</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Vertical Rate:</td><td style='padding:8px;'>{vert_text}</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Squawk:</td><td style='padding:8px;font-family:monospace;'>{aircraft.get('squawk', 'N/A')}</td></tr>
                    </table>
                </div>

                {flight_plan_html}

                <div style='text-align:center;margin:25px 0;'>
                    <h3 style='color:#666;margin:0 0 15px 0;font-size:16px;'>Track This Flight:</h3>
                    <div style='display:inline-block;'>
                        <a href='https://www.flightaware.com/live/flight/{icao}'
                           style='display:inline-block;background:#0066CC;color:white;padding:12px 20px;text-decoration:none;border-radius:6px;font-weight:bold;margin:5px;'>
                            FlightAware
                        </a>
                        <a href='https://globe.adsbexchange.com/?icao={icao}'
                           style='display:inline-block;background:#FF6B35;color:white;padding:12px 20px;text-decoration:none;border-radius:6px;font-weight:bold;margin:5px;'>
                            ADS-B Exchange
                        </a>
                        <a href='https://www.flightradar24.com/data/aircraft/{tail.lower()}'
                           style='display:inline-block;background:#FFD500;color:#333;padding:12px 20px;text-decoration:none;border-radius:6px;font-weight:bold;margin:5px;'>
                            Flightradar24
                        </a>
                    </div>
                </div>

                <div style='text-align:center;margin:20px 0;'>
                    <a href='https://www.google.com/maps?q={lat},{lon}'
                       style='display:inline-block;background:#4CAF50;color:white;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;'>
                        📍 View Location on Map
                    </a>
                </div>

                <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:2px solid #e0e0e0;'>
                    <p style='font-size:13px;color:#999;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}<br>
                        <strong>FlightTrak Detection System</strong> • {lat:.4f}, {lon:.4f}
                    </p>
                </div>
            </div>
        </body></html>
        """
    
    def _generate_anomaly_alert_html(self, anomaly: Dict, flight_plan: Optional[Dict] = None) -> str:
        """Generate HTML for anomaly alert"""
        aircraft = anomaly.get('aircraft', {})
        severity_colors = {
            'CRITICAL': '#ff4757',
            'HIGH': '#ff6b6b',
            'MEDIUM': '#ffa502',
            'LOW': '#3742fa'
        }

        color = severity_colors.get(anomaly.get('severity', 'MEDIUM'), '#666')

        # Extract aircraft data
        icao = aircraft.get('hex', '').upper()
        flight = aircraft.get('flight', '').strip() if aircraft.get('flight') else ''
        lat = aircraft.get('lat')
        lon = aircraft.get('lon')
        altitude = aircraft.get('alt_baro', 'N/A')
        speed = aircraft.get('gs', 'N/A')
        squawk = aircraft.get('squawk', 'N/A')
        heading = aircraft.get('track', 'N/A')
        vert_rate = aircraft.get('baro_rate', 0)

        # Calculate heading direction
        if isinstance(heading, (int, float)):
            directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
            heading_text = f"{heading}° ({directions[int((heading + 22.5) % 360 / 45)]})"
        else:
            heading_text = 'N/A'

        # Vertical rate text
        if isinstance(vert_rate, (int, float)) and vert_rate != 0:
            vert_text = f"{'Climbing' if vert_rate > 0 else 'Descending'} at {abs(vert_rate):,} ft/min"
        else:
            vert_text = "Level flight"

        # Location display
        location_text = 'Unknown'
        if lat is not None and lon is not None:
            location_text = f"{lat:.4f}, {lon:.4f}"

        # Distance from home (if available)
        distance_text = ''
        if lat is not None and lon is not None:
            try:
                from utils import haversine_distance
                from config_manager import config
                home_lat, home_lon = config.get_home_coordinates()
                distance = haversine_distance(home_lat, home_lon, lat, lon)
                distance_text = f"<tr><td style='padding:8px;font-weight:bold;'>Distance from Home:</td><td style='padding:8px;'>{distance:.1f} miles</td></tr>"
            except:
                pass

        # Generate flight plan HTML section if available
        flight_plan_html = ''
        if flight_plan:
            origin = flight_plan.get('origin', {})
            destination = flight_plan.get('destination', {})
            flight_plan_html = f"""
                <div style='background:#e3f2fd;padding:25px;border-radius:8px;margin:20px 0;border-left:5px solid #2196F3;'>
                    <h3 style='color:#1565c0;margin:0 0 20px 0;border-bottom:2px solid #bbdefb;padding-bottom:10px;'>✈️ Flight Plan</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>From:</td><td style='padding:8px;'><strong>{origin.get('code', 'N/A')}</strong> - {origin.get('name', 'Unknown')}<br><span style='color:#666;font-size:13px;'>{origin.get('city', '')}</span></td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>To:</td><td style='padding:8px;'><strong>{destination.get('code', 'N/A')}</strong> - {destination.get('name', 'Unknown')}<br><span style='color:#666;font-size:13px;'>{destination.get('city', '')}</span></td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Departure:</td><td style='padding:8px;'>{flight_plan.get('departure_time', 'N/A')}</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Estimated Arrival:</td><td style='padding:8px;'>{flight_plan.get('arrival_time', 'N/A')}</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Status:</td><td style='padding:8px;'><span style='color:#1565c0;font-weight:bold;'>{flight_plan.get('status', 'Unknown').upper()}</span></td></tr>
                    </table>
                </div>
            """

        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.6;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:750px;margin:0 auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.15);'>

                <div style='text-align:center;margin-bottom:30px;padding-bottom:20px;border-bottom:3px solid {color};'>
                    <h1 style='color:{color};margin:0;font-size:28px;'>🚨 FlightTrak Emergency Alert</h1>
                    <h2 style='color:#333;margin:15px 0;font-size:20px;'>{anomaly.get("type", "Unknown").replace("_", " ").title()}</h2>
                    <p style='color:{color};font-size:18px;margin:5px 0;font-weight:bold;'>Severity: {anomaly.get("severity", "MEDIUM")}</p>
                </div>

                <div style='background:#ffebee;padding:25px;border-left:5px solid {color};border-radius:8px;margin:20px 0;'>
                    <h3 style='color:{color};margin:0 0 15px 0;font-size:18px;'>Emergency Description</h3>
                    <p style='color:#333;margin:0;font-size:16px;line-height:1.8;'>{anomaly.get("description", "Anomaly detected")}</p>
                </div>

                <div style='background:#f9f9f9;padding:25px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#333;margin:0 0 20px 0;border-bottom:2px solid #e0e0e0;padding-bottom:10px;'>Aircraft Information</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>ICAO Hex:</td><td style='padding:8px;font-family:monospace;'>{icao}</td></tr>
                        <tr style='background:#fff;'><td style='padding:8px;font-weight:bold;'>Callsign:</td><td style='padding:8px;font-family:monospace;font-size:16px;font-weight:bold;'>{flight if flight else 'N/A'}</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Squawk Code:</td><td style='padding:8px;font-family:monospace;font-size:16px;color:{color};font-weight:bold;'>{squawk}</td></tr>
                        <tr style='background:#fff;'><td style='padding:8px;font-weight:bold;'>Location:</td><td style='padding:8px;'>{location_text}</td></tr>
                        {distance_text}
                    </table>
                </div>

                <div style='background:#e8f5e9;padding:25px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#2e7d32;margin:0 0 20px 0;border-bottom:2px solid #c8e6c9;padding-bottom:10px;'>Flight Status</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:8px;font-weight:bold;width:40%;'>Altitude:</td><td style='padding:8px;'>{altitude:,} ft</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Ground Speed:</td><td style='padding:8px;'>{speed} knots</td></tr>
                        <tr><td style='padding:8px;font-weight:bold;'>Heading:</td><td style='padding:8px;'>{heading_text}</td></tr>
                        <tr style='background:rgba(255,255,255,0.5);'><td style='padding:8px;font-weight:bold;'>Vertical Rate:</td><td style='padding:8px;'>{vert_text}</td></tr>
                    </table>
                </div>

                {flight_plan_html}

                <div style='text-align:center;margin:25px 0;'>
                    <h3 style='color:#666;margin:0 0 15px 0;font-size:16px;'>Track This Emergency:</h3>
                    <div style='display:inline-block;'>
                        <a href='https://www.flightaware.com/live/flight/{flight if flight else icao}'
                           style='display:inline-block;background:#0066CC;color:white;padding:12px 20px;text-decoration:none;border-radius:6px;font-weight:bold;margin:5px;'>
                            FlightAware
                        </a>
                        <a href='https://globe.adsbexchange.com/?icao={icao.lower()}'
                           style='display:inline-block;background:#FF6B35;color:white;padding:12px 20px;text-decoration:none;border-radius:6px;font-weight:bold;margin:5px;'>
                            ADS-B Exchange
                        </a>
                    </div>
                </div>

                {f'''
                <div style='text-align:center;margin:20px 0;'>
                    <a href='https://www.google.com/maps?q={lat},{lon}'
                       style='display:inline-block;background:#4CAF50;color:white;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;'>
                        📍 View Location on Map
                    </a>
                </div>
                ''' if lat is not None and lon is not None else ''}

                <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:2px solid #e0e0e0;'>
                    <p style='font-size:13px;color:#999;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}<br>
                        <strong>FlightTrak Emergency Detection System</strong>
                    </p>
                </div>
            </div>
        </body></html>
        """
    
    def _generate_ai_intelligence_html(self, event_data: Dict) -> str:
        """Generate HTML for AI intelligence alert"""
        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
            <div style='max-width:700px;margin:0 auto;background:#1a1f3a;padding:25px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.3);'>
                
                <div style='text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid #4fc3f7;'>
                    <h1 style='color:#4fc3f7;margin:0;font-size:24px;'>🧠 FlightTrak AI Intelligence Alert</h1>
                    <h2 style='color:#feca57;margin:10px 0;font-size:18px;'>{event_data.get("event_type", "Unknown").replace("_", " ").title()}</h2>
                </div>
                
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>Event Details:</h3>
                    <table style='width:100%;border-collapse:collapse;color:#e0e6ed;'>
                        <tr><td style='padding:5px;font-weight:bold;'>Event Type:</td><td style='padding:5px;'>{event_data.get('event_type', 'Unknown').replace('_', ' ').title()}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Confidence:</td><td style='padding:5px;'>{event_data.get('confidence', 0):.1%}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Severity:</td><td style='padding:5px;'>{event_data.get('severity', 'Unknown')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Aircraft Count:</td><td style='padding:5px;'>{len(event_data.get('aircraft_involved', []))}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Location:</td><td style='padding:5px;'>{event_data.get('location', 'Unknown')}</td></tr>
                    </table>
                </div>
                
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>Analysis:</h3>
                    <p style='color:#e0e6ed;margin:0;'>{event_data.get('description', 'AI analysis detected unusual flight patterns or behavior.')}</p>
                </div>
                
                <div style='text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #4fc3f7;'>
                    <p style='font-size:12px;color:#8892b0;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        FlightTrak AI Intelligence System
                    </p>
                </div>
            </div>
        </body></html>
        """
    
    def _generate_health_alert_html(self, minutes_since_aircraft: float, threshold_minutes: int, diagnostics: Dict) -> str:
        """Generate HTML for health monitoring alert with diagnostic results"""
        hours = int(minutes_since_aircraft // 60)
        mins = int(minutes_since_aircraft % 60)

        if hours > 0:
            time_display = f"{hours} hour{'s' if hours != 1 else ''} and {mins} minute{'s' if mins != 1 else ''}"
        else:
            time_display = f"{mins} minute{'s' if mins != 1 else ''}"

        # Generate diagnostic results HTML
        def get_status_icon(status):
            if status == 'ok':
                return '✅'
            elif status == 'warning':
                return '⚠️'
            elif status == 'failed':
                return '❌'
            elif status == 'skipped':
                return '⏭️'
            else:
                return '❓'

        def get_status_color(status):
            if status == 'ok':
                return '#4CAF50'
            elif status == 'warning':
                return '#ff9800'
            elif status == 'failed':
                return '#f44336'
            else:
                return '#757575'

        diagnostic_rows = []
        root_cause = None
        recommended_action = None

        # Analyze diagnostics to determine root cause
        check_names = {
            'network': 'Internet Connectivity',
            'planes_url': 'planes.hamm.me Status',
            'dump1090_service': 'dump1090 Service',
            'dump1090_port': 'ADS-B Receiver Port'
        }

        for check_key, check_name in check_names.items():
            if check_key in diagnostics:
                result = diagnostics[check_key]
                status = result['status']
                details = result['details']
                icon = get_status_icon(status)
                color = get_status_color(status)

                diagnostic_rows.append(f"""
                    <tr>
                        <td style='padding:10px;border-bottom:1px solid #e0e0e0;font-weight:bold;'>{icon} {check_name}</td>
                        <td style='padding:10px;border-bottom:1px solid #e0e0e0;color:{color};font-weight:bold;'>{status.upper()}</td>
                        <td style='padding:10px;border-bottom:1px solid #e0e0e0;'>{details}</td>
                    </tr>
                """)

                # Determine root cause
                if status == 'failed' and not root_cause:
                    if check_key == 'network':
                        root_cause = 'No internet connectivity'
                        recommended_action = 'Check your network connection and router'
                    elif check_key == 'planes_url':
                        root_cause = 'Cannot reach planes.hamm.me'
                        recommended_action = 'Check Cloudflare tunnel status or dump1090 on remote server'
                    elif check_key == 'dump1090_service':
                        root_cause = 'dump1090 service is not running'
                        recommended_action = 'Run: <code style="background:#fff;padding:2px 6px;border-radius:3px;">sudo systemctl start dump1090</code>'
                    elif check_key == 'dump1090_port':
                        root_cause = 'ADS-B receiver is not responding'
                        recommended_action = 'Check receiver hardware (antenna, SDR dongle, USB connection)'
                elif status == 'warning' and check_key == 'planes_url' and not root_cause:
                    root_cause = 'dump1090 is running but receiving no aircraft data'
                    recommended_action = 'Check ADS-B receiver antenna connection and positioning'

        diagnostic_table = ''.join(diagnostic_rows)

        # Root cause section
        root_cause_html = ''
        if root_cause:
            root_cause_html = f"""
                <div style='background:#ffebee;padding:25px;border-left:5px solid #f44336;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#c62828;margin:0 0 15px 0;font-size:18px;'>🔍 Root Cause Identified</h3>
                    <p style='color:#333;margin:0 0 15px 0;font-size:16px;font-weight:bold;'>
                        {root_cause}
                    </p>
                    <p style='color:#333;margin:0;font-size:14px;'>
                        <strong>Recommended Action:</strong><br>
                        {recommended_action}
                    </p>
                </div>
            """
        else:
            root_cause_html = """
                <div style='background:#fff9c4;padding:20px;border-left:5px solid #fbc02d;border-radius:8px;margin:20px 0;'>
                    <p style='color:#f57f17;margin:0;font-size:14px;'>
                        ⚠️ All systems appear normal, but no aircraft are being detected. This may indicate a hardware issue with the ADS-B receiver or antenna.
                    </p>
                </div>
            """

        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.6;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:800px;margin:0 auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.15);'>

                <div style='text-align:center;margin-bottom:30px;padding-bottom:20px;border-bottom:3px solid #ff9800;'>
                    <h1 style='color:#ff9800;margin:0;font-size:28px;'>⚠️ FlightTrak Health Alert</h1>
                    <h2 style='color:#333;margin:15px 0;font-size:20px;'>System Issue Detected</h2>
                </div>

                <div style='background:#fff3e0;padding:25px;border-left:5px solid #ff9800;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#e65100;margin:0 0 15px 0;font-size:18px;'>⚠️ No Aircraft Detected</h3>
                    <p style='color:#333;margin:0;font-size:16px;line-height:1.8;'>
                        The FlightTrak monitoring system has <strong>not detected any aircraft</strong> for:
                    </p>
                    <p style='color:#e65100;font-size:24px;font-weight:bold;margin:15px 0;text-align:center;'>
                        {time_display}
                    </p>
                    <p style='color:#666;margin:10px 0;font-size:14px;'>
                        Alert Threshold: {threshold_minutes} minutes
                    </p>
                </div>

                {root_cause_html}

                <div style='background:#f9f9f9;padding:25px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#333;margin:0 0 20px 0;font-size:18px;'>🔧 Diagnostic Results</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <thead>
                            <tr style='background:#e0e0e0;'>
                                <th style='padding:10px;text-align:left;'>Component</th>
                                <th style='padding:10px;text-align:left;'>Status</th>
                                <th style='padding:10px;text-align:left;'>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {diagnostic_table}
                        </tbody>
                    </table>
                </div>

                <div style='text-align:center;margin:25px 0;padding:20px;background:#e3f2fd;border-radius:8px;'>
                    <p style='color:#1565c0;font-size:14px;margin:0;'>
                        ℹ️ <strong>Note:</strong> This alert will not repeat for 4 hours to prevent spam.<br>
                        The system will continue monitoring and send another alert if the issue persists.
                    </p>
                </div>

                <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:2px solid #e0e0e0;'>
                    <p style='font-size:13px;color:#999;margin:5px 0;'>
                        Alert Time: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}<br>
                        <strong>FlightTrak Automated Diagnostics System</strong>
                    </p>
                </div>
            </div>
        </body></html>
        """

    def _generate_service_notification_html(self, service_name: str, status: str, details: Optional[Dict] = None) -> str:
        """Generate HTML for service notification"""
        status_colors = {
            'started': '#4CAF50',
            'stopped': '#f44336',
            'alive': '#2196F3',
            'error': '#FF5722'
        }

        color = status_colors.get(status.lower(), '#666')

        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:600px;margin:0 auto;background:white;padding:25px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);'>

                <div style='text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid {color};'>
                    <h1 style='color:{color};margin:0;font-size:24px;'>📢 FlightTrak Service Notification</h1>
                    <h2 style='color:#333;margin:10px 0;font-size:18px;'>{service_name} {status.title()}</h2>
                </div>

                <div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:15px 0;'>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:5px;font-weight:bold;'>Service:</td><td style='padding:5px;'>{service_name}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Status:</td><td style='padding:5px;'>{status.title()}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Time:</td><td style='padding:5px;'>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    </table>
                </div>

                <div style='text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #ddd;'>
                    <p style='font-size:12px;color:#666;margin:5px 0;'>
                        FlightTrak Enhanced Alert System
                    </p>
                </div>
            </div>
        </body></html>
        """