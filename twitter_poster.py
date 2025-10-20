#!/usr/bin/env python3
"""
Twitter/X posting module for FlightTrak
Posts interesting aircraft detections with appropriate delays and filters
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque

try:
    import tweepy
    TWITTER_AVAILABLE = True
except ImportError:
    TWITTER_AVAILABLE = False
    logging.warning("tweepy not installed - Twitter posting disabled")

from config_manager import config


class TwitterPoster:
    """Handles posting aircraft detections to Twitter/X"""

    # Aircraft categories and their posting rules
    AIRCRAFT_CATEGORIES = {
        'historic': {
            'delay_hours': 0,  # Post immediately
            'include_location': 'vague',  # "Over South Carolina"
            'include_exact_data': True,
            'examples': ['N529B', 'N494DF']  # B-29 FIFI, Ford Trimotor
        },
        'military_vip': {
            'delay_hours': 0,  # Post immediately (already public)
            'include_location': 'vague',
            'include_exact_data': True,
            'examples': ['ADFDF8', 'ADFDF9']  # Air Force One
        },
        'celebrity': {
            'delay_hours': 24,  # 24-hour delay for privacy
            'include_location': 'vague',
            'include_exact_data': False,  # No exact coords
            'examples': ['A47CB5', 'A835AF', 'A4AEB6']  # Taylor Swift, Elon Musk
        },
        'government': {
            'delay_hours': 2,  # Short delay
            'include_location': 'vague',
            'include_exact_data': False
        },
        'skip': {
            'delay_hours': None,
            'include_location': None,
            'include_exact_data': False,
            'examples': []  # Don't post these
        }
    }

    def __init__(self):
        self.enabled = False
        self.dry_run = True  # Safety: default to dry-run mode
        self.client = None
        self.post_queue = deque()  # Queue for delayed posts

        # Load configuration
        twitter_config = config.get('twitter', {})
        self.enabled = twitter_config.get('enabled', False)
        self.dry_run = twitter_config.get('dry_run', True)

        # Aircraft classifications
        self.aircraft_classifications = self._load_aircraft_classifications()

        # Initialize Twitter API if available and enabled
        if TWITTER_AVAILABLE and self.enabled:
            self._init_twitter_api(twitter_config)

        logging.info(f"Twitter poster initialized (enabled={self.enabled}, dry_run={self.dry_run})")

    def _init_twitter_api(self, twitter_config: Dict) -> None:
        """Initialize Twitter API v2 client"""
        try:
            api_key = twitter_config.get('api_key')
            api_secret = twitter_config.get('api_secret')
            access_token = twitter_config.get('access_token')
            access_secret = twitter_config.get('access_secret')
            bearer_token = twitter_config.get('bearer_token')

            if not all([api_key, api_secret, access_token, access_secret]):
                logging.warning("Twitter API credentials incomplete - posting disabled")
                self.enabled = False
                return

            # Initialize Twitter API v2 client
            self.client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret
            )

            logging.info("Twitter API initialized successfully")

        except Exception as e:
            logging.error(f"Failed to initialize Twitter API: {e}")
            self.enabled = False

    def _load_aircraft_classifications(self) -> Dict:
        """Load aircraft classifications from config or aircraft_list.json"""
        classifications = {}

        try:
            # Load aircraft list
            aircraft_file = config.get('files.aircraft_list', 'aircraft_list.json')
            with open(aircraft_file, 'r') as f:
                data = json.load(f)

            aircraft_list = data.get('aircraft_to_detect', [])

            for aircraft in aircraft_list:
                icao = aircraft.get('icao', '').upper()
                owner = aircraft.get('owner', '').lower()
                description = aircraft.get('description', '').lower()
                model = aircraft.get('model', '').lower()

                # Classify aircraft based on owner/description
                if 'fifi' in description or 'b-29' in model or 'trimotor' in model:
                    classifications[icao] = 'historic'
                elif 'air force one' in owner or 'marine one' in owner:
                    classifications[icao] = 'military_vip'
                elif any(celeb in owner.lower() for celeb in ['swift', 'musk', 'bezos', 'kardashian', 'drake', 'trump', 'gates']):
                    classifications[icao] = 'celebrity'
                elif 'government' in owner or 'u.s. ' in owner:
                    classifications[icao] = 'government'
                else:
                    classifications[icao] = 'skip'  # Don't post by default

            logging.info(f"Classified {len(classifications)} aircraft for Twitter posting")

        except Exception as e:
            logging.error(f"Failed to load aircraft classifications: {e}")

        return classifications

    def should_post_aircraft(self, icao: str, category: str) -> bool:
        """Determine if an aircraft should be posted to Twitter"""
        if not self.enabled:
            return False

        if category == 'skip':
            return False

        # Historic and military VIP: always post (immediately)
        if category in ['historic', 'military_vip']:
            return True

        # Celebrity: post with delay
        if category == 'celebrity':
            return True

        return False

    def queue_post(self, aircraft: Dict, tracked_info: Dict, distance: float) -> None:
        """Queue an aircraft detection for Twitter posting"""
        if not self.enabled:
            return

        icao = aircraft.get('hex', '').upper()
        category = self.aircraft_classifications.get(icao, 'skip')

        if not self.should_post_aircraft(icao, category):
            logging.debug(f"Skipping Twitter post for {icao} (category: {category})")
            return

        # Get posting rules for this category
        rules = self.AIRCRAFT_CATEGORIES.get(category, {})
        delay_hours = rules.get('delay_hours', 24)

        # Calculate post time
        post_time = time.time()
        if delay_hours > 0:
            post_time += (delay_hours * 3600)

        # Create post data
        post_data = {
            'post_time': post_time,
            'aircraft': aircraft,
            'tracked_info': tracked_info,
            'distance': distance,
            'category': category,
            'detection_time': time.time()
        }

        # Add to queue
        self.post_queue.append(post_data)

        delay_text = f"in {delay_hours}h" if delay_hours > 0 else "immediately"
        logging.info(f"Queued Twitter post for {tracked_info.get('owner', 'Unknown')} ({icao}) - posting {delay_text}")

    def process_queue(self) -> None:
        """Process queued posts and post when delay has elapsed"""
        if not self.enabled or not self.post_queue:
            return

        current_time = time.time()
        posts_to_remove = []

        for post_data in self.post_queue:
            if current_time >= post_data['post_time']:
                # Time to post!
                success = self._create_and_post_tweet(post_data)
                if success:
                    posts_to_remove.append(post_data)

        # Remove posted items from queue
        for post_data in posts_to_remove:
            self.post_queue.remove(post_data)

    def _create_and_post_tweet(self, post_data: Dict) -> bool:
        """Create tweet content and post it"""
        try:
            aircraft = post_data['aircraft']
            tracked_info = post_data['tracked_info']
            distance = post_data['distance']
            category = post_data['category']
            detection_time = post_data.get('detection_time', time.time())

            # Generate tweet content based on category
            tweet_text = self._generate_tweet_text(aircraft, tracked_info, distance, category, detection_time)

            if self.dry_run:
                logging.info(f"[DRY RUN] Would post tweet:\n{tweet_text}")
                return True

            # Post to Twitter
            response = self.client.create_tweet(text=tweet_text)
            logging.info(f"Posted tweet for {tracked_info.get('owner')} - ID: {response.data['id']}")
            return True

        except Exception as e:
            logging.error(f"Failed to post tweet: {e}")
            return False

    def _generate_tweet_text(self, aircraft: Dict, tracked_info: Dict, distance: float, category: str, detection_time: float = None) -> str:
        """Generate tweet text based on aircraft category"""

        icao = aircraft.get('hex', '').upper()
        tail = tracked_info.get('tail_number', 'N/A')
        model = tracked_info.get('model', 'Unknown')
        owner = tracked_info.get('owner', 'Unknown')
        description = tracked_info.get('description', '')

        alt = aircraft.get('alt_baro', 'N/A')
        speed = aircraft.get('gs', 'N/A')

        # Get location (vague for privacy)
        location = self._get_vague_location()

        # Format based on category
        if category == 'historic':
            tweet = f"✈️ {owner} spotted!\n"
            tweet += f"Reg: {tail} | Type: {model}\n"
            tweet += f"Alt: {alt:,}ft | Speed: {speed}kt\n"
            if description:
                tweet += f"{description}\n"
            tweet += f"Location: {location}\n"
            tweet += f"#avgeek #warbird #aviation"

        elif category == 'military_vip':
            tweet = f"🇺🇸 {owner} detected\n"
            tweet += f"ICAO: {icao} | Tail: {tail}\n"
            tweet += f"Alt: {alt:,}ft | Speed: {speed}kt\n"
            tweet += f"Location: {location}\n"
            tweet += f"#AirForceOne #POTUS #aviation" if 'air force' in owner.lower() else "#military #aviation"

        elif category == 'celebrity':
            # 24-hour delayed post, less specific
            detect_dt = datetime.fromtimestamp(detection_time) if detection_time else datetime.now()
            tweet = f"✈️ {owner}'s {model} was in the {location} area\n"
            tweet += f"Reg: {tail}\n"
            tweet += f"Detected: {detect_dt.strftime('%B %d, %Y')}\n"
            tweet += f"#avgeek #aviation"

        else:
            # Generic format
            tweet = f"✈️ {model} spotted\n"
            tweet += f"Reg: {tail} | Owner: {owner}\n"
            tweet += f"Alt: {alt:,}ft | Speed: {speed}kt\n"
            tweet += f"#avgeek #aviation #planespotting"

        # Ensure tweet is under 280 characters
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."

        return tweet

    def _get_vague_location(self) -> str:
        """Get vague location description for privacy"""
        # Based on home coordinates in config
        lat, lon = config.get_home_coordinates()

        # Simple location descriptions (expand as needed)
        if 33 < lat < 36 and -82 < lon < -79:
            return "South Carolina"
        elif 36 < lat < 37 and -82 < lon < -79:
            return "North Carolina"
        else:
            return "the area"

    def post_immediate(self, aircraft: Dict, tracked_info: Dict, distance: float) -> None:
        """Post immediately (for historic/military aircraft)"""
        icao = aircraft.get('hex', '').upper()
        category = self.aircraft_classifications.get(icao, 'skip')

        if category not in ['historic', 'military_vip']:
            return

        post_data = {
            'post_time': time.time(),
            'aircraft': aircraft,
            'tracked_info': tracked_info,
            'distance': distance,
            'category': category,
            'detection_time': time.time()
        }

        self._create_and_post_tweet(post_data)
