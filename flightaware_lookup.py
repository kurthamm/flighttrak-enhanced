#!/usr/bin/env python3
"""
FlightAware API Lookup Service
Retrieves flight plan information for aircraft
"""

import logging
import requests
from typing import Dict, Optional
from datetime import datetime
from config_manager import config


class FlightAwareLookup:
    """FlightAware API service for flight plan lookups"""

    def __init__(self):
        self.api_key = config.get('flightaware_api_key')
        self.base_url = "https://aeroapi.flightaware.com/aeroapi"

        if not self.api_key:
            logging.warning("FlightAware API key not configured - flight plan lookups disabled")

    def get_flight_info(self, ident: str) -> Optional[Dict]:
        """
        Get flight plan information for a flight

        Args:
            ident: Flight identifier (callsign like "PDT6120" or registration like "N621MM")

        Returns:
            Dictionary with flight info or None if not found
        """
        if not self.api_key:
            return None

        try:
            # Try to get the most recent flight for this identifier
            url = f"{self.base_url}/flights/{ident}"
            headers = {"x-apikey": self.api_key}

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                flights = data.get('flights', [])

                if flights:
                    # Get the most recent flight (first in list)
                    flight = flights[0]
                    return self._parse_flight_data(flight)
            elif response.status_code == 404:
                logging.debug(f"Flight {ident} not found in FlightAware")
            else:
                logging.warning(f"FlightAware API error {response.status_code}: {response.text}")

            return None

        except requests.exceptions.Timeout:
            logging.error(f"FlightAware API timeout for {ident}")
            return None
        except Exception as e:
            logging.error(f"Error fetching FlightAware data for {ident}: {e}")
            return None

    def _parse_flight_data(self, flight: Dict) -> Dict:
        """Parse FlightAware flight data into simplified format"""
        try:
            origin = flight.get('origin', {})
            destination = flight.get('destination', {})

            # Parse times
            departure_time = self._parse_time(flight.get('scheduled_off') or flight.get('actual_off'))
            arrival_time = self._parse_time(flight.get('estimated_on') or flight.get('scheduled_on'))

            return {
                'ident': flight.get('ident', 'Unknown'),
                'origin': {
                    'code': origin.get('code', 'Unknown'),
                    'name': origin.get('name', 'Unknown'),
                    'city': origin.get('city', 'Unknown'),
                },
                'destination': {
                    'code': destination.get('code', 'Unknown'),
                    'name': destination.get('name', 'Unknown'),
                    'city': destination.get('city', 'Unknown'),
                },
                'departure_time': departure_time,
                'arrival_time': arrival_time,
                'status': flight.get('status', 'Unknown'),
                'aircraft_type': flight.get('aircraft_type', 'Unknown'),
            }

        except Exception as e:
            logging.error(f"Error parsing FlightAware data: {e}")
            return None

    def _parse_time(self, time_str: Optional[str]) -> Optional[str]:
        """Parse ISO time string to readable format"""
        if not time_str:
            return None

        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime('%I:%M %p %Z on %b %d')
        except (ValueError, AttributeError):
            return time_str

    def get_flight_info_by_icao(self, icao_hex: str, callsign: Optional[str] = None) -> Optional[Dict]:
        """
        Get flight info, trying callsign first, then ICAO hex

        Args:
            icao_hex: Aircraft ICAO hex code
            callsign: Aircraft callsign if available

        Returns:
            Flight information dictionary or None
        """
        # Try callsign first (more reliable)
        if callsign and callsign.strip():
            info = self.get_flight_info(callsign.strip())
            if info:
                return info

        # Fallback to ICAO hex
        info = self.get_flight_info(icao_hex)
        return info


# Global instance
_flightaware_lookup = None

def get_flightaware_lookup() -> FlightAwareLookup:
    """Get or create global FlightAware lookup instance"""
    global _flightaware_lookup
    if _flightaware_lookup is None:
        _flightaware_lookup = FlightAwareLookup()
    return _flightaware_lookup
