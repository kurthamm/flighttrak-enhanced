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
    
    def send_aircraft_alert(self, aircraft: Dict, tracked_info: Dict, 
                           distance: float, recipients: List[str]) -> bool:
        """Send aircraft detection alert"""
        html_content = self._generate_aircraft_alert_html(aircraft, tracked_info, distance)
        subject = f"✈️ FlightTrak Alert: {tracked_info.get('description', 'Tracked Aircraft')} Detected"
        
        return self.send_email(recipients, subject, html_content)
    
    def send_anomaly_alert(self, anomaly: Dict, recipients: List[str]) -> bool:
        """Send anomaly detection alert"""
        html_content = self._generate_anomaly_alert_html(anomaly)
        
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
    
    def _generate_aircraft_alert_html(self, aircraft: Dict, tracked_info: Dict, distance: float) -> str:
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
    
    def _generate_anomaly_alert_html(self, anomaly: Dict) -> str:
        """Generate HTML for anomaly alert"""
        aircraft = anomaly.get('aircraft', {})
        severity_colors = {
            'CRITICAL': '#ff4757',
            'HIGH': '#ff6b6b', 
            'MEDIUM': '#ffa502',
            'LOW': '#3742fa'
        }
        
        color = severity_colors.get(anomaly.get('severity', 'MEDIUM'), '#666')
        
        return f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#f4f4f4;color:#333;padding:20px;'>
            <div style='max-width:700px;margin:0 auto;background:white;padding:25px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);'>
                
                <div style='text-align:center;margin-bottom:25px;padding-bottom:15px;border-bottom:2px solid {color};'>
                    <h1 style='color:{color};margin:0;font-size:24px;'>⚠️ FlightTrak Anomaly Alert</h1>
                    <h2 style='color:#333;margin:10px 0;font-size:18px;'>{anomaly.get("type", "Unknown").replace("_", " ").title()}</h2>
                    <p style='color:{color};font-size:16px;margin:5px 0;font-weight:bold;'>Severity: {anomaly.get("severity", "MEDIUM")}</p>
                </div>
                
                <div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#333;margin:0 0 15px 0;'>Description:</h3>
                    <p style='color:#333;margin:0;'>{anomaly.get("description", "Anomaly detected")}</p>
                </div>
                
                <div style='background:#f9f9f9;padding:20px;border-radius:8px;margin:15px 0;'>
                    <h3 style='color:#333;margin:0 0 15px 0;'>Aircraft Details:</h3>
                    <table style='width:100%;border-collapse:collapse;'>
                        <tr><td style='padding:5px;font-weight:bold;'>ICAO:</td><td style='padding:5px;'>{aircraft.get('hex', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Flight:</td><td style='padding:5px;'>{aircraft.get('flight', 'N/A')}</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Altitude:</td><td style='padding:5px;'>{aircraft.get('alt_baro', 'N/A')} ft</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Speed:</td><td style='padding:5px;'>{aircraft.get('gs', 'N/A')} kt</td></tr>
                        <tr><td style='padding:5px;font-weight:bold;'>Squawk:</td><td style='padding:5px;'>{aircraft.get('squawk', 'N/A')}</td></tr>
                    </table>
                </div>
                
                <div style='text-align:center;margin:20px 0;'>
                    <a href='https://flightaware.com/live/flight/{aircraft.get("hex", "").upper()}' 
                       style='background:{color};color:white;padding:12px 25px;text-decoration:none;border-radius:5px;font-weight:bold;'>
                        Track Aircraft
                    </a>
                </div>
                
                <div style='text-align:center;margin-top:20px;padding-top:15px;border-top:1px solid #ddd;'>
                    <p style='font-size:12px;color:#666;margin:5px 0;'>
                        Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                        FlightTrak Enhanced Alert System
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