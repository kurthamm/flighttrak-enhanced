#!/usr/bin/env python3
"""
Centralized configuration management for FlightTrak
Loads configuration from environment variables with fallback to config.json
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class FlightTrakConfig:
    """Unified configuration manager for FlightTrak"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / config_file
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file and environment variables"""
        config = {}
        
        # Load JSON config as base
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                logging.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logging.warning(f"Could not load {self.config_file}: {e}")
        
        # Build unified configuration structure
        return {
            # FlightAware API
            'flightaware_api_key': os.getenv('FLIGHTAWARE_API_KEY', 
                config.get('flightaware_config', {}).get('flightaware_api_key')),
            
            # Email configuration (now using Gmail SMTP)
            'email': {
                'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 
                    config.get('email_config', {}).get('smtp_server', 'smtp.gmail.com')),
                'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', 
                    config.get('email_config', {}).get('smtp_port', 587))),
                'sender': os.getenv('EMAIL_SENDER',
                    config.get('email_config', {}).get('sender')),
                'password': os.getenv('EMAIL_PASSWORD',
                    config.get('email_config', {}).get('password')),
                'use_tls': os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
                'notification_email': os.getenv('NOTIFICATION_EMAIL',
                    config.get('email_config', {}).get('notification_email')),
            },
            
            # Home location
            'home': {
                'lat': float(os.getenv('HOME_LAT', 
                    config.get('home', {}).get('lat', 0))),
                'lon': float(os.getenv('HOME_LON',
                    config.get('home', {}).get('lon', 0))),
            },
            
            # Alert configuration
            'alerts': {
                'tracked_aircraft': {
                    'enabled': os.getenv('ALERTS_TRACKED_ENABLED', 'true').lower() == 'true',
                    'recipients': self._parse_recipients(os.getenv('ALERTS_TRACKED_RECIPIENTS', 
                        config.get('alert_config', {}).get('tracked_aircraft_alerts', {}).get('recipients', [])))
                },
                'ai_intelligence': {
                    'enabled': os.getenv('ALERTS_AI_ENABLED', 'true').lower() == 'true',
                    'recipients': self._parse_recipients(os.getenv('ALERTS_AI_RECIPIENTS',
                        config.get('alert_config', {}).get('ai_intelligence_alerts', {}).get('recipients', []))),
                    'min_confidence': float(os.getenv('ALERTS_AI_MIN_CONFIDENCE',
                        config.get('alert_config', {}).get('ai_intelligence_alerts', {}).get('min_confidence', 0.6)))
                },
                'anomaly': {
                    'enabled': os.getenv('ALERTS_ANOMALY_ENABLED', 'true').lower() == 'true',
                    'recipients': self._parse_recipients(os.getenv('ALERTS_ANOMALY_RECIPIENTS',
                        config.get('alert_config', {}).get('anomaly_alerts', {}).get('recipients', [])))
                }
            },
            
            # Monitoring settings
            'monitoring': {
                'alive_interval': int(os.getenv('ALIVE_INTERVAL',
                    config.get('alive_interval', 86400))),
                'dump1090_host': os.getenv('DUMP1090_HOST', '127.0.0.1'),
                'dump1090_port': int(os.getenv('DUMP1090_PORT', 30002)),
                'planes_url': os.getenv('PLANES_URL', 'https://planes.hamm.me/data/aircraft.json'),
                'check_interval': int(os.getenv('CHECK_INTERVAL', 15)),
            },
            
            # Intelligence APIs
            'intelligence': {
                'claude_api_key': os.getenv('CLAUDE_API_KEY',
                    config.get('claude_api_key')),
                'newsapi_key': os.getenv('NEWSAPI_KEY',
                    config.get('intelligence_apis', {}).get('newsapi_key')),
                'mapbox_token': os.getenv('MAPBOX_TOKEN',
                    config.get('intelligence_apis', {}).get('mapbox_token')),
                'here_api_key': os.getenv('HERE_API_KEY',
                    config.get('intelligence_apis', {}).get('here_api_key')),
                'what3words_key': os.getenv('WHAT3WORDS_KEY',
                    config.get('intelligence_apis', {}).get('what3words_key')),
                'reddit_client_id': os.getenv('REDDIT_CLIENT_ID',
                    config.get('intelligence_apis', {}).get('reddit_client_id')),
                'reddit_client_secret': os.getenv('REDDIT_CLIENT_SECRET',
                    config.get('intelligence_apis', {}).get('reddit_client_secret')),
                'broadcastify_key': os.getenv('BROADCASTIFY_KEY',
                    config.get('intelligence_apis', {}).get('broadcastify_key')),
                'aviationapi_key': os.getenv('AVIATIONAPI_KEY',
                    config.get('intelligence_apis', {}).get('aviationapi_key')),
            },
            
            # File paths
            'files': {
                'aircraft_list': self.base_dir / os.getenv('AIRCRAFT_LIST_FILE',
                    config.get('aircraft_file_path', 'aircraft_list.json')),
                'detected_aircraft': self.base_dir / os.getenv('DETECTED_AIRCRAFT_FILE',
                    'detected_aircraft.txt'),
                'log_file': self.base_dir / os.getenv('LOG_FILE', 'flightalert.log'),
                'intelligence_db': self.base_dir / os.getenv('INTELLIGENCE_DB_FILE',
                    'intelligence.db'),
                'contextual_db': self.base_dir / os.getenv('CONTEXTUAL_DB_FILE',
                    'contextual_intelligence.db'),
            },
            
            # Dashboard settings
            'dashboard': {
                'port': int(os.getenv('DASHBOARD_PORT', 5030)),
                'host': os.getenv('DASHBOARD_HOST', '0.0.0.0'),
                'debug': os.getenv('DASHBOARD_DEBUG', 'false').lower() == 'true',
            }
        }
    
    def _parse_recipients(self, recipients: Any) -> List[str]:
        """Parse recipients from various formats"""
        if isinstance(recipients, str):
            return [r.strip() for r in recipients.split(',') if r.strip()]
        elif isinstance(recipients, list):
            return recipients
        return []
    
    def _validate_config(self) -> None:
        """Validate critical configuration values"""
        required_fields = [
            ('home.lat', 'Home latitude'),
            ('home.lon', 'Home longitude'),
            ('email.sender', 'Email sender address'),
            ('email.password', 'Email password'),
        ]
        
        missing = []
        for field, description in required_fields:
            if not self.get(field):
                missing.append(description)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        # Validate coordinates
        lat, lon = self.get('home.lat'), self.get('home.lon')
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError("Invalid home coordinates")
        
        logging.info("Configuration validation passed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key using dot notation"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration for EmailService"""
        return self.get('email', {})
    
    def get_home_coordinates(self) -> tuple[float, float]:
        """Get home coordinates as tuple"""
        return self.get('home.lat'), self.get('home.lon')
    
    def get_alert_recipients(self, alert_type: str) -> List[str]:
        """Get recipients for specific alert type"""
        return self.get(f'alerts.{alert_type}.recipients', [])
    
    def is_alert_enabled(self, alert_type: str) -> bool:
        """Check if alert type is enabled"""
        return self.get(f'alerts.{alert_type}.enabled', False)
    
    def get_intelligence_apis(self) -> Dict[str, str]:
        """Get intelligence API configuration"""
        return self.get('intelligence', {})
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._config = self._load_config()
        self._validate_config()
        logging.info("Configuration reloaded")
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """Save current configuration to file"""
        try:
            save_path = file_path or self.config_file
            with open(save_path, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)
            logging.info(f"Configuration saved to {save_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def __repr__(self) -> str:
        """String representation of config"""
        return f"FlightTrakConfig(file={self.config_file})"


# Global config instance
config = FlightTrakConfig()