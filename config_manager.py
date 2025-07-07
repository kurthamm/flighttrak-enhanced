#!/usr/bin/env python3
"""
Centralized configuration management for FlightTrak
Loads configuration from environment variables with fallback to config.json
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration manager for FlightTrak"""
    
    def __init__(self, config_file='config.json'):
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / config_file
        self._config = self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables with JSON fallback"""
        config = {}
        
        # Try to load JSON config as fallback
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load {self.config_file}: {e}")
        
        # Override with environment variables (these take precedence)
        return {
            'flightaware_api_key': os.getenv('FLIGHTAWARE_API_KEY', 
                config.get('flightaware_config', {}).get('flightaware_api_key')),
            
            'email': {
                'sendgrid_api_key': os.getenv('SENDGRID_API_KEY',
                    config.get('email_config', {}).get('sendgrid_api_key')),
                'sender': os.getenv('EMAIL_SENDER',
                    config.get('email_config', {}).get('sender')),
                'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',') or
                    config.get('email_config', {}).get('recipients', []),
                'notification_email': os.getenv('NOTIFICATION_EMAIL',
                    config.get('email_config', {}).get('notification_email')),
            },
            
            'home': {
                'lat': float(os.getenv('HOME_LAT', 
                    config.get('home', {}).get('lat', 0))),
                'lon': float(os.getenv('HOME_LON',
                    config.get('home', {}).get('lon', 0))),
            },
            
            'monitoring': {
                'alive_interval': int(os.getenv('ALIVE_INTERVAL',
                    config.get('alive_interval', 86400))),
                'dump1090_host': os.getenv('DUMP1090_HOST', '127.0.0.1'),
                'dump1090_port': int(os.getenv('DUMP1090_PORT', 30002)),
            },
            
            'files': {
                'aircraft_list': self.base_dir / os.getenv('AIRCRAFT_LIST_FILE',
                    config.get('aircraft_file_path', 'aircraft_list.json')),
                'detected_aircraft': self.base_dir / os.getenv('DETECTED_AIRCRAFT_FILE',
                    'detected_aircraft.txt'),
                'log_file': self.base_dir / os.getenv('LOG_FILE', 'flightalert.log'),
            }
        }
    
    def get(self, key, default=None):
        """Get configuration value by key using dot notation"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def validate(self):
        """Validate required configuration values"""
        required = [
            ('flightaware_api_key', 'FlightAware API key'),
            ('email.sendgrid_api_key', 'SendGrid API key'),
            ('email.sender', 'Email sender address'),
            ('home.lat', 'Home latitude'),
            ('home.lon', 'Home longitude'),
        ]
        
        missing = []
        for key, name in required:
            if not self.get(key):
                missing.append(name)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True

# Global config instance
config = Config()