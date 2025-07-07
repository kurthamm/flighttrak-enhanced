# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlightTrak is a real-time aircraft monitoring and alert system that tracks specific aircraft using ADS-B data and sends email notifications when they are detected within range.

## Key Architecture

The system consists of:
- **fa.py**: Main monitoring service that connects to dump1090 (port 30002) for ADS-B data
- **caf.py**: Aircraft validation tool using FlightAware API
- **merge_plane_data.py**: Merges aircraft data from Excel with JSON
- **send_service_notification.py**: Service notification utility
- **checkaf.py**: Simple tail number identification tool

Data flow: dump1090 → fa.py → distance calculation → email alerts via SendGrid

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the main flight alert service
python fa.py

# Validate and update aircraft list
python caf.py

# Merge aircraft data from Excel
python merge_plane_data.py

# Check aircraft list for tail numbers
python checkaf.py

# Send service notifications
python send_service_notification.py start  # or 'reload'
```

## Configuration

All configuration is in `config.json`:
- Aircraft tracking list: `aircraft_list.json`
- Home location coordinates for distance calculations
- FlightAware API credentials
- SendGrid email configuration
- Alive notification interval (seconds)

## Important Notes

1. The system expects dump1090 to be running on localhost:30002
2. Logs are written to `/home/kurt/flightalert/flightalert.log`
3. Detected aircraft are logged to `detected_aircraft.txt`
4. Distance calculations use the Haversine formula
5. Email alerts include rich HTML with flight details and tracking links

## Dependencies

- Python 3.12 with venv
- sendgrid (6.11.0)
- python-http-client (3.3.7)
- Standard libraries: socket, json, logging, threading, math

## Testing

No formal test suite exists. Testing is done manually by:
1. Running the service and monitoring logs
2. Checking aircraft detection against known ICAO codes
3. Verifying email delivery

## Common Tasks

### Adding new aircraft to track
1. Edit `aircraft_list.json` directly, or
2. Add to Excel database and run `python merge_plane_data.py`

### Debugging connection issues
- Check dump1090 is running: `nc localhost 30002`
- Review logs: `tail -f /home/kurt/flightalert/flightalert.log`
- Verify config.json has correct credentials

### Updating aircraft information
Use `caf.py` to validate ICAO codes and check blocking status via FlightAware API.

## New Features

### Web Dashboard
Remote monitoring dashboard accessible from anywhere:
```bash
python web_dashboard.py
# Access at http://localhost:5000
```
Features:
- Real-time aircraft tracking from planes.hamm.me
- Distance calculations from home location
- Statistics (total seen, closest approach, etc.)
- Color-coded distance indicators
- Links to FlightAware for each flight

### Flight Pattern Analyzer
Detects interesting patterns and events:
```bash
python flight_analyzer.py
```
Monitors for:
- Emergency squawk codes (7500/7600/7700)
- Unusual maneuvers (circling patterns)
- Rapid altitude changes
- Abnormal speeds
- Aircraft with multiple callsigns

### Remote Monitoring Setup
The application can monitor data from planes.hamm.me (Cloudflare tunnel to local dump1090):
- Web dashboard connects to https://planes.hamm.me/data/aircraft.json
- No local dump1090 required for monitoring
- Can run analytics from any location

## Cleanup Notes

Removed files:
- `fa.py.06102025` (old backup)
- Corrupted empty file

Created:
- `requirements.txt` for dependency management
- `.env.example` for secure credential storage
- `config_manager.py` for centralized configuration
- `web_dashboard.py` and templates for remote monitoring
- `flight_analyzer.py` for pattern detection

Security improvements needed:
- Move API keys from config.json to environment variables
- Implement log rotation for detected_aircraft.txt