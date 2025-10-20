# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlightTrak is a simple, focused real-time aircraft monitoring system that tracks specific aircraft (celebrities, government, historic planes) using ADS-B data from dump1090 and sends rich email alerts when detected. The system emphasizes reliability and actionable notifications over complex analysis.

## Architecture

### Core Services (2 Services)

**1. flight_monitor.py** (flightalert.service) - Main tracking service
- Polls planes.hamm.me (remote dump1090 via Cloudflare tunnel) every 15 seconds
- Compares detected aircraft against aircraft_list.json (59 tracked aircraft)
- Sends **enhanced HTML email alerts** with distance, tracking links, and flight details
- Logs detections to detected_aircraft.txt
- Optional emergency squawk detection (7500/7600/7700/7777)
- 5-minute cooldown per aircraft to prevent spam

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
- Uses Gmail SMTP with TLS (port 587), no API costs

**anomaly_detector.py**: Emergency detection only
- Simplified to detect emergency squawk codes only (7500/7600/7700/7777)
- No complex pattern analysis
- Critical severity alerts for genuine emergencies

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

### Alert Deduplication
- flight_monitor.py uses `recent_alerts` set with 5-minute cooldown
- Prevents spam from aircraft circling near home location
- Same aircraft won't trigger multiple alerts within 5 minutes

### Enhanced Email Alerts
- **Distance prominently displayed**: "24.5 miles from home" in large text
- **Multiple tracking links**: FlightAware, ADS-B Exchange, Flightradar24
- **Google Maps link**: View current aircraft location
- **Flight details**: Heading (with compass direction), vertical rate, altitude, speed
- **Aircraft information**: Owner, model, registration, ICAO hex, description
- **Rich formatting**: Separate sections for aircraft info and flight status

### Emergency Squawk Detection
- Emergency codes: 7500 (hijack), 7600 (radio failure), 7700 (emergency), 7777 (military intercept)
- Triggers immediate CRITICAL alerts
- Simplified from complex anomaly analysis to just squawk code checking

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

## Tracked Aircraft Examples

The system tracks 59 aircraft including:
- **Taylor Swift** (N621MM) - Dassault Falcon 7X - "Primary private jet - Heavily tracked"
- **Elon Musk** (N628TS, N272BG) - Gulfstream G650ER and G550
- **Air Force One** (ADFDF8, ADFDF9) - VC-25A Boeing 747s
- **Jeff Bezos** (N11AF) - Gulfstream G700 - "$80M flagship delivered July 2024"
- **Drake** (N767CJ) - Boeing 767-200ER - "Air Drake - $200M with bedroom and casino"
- **Donald Trump** (N757AF) - Boeing 757-200 - "Trump Force One"
- **B-29 FIFI** (N529B) - One of only two flying B-29s worldwide

See aircraft_list.json for the complete list.

## System Evolution

**October 2025 Refactoring**: Simplified from over-engineered AI system to focused tracking
- ✅ Removed AI event intelligence (DBSCAN clustering, ML pattern matching)
- ✅ Removed contextual intelligence integration (news, weather correlation)
- ✅ Disabled ai_intelligence_service.py (flighttrak-ai-intelligence.service)
- ✅ Simplified anomaly detection to emergency squawks only
- ✅ Enhanced email alerts with distance, tracking links, and rich flight details
- ✅ Migrated from SendGrid API to Gmail SMTP (no per-email costs)
- ✅ Fixed data type errors in anomaly detector
- ✅ Updated aircraft database with enhanced descriptions

**Previous Migration (2025)**: SendGrid to Gmail SMTP
- Old code used `sendgrid` Python library
- New code uses stdlib `smtplib` with TLS
- No per-email costs with Gmail
- Environment variable changed: SENDGRID_API_KEY → EMAIL_PASSWORD
