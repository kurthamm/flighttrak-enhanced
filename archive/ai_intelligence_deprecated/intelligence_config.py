#!/usr/bin/env python3
"""
Intelligence API Configuration for FlightTrak Enhanced Sources
Centralized configuration for all intelligence APIs
"""

import os
import json
import logging
from typing import Dict, Optional

class IntelligenceConfig:
    """Manages API keys and configuration for intelligence sources"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.api_keys = {}
        self.load_config()
    
    def load_config(self):
        """Load API configuration from file and environment"""
        try:
            # Load from config.json first
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                
            intelligence_config = config.get('intelligence_apis', {})
            
            # API Keys with fallback to environment variables
            self.api_keys = {
                'newsapi': intelligence_config.get('newsapi_key') or os.getenv('NEWSAPI_KEY'),
                'mapbox': intelligence_config.get('mapbox_token') or os.getenv('MAPBOX_TOKEN'),
                'here': intelligence_config.get('here_api_key') or os.getenv('HERE_API_KEY'),
                'what3words': intelligence_config.get('what3words_key') or os.getenv('WHAT3WORDS_KEY'),
                'reddit_client_id': intelligence_config.get('reddit_client_id') or os.getenv('REDDIT_CLIENT_ID'),
                'reddit_client_secret': intelligence_config.get('reddit_client_secret') or os.getenv('REDDIT_CLIENT_SECRET'),
                'broadcastify': intelligence_config.get('broadcastify_key') or os.getenv('BROADCASTIFY_KEY'),
                'aviationapi': intelligence_config.get('aviationapi_key') or os.getenv('AVIATIONAPI_KEY')
            }
            
            # Remove None values
            self.api_keys = {k: v for k, v in self.api_keys.items() if v is not None}
            
            logging.info(f"Loaded {len(self.api_keys)} intelligence API configurations")
            
        except Exception as e:
            logging.error(f"Failed to load intelligence config: {e}")
            self.api_keys = {}
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        return self.api_keys.get(service)
    
    def has_service(self, service: str) -> bool:
        """Check if service is configured"""
        return service in self.api_keys and self.api_keys[service] is not None
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get status of all intelligence services"""
        services = {
            'OpenStreetMap': True,  # Always available (free)
            'Overpass API': True,   # Always available (free)
            'Google News RSS': True,  # Always available (free)
            'NewsAPI': self.has_service('newsapi'),
            'MapBox': self.has_service('mapbox'),
            'HERE Maps': self.has_service('here'),
            'What3Words': self.has_service('what3words'),
            'Reddit API': self.has_service('reddit_client_id') and self.has_service('reddit_client_secret'),
            'Broadcastify': self.has_service('broadcastify'),
            'Aviation API': self.has_service('aviationapi')
        }
        
        return services
    
    def add_to_config(self):
        """Add intelligence API configuration to config.json"""
        try:
            # Read current config
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Add intelligence APIs section if it doesn't exist
            if 'intelligence_apis' not in config:
                config['intelligence_apis'] = {
                    "newsapi_key": "YOUR_NEWSAPI_KEY_HERE",
                    "mapbox_token": "YOUR_MAPBOX_TOKEN_HERE", 
                    "here_api_key": "YOUR_HERE_API_KEY_HERE",
                    "what3words_key": "YOUR_WHAT3WORDS_KEY_HERE",
                    "reddit_client_id": "YOUR_REDDIT_CLIENT_ID_HERE",
                    "reddit_client_secret": "YOUR_REDDIT_CLIENT_SECRET_HERE",
                    "broadcastify_key": "YOUR_BROADCASTIFY_KEY_HERE",
                    "aviationapi_key": "YOUR_AVIATIONAPI_KEY_HERE"
                }
                
                # Write back to config
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logging.info("Added intelligence APIs configuration template to config.json")
                logging.info("Please add your API keys to the intelligence_apis section")
                
        except Exception as e:
            logging.error(f"Failed to add intelligence config: {e}")

def get_signup_instructions() -> Dict[str, Dict]:
    """Get instructions for signing up for each API service"""
    return {
        'NewsAPI': {
            'url': 'https://newsapi.org/register',
            'free_tier': '500 requests/day',
            'description': 'Comprehensive news source aggregation'
        },
        'MapBox': {
            'url': 'https://account.mapbox.com/auth/signup/',
            'free_tier': '100,000 requests/month',
            'description': 'Enhanced geocoding and location intelligence'
        },
        'HERE Maps': {
            'url': 'https://developer.here.com/sign-up',
            'free_tier': '1,000 requests/day',
            'description': 'Professional geocoding and place data'
        },
        'What3Words': {
            'url': 'https://developer.what3words.com/public-api',
            'free_tier': '1,000 requests/day',
            'description': 'Precise 3-word location addresses'
        },
        'Reddit API': {
            'url': 'https://www.reddit.com/prefs/apps',
            'free_tier': '60 requests/minute',
            'description': 'Local community discussions and breaking news'
        },
        'Broadcastify': {
            'url': 'https://www.broadcastify.com/developer/',
            'free_tier': 'Varies by API',
            'description': 'Emergency scanner feeds and dispatch audio'
        }
    }

def print_setup_instructions():
    """Print setup instructions for all APIs"""
    print("\n🚀 ENHANCED INTELLIGENCE SETUP INSTRUCTIONS")
    print("=" * 60)
    
    instructions = get_signup_instructions()
    
    print("\n📋 API SERVICES TO CONFIGURE:")
    for service, info in instructions.items():
        print(f"\n{service}:")
        print(f"  🌐 Sign up: {info['url']}")
        print(f"  💰 Free tier: {info['free_tier']}")
        print(f"  📝 Description: {info['description']}")
    
    print("\n🔧 CONFIGURATION STEPS:")
    print("1. Sign up for the APIs you want (start with NewsAPI and MapBox)")
    print("2. Get your API keys from each service")
    print("3. Add them to config.json in the 'intelligence_apis' section")
    print("4. Restart the FlightTrak service")
    
    print("\n💡 RECOMMENDED PRIORITY:")
    print("1. NewsAPI (comprehensive news coverage)")
    print("2. MapBox (enhanced location data)")
    print("3. What3Words (precise location addressing)")
    print("4. Reddit API (local community intelligence)")
    print("5. HERE Maps (additional location validation)")

def main():
    """Setup and test intelligence configuration"""
    config = IntelligenceConfig()
    
    # Add configuration template to config.json
    config.add_to_config()
    
    # Show available services
    services = config.get_available_services()
    print("\n📊 INTELLIGENCE SERVICES STATUS:")
    print("-" * 40)
    
    for service, available in services.items():
        status = "✅ ACTIVE" if available else "❌ NEEDS CONFIG"
        print(f"{service:<20}: {status}")
    
    # Show setup instructions
    print_setup_instructions()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()