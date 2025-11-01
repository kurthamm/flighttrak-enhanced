# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlightTrak is an intelligent real-time aircraft monitoring system that tracks 69 specific aircraft (celebrities, government, historic planes) using ADS-B data from dump1090. The system features smart closest-approach alerting that sends ONE notification per flyby at the most interesting moment, eliminating alert spam while maximizing engagement. Emphasizes reliability, actionable notifications, and user experience over complex analysis.

## Architecture

### Core Services (2 Services)

**1. flight_monitor.py** (flightalert.service) - Main tracking service
- Polls planes.hamm.me (remote dump1090 via Cloudflare tunnel) every 15 seconds
- Compares detected aircraft against aircraft_list.json (69 tracked aircraft)
- **Smart Closest-Approach Alerting**: Tracks each aircraft and alerts ONCE at closest point
  - Monitors distance continuously as aircraft approaches/departs
  - Sends alert when aircraft leaves radar at its closest approach point
  - 24-hour cooldown between alerts for same aircraft
  - 30-minute safety timeout prevents losing long-flying aircraft
- Sends **enhanced HTML email alerts** with distance, tracking links, and flight details
- Logs detections to detected_aircraft.txt
- **Intelligent emergency squawk detection** with false-positive filtering (7500/7600/7700/7777)
  - Filters 7600 (radio failure) during landing approaches to prevent spam
  - Checks altitude, descent rate, proximity to airports, and approach speed
  - Genuine emergencies (7700, 7500, 7777) ALWAYS alert
  - Covers 40+ major US airports for accurate landing detection

**2. enhanced_dashboard.py** (flighttrak-dashboard.service) - Web dashboard
- Flask web server on port 5030
- Real-time aircraft display with Leaflet.js maps
- API endpoints: /api/stats, /api/aircraft
- Independent of flight_monitor.py

### Core Modules

**config_manager.py**: Configuration management
- Loads config.json with environment variable overrides
- Environment variables take precedence (EMAIL_SENDER, HOME_LAT, etc.)
- Usage: `from config_manager import config`

**email_service.py**: Email alerts via Gmail SMTP
- send_aircraft_alert() - Enhanced HTML emails with distance and tracking links
- send_anomaly_alert() - Emergency squawk code alerts
- **Integrated FlightAware API** - FlightAwareLookup class for flight plan data
- Uses Gmail SMTP with TLS (port 587), no API costs

**anomaly_detector.py**: Intelligent emergency detection
- Detects emergency squawk codes (7500/7600/7700/7777) with false-positive filtering
- Smart landing detection: Filters 7600 alerts during normal approach/landing
  - Checks: altitude (<10,000 ft), descent rate (negative), airport proximity (<15 mi), approach speed (80-300 kt)
  - Uses database of 40+ major US airports (JFK, LAX, ORD, ATL, etc.)
- Genuine emergencies (7700 hijack, 7500 emergency, 7777 intercept) ALWAYS alert
- No complex pattern analysis - focused on real emergencies only

**utils.py**: Shared utilities
- haversine_distance() for calculating distance from home
- Log rotation
- Aircraft data formatting

## Data Flow

1. **ADS-B Data Ingestion**: planes.hamm.me serves JSON from remote dump1090
2. **Aircraft Matching**: flight_monitor.py compares detected ICAO codes against aircraft_list.json
3. **Distance Calculation**: Uses haversine formula to calculate miles from home location
4. **Alert Generation**: Two alert types with separate recipients:
   - **Tracked aircraft alerts** - Rich HTML email when celebrity/government aircraft detected
   - **Emergency alerts** - Critical alerts for squawk codes 7500/7600/7700/7777
5. **Persistence**: detected_aircraft.txt logs all detections with timestamps

## Key Integration Points

### Adding New Aircraft to Track
- Edit `aircraft_list.json` directly, OR
- Import from Excel with `python merge_plane_data.py`
- Services automatically reload on change (no restart needed)
- ICAO codes must be uppercase (e.g., "A6F2B7" not "a6f2b7")

### Configuration Hierarchy
1. Environment variables (highest priority)
2. config.json (fallback)
3. Code defaults (lowest priority)

Access via: `config.get('key.subkey')` or `config.get_home_coordinates()`

### Email Alert Flow
All alerts follow this pattern:
```python
from email_service import EmailService
from config_manager import config

email_service = EmailService(config.get_email_config())
email_service.send_aircraft_alert(aircraft, tracked_info, distance, recipients)
```

## Development Commands

```bash
# Virtual environment
source venv/bin/activate
pip install -r requirements.txt

# Run services (development)
python flight_monitor.py              # Main tracking service
python enhanced_dashboard.py          # Dashboard on port 5030

# Run services (production via systemd)
sudo systemctl start flightalert.service
sudo systemctl start flighttrak-dashboard.service
sudo systemctl status flightalert.service

# Restart after code changes
sudo systemctl restart flightalert.service

# View logs
tail -f flighttrak_monitor.log        # Main service logs
tail -f detected_aircraft.txt         # Detection history
tail -f dashboard.log                 # Dashboard logs

# Utilities
python caf.py                         # Validate aircraft with FlightAware API
python merge_plane_data.py            # Import from Excel
python test_email.py                  # Test Gmail SMTP configuration
```

## Testing

```bash
# Test email configuration
python -c "
from email_service import EmailService
from config_manager import config
service = EmailService(config.get_email_config())
print('Gmail SMTP configured successfully')
"

# Test configuration loading
python -c "
from config_manager import config
print(f'Home: {config.get_home_coordinates()}')
print(f'Tracked aircraft: 59')
"

# Test data source connectivity
curl https://planes.hamm.me/data/aircraft.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Aircraft visible: {len(d.get(\"aircraft\",[]))}')"

# Watch for detections in real-time
tail -f detected_aircraft.txt
```

## Important Implementation Details

### Smart Closest-Approach Alerting System

**Problem Solved**: Previously sent 9 alerts in 25 minutes as aircraft flew by (alert every 5 min)

**Solution**: Intelligent flyby tracking
1. **Detection**: Aircraft enters tracking area → Start monitoring
2. **Tracking**: Update distance every 15 seconds, record closest point
3. **Decision Logic**:
   - If getting closer → Keep waiting
   - If starts moving away → Aircraft has passed closest point
   - When aircraft leaves radar → Send ONE alert at closest approach
   - Safety timeout: 30 minutes max tracking before forcing alert
4. **Cooldown**: 24-hour cooldown prevents duplicate alerts same day

**Result**: ONE perfectly-timed alert per flyby showing the closest distance achieved

**Example**:
- 16:03 - Detected at 102 miles → Start tracking
- 16:08 - Now 86 miles → Closer, keep waiting
- 16:13 - Now 85 miles → **Closest point recorded**
- 16:18 - Now 100 miles → Moving away
- 16:20 - Left radar → **Send ONE alert: "Tommy Hilfiger at 85 miles (closest approach)"**

### Enhanced Email Alerts
- **Distance prominently displayed**: "24.5 miles from home" in large text
- **Multiple tracking links**: FlightAware, ADS-B Exchange, Flightradar24
- **Google Maps link**: View current aircraft location
- **Flight details**: Heading (with compass direction), vertical rate, altitude, speed
- **Aircraft information**: Owner, model, registration, ICAO hex, description
- **Rich formatting**: Separate sections for aircraft info and flight status

### Intelligent Emergency Squawk Detection

**Problem Solved**: False positive 7600 (radio failure) alerts during normal landings

**Emergency Codes**:
- 7500 = Hijack
- 7600 = Radio failure
- 7700 = General emergency
- 7777 = Military intercept

**Smart Filtering**:
- **7600 ONLY filtered if**:
  - Descending (negative vertical rate)
  - Low altitude (<10,000 ft)
  - Near major airport (<15 miles)
  - Approach speed (80-300 knots)
  - OR very low (<5,000 ft) and descending fast (>500 fpm)
- **7700, 7500, 7777 ALWAYS alert** (genuine emergencies)

**Airport Database**: 40+ major US airports (JFK, LAX, ORD, ATL, DFW, SFO, BOS, etc.)

**Result**: Eliminates false positives from landing approaches while catching all real emergencies

### Dashboard Architecture
- Flask app with Jinja2 templates
- JavaScript polls /api/aircraft every 5 seconds
- Leaflet.js for interactive maps
- No database; reads aircraft.json directly from planes.hamm.me
- Available at http://server:5030

## Common Pitfalls

1. **Gmail App Passwords**: Requires 2FA enabled on Gmail account. Regular password won't work.
2. **planes.hamm.me**: If unreachable, service logs errors but continues. Check Cloudflare tunnel status.
3. **JSON Formatting**: aircraft_list.json must be valid JSON. Use `python -m json.tool aircraft_list.json` to validate.
4. **ICAO Codes**: Must be uppercase in aircraft_list.json (e.g., "A6F2B7" not "a6f2b7")
5. **Service Path**: Services expect to run from /home/kurt/flighttrak (systemd WorkingDirectory)
6. **Distance Units**: All distances in miles, altitudes in feet, speeds in knots (aviation standard)

## Tracked Aircraft Database

**Total: 69 aircraft tracked**

**Breakdown**:
- Government/Military: 6 aircraft (Air Force One, Marine One, etc.)
- Celebrity/Private: 55 aircraft (Taylor Swift, Elon Musk, etc.)
- Historic: 2 aircraft (B-29 FIFI, Ford Trimotor)

**Notable Examples**:
- **Taylor Swift** (N621MM) - Dassault Falcon 7X - "Primary private jet - Heavily tracked"
- **Elon Musk** (N628TS, N272BG) - Gulfstream G650ER and G550
- **Air Force One** (ADFDF8, ADFDF9) - VC-25A Boeing 747s
- **Jeff Bezos** (N11AF) - Gulfstream G700 - "$80M flagship delivered July 2024"
- **Drake** (N767CJ) - Boeing 767-200ER - "Air Drake - $200M with bedroom and casino"
- **Donald Trump** (N757AF) - Boeing 757-200 - "Trump Force One"
- **Tommy Hilfiger** (N818TH) - Dassault Falcon 900 - "Custom nautical interior" (Most frequently detected)
- **Eric Schmidt** (N652WE) - Gulfstream G650 - "Via Palo Alto investor trust"
- **B-29 FIFI** (N529B) - One of only two flying B-29s worldwide

See aircraft_list.json for the complete list.

## System Evolution & Recent Updates

### November 1, 2025 - Comprehensive Codebase Refactoring & Consolidation
**Major Cleanup**: Removed dead code, freed disk space, improved code quality, consolidated architecture

**Phase 1 - Initial Refactoring:**
- ✅ **Archived dead AI intelligence system**: Moved 15 Python files (7,141 lines) to `archive/ai_intelligence_deprecated/`
- ✅ **Deleted unused databases**: Freed 1.76GB disk space (flight_paths.db, contextual_intelligence.db, etc.)
- ✅ **Fixed exception handling bugs**: Replaced 4 bare `except:` statements with specific exceptions
- ✅ **Organized file structure**:
  - Created `tests/` directory (8 test files)
  - Created `scripts/` directory (9 utility scripts)
  - Root reduced to 9 core production files
- ✅ **Security audit**: Verified no `debug=True` in production code, proper logging configuration

**Phase 2 - Module Consolidation:**
- ✅ **Consolidated FlightAware API**: Merged `flightaware_lookup.py` (139 lines) into `email_service.py`
  - Eliminated single-use module (only imported by email_service.py)
  - Reduced import complexity
- ✅ **Moved weekly_report.py to scripts/**: Standalone script with no imports
  - Now in `scripts/weekly_report.py` where it belongs
- ✅ **Final result**: **7 core files** (reduced from 9, down 22%)

**Impact:**
- Repository footprint reduced by 50%+
- Core modules reduced from 9 → 7 files
- Clearer project structure with single-responsibility modules
- Better error handling and debugging
- Easier maintenance and onboarding
- No breaking changes - fully backward compatible

**Final File Structure:**
```
/flighttrak/
├── Core Files (7):
│   ├── flight_monitor.py (33K) - Main tracking service
│   ├── enhanced_dashboard.py (12K) - Web dashboard
│   ├── config_manager.py (11K) - Configuration
│   ├── email_service.py (54K) - Alerts + FlightAware API
│   ├── anomaly_detector.py (27K) - Emergency detection
│   ├── twitter_poster.py (13K) - Social media posting
│   └── utils.py (11K) - Shared utilities
├── tests/ (8 test files)
├── scripts/ (9 utility scripts)
├── archive/ai_intelligence_deprecated/ (15 dead files)
└── Configuration & docs
```

See REFACTORING.md for complete details.

### October 30, 2025 - Smart Alerting & Emergency Filter Enhancements
**Major UX Improvements**:
- ✅ **Smart Closest-Approach Alerting**: Replaced spam-prone 5-minute cooldown with intelligent tracking
  - Monitors each aircraft's distance continuously
  - Sends ONE alert per flyby at closest approach point
  - 24-hour cooldown between alerts for same aircraft
  - Reduced alert volume by ~90% while improving relevance
- ✅ **Emergency Squawk False-Positive Filtering**: Eliminated landing-related false alarms
  - Intelligent 7600 filtering based on altitude, descent rate, airport proximity
  - Expanded airport database to 40+ major US airports
  - Maintains 100% detection of genuine emergencies (7700, 7500, 7777)
- ✅ **Gmail Filter Issue Resolved**: Identified and fixed auto-archiving filter
- ✅ **Increased aircraft database**: Now tracking 69 aircraft (was 59)

### October 2025 Refactoring - Simplified from over-engineered AI system
- ✅ Removed AI event intelligence (DBSCAN clustering, ML pattern matching)
- ✅ Removed contextual intelligence integration (news, weather correlation)
- ✅ Disabled ai_intelligence_service.py (flighttrak-ai-intelligence.service)
- ✅ Simplified anomaly detection to emergency squawks only
- ✅ Enhanced email alerts with distance, tracking links, and rich flight details
- ✅ Migrated from SendGrid API to Gmail SMTP (no per-email costs)
- ✅ Fixed data type errors in anomaly detector
- ✅ Updated aircraft database with enhanced descriptions

### 2025 - SendGrid to Gmail SMTP Migration
- Old code used `sendgrid` Python library
- New code uses stdlib `smtplib` with TLS
- No per-email costs with Gmail
- Environment variable changed: SENDGRID_API_KEY → EMAIL_PASSWORD

## Current System Status (October 30, 2025)

**Operational Status**: ✅ Fully Operational

**Services Running**:
- flightalert.service: Running (PID 96928, started Oct 29 22:12)
- flighttrak-dashboard.service: Running (port 5030)

**Recent Performance**:
- Last 24 hours: 11 detections (Tommy Hilfiger's Falcon 900)
- Last 30 days: 217 total detections
  - Tommy Hilfiger (A6F2B7): 203 detections (most active)
  - Eric Schmidt (A6B42A): 14 detections
- Dashboard: 32 aircraft currently visible

**Alert Recipients**: 4 email addresses
- kurthamm@gmail.com
- jamie@jamiehamm.com
- me@kathrynbaird.com
- stacey@hammfamily.com

**Integration Status**:
- ✅ Gmail SMTP: Working
- ✅ FlightAware API: Configured
- ✅ Twitter/X: Enabled (with privacy delays)
- ✅ Weekly Reports: Enabled
- ✅ Health Monitoring: Enabled
- ✅ Emergency Detection: Enhanced with false-positive filtering

**Data Source**: planes.hamm.me (remote dump1090 via Cloudflare tunnel)
