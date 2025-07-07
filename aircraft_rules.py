#!/usr/bin/env python3
"""
Aircraft Type-Aware Alert Rules for FlightTrak
Different alert thresholds based on aircraft type and operational context
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class AircraftCategory(Enum):
    COMMERCIAL_AIRLINER = "commercial_airliner"
    REGIONAL_AIRCRAFT = "regional_aircraft"
    BUSINESS_JET = "business_jet"
    GENERAL_AVIATION = "general_aviation"
    HELICOPTER = "helicopter"
    MEDICAL_HELICOPTER = "medical_helicopter"
    POLICE_HELICOPTER = "police_helicopter"
    MILITARY_AIRCRAFT = "military_aircraft"
    CARGO_AIRCRAFT = "cargo_aircraft"
    TRAINING_AIRCRAFT = "training_aircraft"
    UNKNOWN = "unknown"

@dataclass
class AlertThresholds:
    """Alert thresholds for different aircraft parameters"""
    min_altitude_ft: int
    max_altitude_ft: int
    min_speed_kt: int
    max_speed_kt: int
    max_vertical_rate_fpm: int
    squawk_emergency_codes: List[str]
    allow_low_altitude_ops: bool
    pattern_detection_sensitivity: float  # 0.0 to 1.0

class AircraftTypeClassifier:
    """Classifies aircraft based on type codes and operational patterns"""
    
    def __init__(self):
        self.type_mappings = self._initialize_type_mappings()
        self.operator_patterns = self._initialize_operator_patterns()
        
    def _initialize_type_mappings(self) -> Dict[str, AircraftCategory]:
        """Initialize aircraft type code to category mappings"""
        return {
            # Commercial Airliners
            'A319': AircraftCategory.COMMERCIAL_AIRLINER,
            'A320': AircraftCategory.COMMERCIAL_AIRLINER,
            'A321': AircraftCategory.COMMERCIAL_AIRLINER,
            'A330': AircraftCategory.COMMERCIAL_AIRLINER,
            'A340': AircraftCategory.COMMERCIAL_AIRLINER,
            'A350': AircraftCategory.COMMERCIAL_AIRLINER,
            'A380': AircraftCategory.COMMERCIAL_AIRLINER,
            'B737': AircraftCategory.COMMERCIAL_AIRLINER,
            'B738': AircraftCategory.COMMERCIAL_AIRLINER,
            'B739': AircraftCategory.COMMERCIAL_AIRLINER,
            'B747': AircraftCategory.COMMERCIAL_AIRLINER,
            'B757': AircraftCategory.COMMERCIAL_AIRLINER,
            'B767': AircraftCategory.COMMERCIAL_AIRLINER,
            'B777': AircraftCategory.COMMERCIAL_AIRLINER,
            'B787': AircraftCategory.COMMERCIAL_AIRLINER,
            'B38M': AircraftCategory.COMMERCIAL_AIRLINER,  # 737 MAX
            
            # Regional Aircraft
            'CRJ2': AircraftCategory.REGIONAL_AIRCRAFT,
            'CRJ7': AircraftCategory.REGIONAL_AIRCRAFT,
            'CRJ9': AircraftCategory.REGIONAL_AIRCRAFT,
            'E145': AircraftCategory.REGIONAL_AIRCRAFT,
            'E170': AircraftCategory.REGIONAL_AIRCRAFT,
            'E175': AircraftCategory.REGIONAL_AIRCRAFT,
            'E190': AircraftCategory.REGIONAL_AIRCRAFT,
            'DH8A': AircraftCategory.REGIONAL_AIRCRAFT,
            'DH8B': AircraftCategory.REGIONAL_AIRCRAFT,
            'DH8C': AircraftCategory.REGIONAL_AIRCRAFT,
            'DH8D': AircraftCategory.REGIONAL_AIRCRAFT,
            
            # Business Jets
            'GLEX': AircraftCategory.BUSINESS_JET,
            'GLF4': AircraftCategory.BUSINESS_JET,
            'GLF5': AircraftCategory.BUSINESS_JET,
            'GLF6': AircraftCategory.BUSINESS_JET,
            'C525': AircraftCategory.BUSINESS_JET,
            'C550': AircraftCategory.BUSINESS_JET,
            'C560': AircraftCategory.BUSINESS_JET,
            'CL30': AircraftCategory.BUSINESS_JET,
            'CL60': AircraftCategory.BUSINESS_JET,
            'F900': AircraftCategory.BUSINESS_JET,
            'HDJT': AircraftCategory.BUSINESS_JET,
            
            # General Aviation
            'C172': AircraftCategory.GENERAL_AVIATION,
            'C182': AircraftCategory.GENERAL_AVIATION,
            'C208': AircraftCategory.GENERAL_AVIATION,
            'PA28': AircraftCategory.GENERAL_AVIATION,
            'PA34': AircraftCategory.GENERAL_AVIATION,
            'PA46': AircraftCategory.GENERAL_AVIATION,
            'BE20': AircraftCategory.GENERAL_AVIATION,
            'BE35': AircraftCategory.GENERAL_AVIATION,
            'BE36': AircraftCategory.GENERAL_AVIATION,
            
            # Helicopters
            'R22': AircraftCategory.HELICOPTER,
            'R44': AircraftCategory.HELICOPTER,
            'R66': AircraftCategory.HELICOPTER,
            'EC35': AircraftCategory.HELICOPTER,  # EC135 (Medical/EMS common)
            'EC45': AircraftCategory.HELICOPTER,  # EC145
            'S76': AircraftCategory.HELICOPTER,
            'B407': AircraftCategory.HELICOPTER,
            'B429': AircraftCategory.HELICOPTER,
            'A109': AircraftCategory.HELICOPTER,
            'AS50': AircraftCategory.HELICOPTER,  # AS350
            'UH1': AircraftCategory.HELICOPTER,
            'H60': AircraftCategory.MILITARY_AIRCRAFT,  # Military helicopter
            
            # Military Aircraft
            'C130': AircraftCategory.MILITARY_AIRCRAFT,
            'C17': AircraftCategory.MILITARY_AIRCRAFT,
            'KC10': AircraftCategory.MILITARY_AIRCRAFT,
            'KC135': AircraftCategory.MILITARY_AIRCRAFT,
            'F16': AircraftCategory.MILITARY_AIRCRAFT,
            'F15': AircraftCategory.MILITARY_AIRCRAFT,
            'F18': AircraftCategory.MILITARY_AIRCRAFT,
            'F22': AircraftCategory.MILITARY_AIRCRAFT,
            'F35': AircraftCategory.MILITARY_AIRCRAFT,
            'A10': AircraftCategory.MILITARY_AIRCRAFT,
            
            # Cargo Aircraft
            'MD11': AircraftCategory.CARGO_AIRCRAFT,
            'B744': AircraftCategory.CARGO_AIRCRAFT,  # 747-400F
            'B748': AircraftCategory.CARGO_AIRCRAFT,  # 747-8F
            'A306': AircraftCategory.CARGO_AIRCRAFT,  # A300-600F
        }
    
    def _initialize_operator_patterns(self) -> Dict[str, AircraftCategory]:
        """Initialize operator name patterns for classification"""
        return {
            # Medical/EMS operators
            'air methods': AircraftCategory.MEDICAL_HELICOPTER,
            'med flight': AircraftCategory.MEDICAL_HELICOPTER,
            'life flight': AircraftCategory.MEDICAL_HELICOPTER,
            'care flight': AircraftCategory.MEDICAL_HELICOPTER,
            'med star': AircraftCategory.MEDICAL_HELICOPTER,
            'stat medevac': AircraftCategory.MEDICAL_HELICOPTER,
            'emergency medical': AircraftCategory.MEDICAL_HELICOPTER,
            'medevac': AircraftCategory.MEDICAL_HELICOPTER,
            
            # Police/Law Enforcement
            'police': AircraftCategory.POLICE_HELICOPTER,
            'sheriff': AircraftCategory.POLICE_HELICOPTER,
            'state patrol': AircraftCategory.POLICE_HELICOPTER,
            'law enforcement': AircraftCategory.POLICE_HELICOPTER,
            
            # Training
            'flight training': AircraftCategory.TRAINING_AIRCRAFT,
            'flying club': AircraftCategory.TRAINING_AIRCRAFT,
            'aviation academy': AircraftCategory.TRAINING_AIRCRAFT,
            
            # Commercial Airlines (major patterns)
            'american airlines': AircraftCategory.COMMERCIAL_AIRLINER,
            'delta': AircraftCategory.COMMERCIAL_AIRLINER,
            'united': AircraftCategory.COMMERCIAL_AIRLINER,
            'southwest': AircraftCategory.COMMERCIAL_AIRLINER,
            'jetblue': AircraftCategory.COMMERCIAL_AIRLINER,
            'alaska airlines': AircraftCategory.COMMERCIAL_AIRLINER,
        }
    
    def classify_aircraft(self, aircraft_type: str, operator: str, registration: str) -> AircraftCategory:
        """Classify aircraft based on available information"""
        
        # First check operator patterns
        if operator:
            operator_lower = operator.lower()
            for pattern, category in self.operator_patterns.items():
                if pattern in operator_lower:
                    return category
        
        # Then check aircraft type code
        if aircraft_type:
            aircraft_type_upper = aircraft_type.upper()
            if aircraft_type_upper in self.type_mappings:
                return self.type_mappings[aircraft_type_upper]
            
            # Check for partial matches
            for type_code, category in self.type_mappings.items():
                if type_code in aircraft_type_upper or aircraft_type_upper.startswith(type_code[:3]):
                    return category
        
        # Registration-based heuristics (US examples)
        if registration:
            if registration.startswith('N') and len(registration) >= 4:
                last_chars = registration[-2:]
                # Some common patterns for medical helicopters
                if any(x in last_chars.upper() for x in ['MH', 'EH', 'LF']):
                    return AircraftCategory.MEDICAL_HELICOPTER
        
        return AircraftCategory.UNKNOWN

class AircraftAlertRules:
    """Aircraft type-aware alert rules"""
    
    def __init__(self):
        self.classifier = AircraftTypeClassifier()
        self.thresholds = self._initialize_thresholds()
        
    def _initialize_thresholds(self) -> Dict[AircraftCategory, AlertThresholds]:
        """Initialize alert thresholds for each aircraft category"""
        return {
            AircraftCategory.COMMERCIAL_AIRLINER: AlertThresholds(
                min_altitude_ft=1000,     # Higher minimum altitude
                max_altitude_ft=45000,    # Normal cruise ceiling
                min_speed_kt=120,         # Minimum safe speed
                max_speed_kt=550,         # Normal max cruise speed
                max_vertical_rate_fpm=3000,  # Normal climb/descent rate
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=False,  # Strict rules
                pattern_detection_sensitivity=0.8  # High sensitivity
            ),
            
            AircraftCategory.REGIONAL_AIRCRAFT: AlertThresholds(
                min_altitude_ft=800,
                max_altitude_ft=35000,
                min_speed_kt=100,
                max_speed_kt=450,
                max_vertical_rate_fpm=3500,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=False,
                pattern_detection_sensitivity=0.7
            ),
            
            AircraftCategory.BUSINESS_JET: AlertThresholds(
                min_altitude_ft=800,
                max_altitude_ft=51000,
                min_speed_kt=100,
                max_speed_kt=600,
                max_vertical_rate_fpm=4000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=False,
                pattern_detection_sensitivity=0.6
            ),
            
            AircraftCategory.GENERAL_AVIATION: AlertThresholds(
                min_altitude_ft=500,      # Lower for GA aircraft
                max_altitude_ft=25000,
                min_speed_kt=50,
                max_speed_kt=350,
                max_vertical_rate_fpm=2000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,  # More flexible
                pattern_detection_sensitivity=0.5  # Lower sensitivity
            ),
            
            AircraftCategory.HELICOPTER: AlertThresholds(
                min_altitude_ft=100,      # Very low allowed for helicopters
                max_altitude_ft=15000,
                min_speed_kt=20,          # Can hover
                max_speed_kt=200,
                max_vertical_rate_fpm=2500,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,
                pattern_detection_sensitivity=0.3  # Very low - helicopters circle normally
            ),
            
            AircraftCategory.MEDICAL_HELICOPTER: AlertThresholds(
                min_altitude_ft=50,       # Can land almost anywhere
                max_altitude_ft=10000,
                min_speed_kt=15,          # Can hover/land
                max_speed_kt=180,
                max_vertical_rate_fpm=3000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,
                pattern_detection_sensitivity=0.1  # Very low - emergency operations
            ),
            
            AircraftCategory.POLICE_HELICOPTER: AlertThresholds(
                min_altitude_ft=100,
                max_altitude_ft=8000,
                min_speed_kt=15,
                max_speed_kt=160,
                max_vertical_rate_fpm=2000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,
                pattern_detection_sensitivity=0.2  # Low - patrol patterns expected
            ),
            
            AircraftCategory.MILITARY_AIRCRAFT: AlertThresholds(
                min_altitude_ft=100,      # Military has wide operational envelope
                max_altitude_ft=60000,
                min_speed_kt=50,
                max_speed_kt=800,
                max_vertical_rate_fpm=10000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,
                pattern_detection_sensitivity=0.4  # Training patterns common
            ),
            
            AircraftCategory.TRAINING_AIRCRAFT: AlertThresholds(
                min_altitude_ft=300,
                max_altitude_ft=15000,
                min_speed_kt=40,
                max_speed_kt=250,
                max_vertical_rate_fpm=1500,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=True,
                pattern_detection_sensitivity=0.3  # Pattern work expected
            ),
            
            AircraftCategory.UNKNOWN: AlertThresholds(
                min_altitude_ft=800,      # Conservative defaults
                max_altitude_ft=40000,
                min_speed_kt=60,
                max_speed_kt=500,
                max_vertical_rate_fpm=3000,
                squawk_emergency_codes=['7500', '7600', '7700'],
                allow_low_altitude_ops=False,
                pattern_detection_sensitivity=0.6
            ),
        }
    
    def get_alert_thresholds(self, aircraft_data: Dict) -> AlertThresholds:
        """Get appropriate alert thresholds for aircraft"""
        lookup = aircraft_data.get('lookup', {})
        aircraft_type = lookup.get('aircraft_type', '')
        operator = lookup.get('operator', '')
        registration = lookup.get('registration', '')
        
        category = self.classifier.classify_aircraft(aircraft_type, operator, registration)
        return self.thresholds[category]
    
    def evaluate_altitude_alert(self, aircraft_data: Dict, airport_proximity: Dict = None) -> Tuple[bool, str, str]:
        """
        Evaluate if altitude should trigger an alert
        Returns (should_alert, severity, reason)
        """
        altitude = aircraft_data.get('alt_baro', aircraft_data.get('alt_geom', 0))
        if not altitude:
            return False, 'NONE', 'No altitude data'
        
        thresholds = self.get_alert_thresholds(aircraft_data)
        category = self.classifier.classify_aircraft(
            aircraft_data.get('lookup', {}).get('aircraft_type', ''),
            aircraft_data.get('lookup', {}).get('operator', ''),
            aircraft_data.get('lookup', {}).get('registration', '')
        )
        
        # Check if near airport (reduces alert likelihood)
        if airport_proximity and airport_proximity.get('likely_approach'):
            return False, 'NONE', f"Normal approach to {airport_proximity['airport'].name}"
        
        # Low altitude check
        if altitude < thresholds.min_altitude_ft:
            severity = 'HIGH'
            
            # Special handling for helicopters and emergency services
            if category in [AircraftCategory.MEDICAL_HELICOPTER, AircraftCategory.POLICE_HELICOPTER]:
                # Much more lenient for emergency services
                if altitude < 200:
                    severity = 'MEDIUM'
                    reason = f"Emergency service helicopter at {altitude}ft - likely normal operations"
                else:
                    return False, 'NONE', f"Emergency service helicopter operations"
            elif category == AircraftCategory.HELICOPTER:
                severity = 'MEDIUM'
                reason = f"Helicopter at {altitude}ft - below typical minimum but normal for helicopter ops"
            elif thresholds.allow_low_altitude_ops and altitude > 300:
                severity = 'MEDIUM'
                reason = f"{category.value.replace('_', ' ')} at {altitude}ft - low but within operational envelope"
            else:
                reason = f"{category.value.replace('_', ' ')} at critically low altitude: {altitude}ft"
            
            return True, severity, reason
        
        return False, 'NONE', 'Altitude normal'
    
    def evaluate_speed_alert(self, aircraft_data: Dict) -> Tuple[bool, str, str]:
        """Evaluate if speed should trigger an alert"""
        speed = aircraft_data.get('gs', 0)
        if not speed:
            return False, 'NONE', 'No speed data'
        
        thresholds = self.get_alert_thresholds(aircraft_data)
        category = self.classifier.classify_aircraft(
            aircraft_data.get('lookup', {}).get('aircraft_type', ''),
            aircraft_data.get('lookup', {}).get('operator', ''),
            aircraft_data.get('lookup', {}).get('registration', '')
        )
        
        # High speed check
        if speed > thresholds.max_speed_kt:
            return True, 'HIGH', f"{category.value.replace('_', ' ')} exceeding normal speed: {speed}kt"
        
        # Low speed check (context dependent)
        altitude = aircraft_data.get('alt_baro', aircraft_data.get('alt_geom', 0))
        if speed < thresholds.min_speed_kt and altitude > 5000:
            # Helicopters can hover
            if category in [AircraftCategory.HELICOPTER, AircraftCategory.MEDICAL_HELICOPTER, AircraftCategory.POLICE_HELICOPTER]:
                return False, 'NONE', 'Helicopter hovering or slow flight - normal'
            return True, 'MEDIUM', f"{category.value.replace('_', ' ')} unusually slow at altitude: {speed}kt @ {altitude}ft"
        
        return False, 'NONE', 'Speed normal'
    
    def should_detect_circling(self, aircraft_data: Dict) -> bool:
        """Determine if circling detection should be applied"""
        thresholds = self.get_alert_thresholds(aircraft_data)
        category = self.classifier.classify_aircraft(
            aircraft_data.get('lookup', {}).get('aircraft_type', ''),
            aircraft_data.get('lookup', {}).get('operator', ''),
            aircraft_data.get('lookup', {}).get('registration', '')
        )
        
        # Reduce circling detection for aircraft types that commonly circle
        if category in [
            AircraftCategory.MEDICAL_HELICOPTER, 
            AircraftCategory.POLICE_HELICOPTER,
            AircraftCategory.TRAINING_AIRCRAFT
        ]:
            return False
        
        return thresholds.pattern_detection_sensitivity > 0.4

# Example usage and testing
if __name__ == '__main__':
    rules = AircraftAlertRules()
    
    # Test aircraft data
    test_aircraft = [
        {
            'hex': 'ac9c2b',
            'alt_baro': 500,
            'gs': 45,
            'lookup': {
                'aircraft_type': 'EC35',
                'operator': 'Air Methods',
                'registration': 'N911UG'
            }
        },
        {
            'hex': 'ab4ea8',
            'alt_baro': 800,
            'gs': 200,
            'lookup': {
                'aircraft_type': 'A319',
                'operator': 'American Airlines',
                'registration': 'N828AW'
            }
        }
    ]
    
    for aircraft in test_aircraft:
        print(f"\nTesting aircraft {aircraft['hex']}:")
        
        thresholds = rules.get_alert_thresholds(aircraft)
        category = rules.classifier.classify_aircraft(
            aircraft['lookup']['aircraft_type'],
            aircraft['lookup']['operator'],
            aircraft['lookup']['registration']
        )
        
        print(f"  Category: {category.value}")
        print(f"  Min altitude: {thresholds.min_altitude_ft}ft")
        print(f"  Pattern sensitivity: {thresholds.pattern_detection_sensitivity}")
        
        should_alert, severity, reason = rules.evaluate_altitude_alert(aircraft)
        print(f"  Altitude alert: {should_alert} ({severity}) - {reason}")
        
        should_alert, severity, reason = rules.evaluate_speed_alert(aircraft)
        print(f"  Speed alert: {should_alert} ({severity}) - {reason}")
        
        print(f"  Should detect circling: {rules.should_detect_circling(aircraft)}")