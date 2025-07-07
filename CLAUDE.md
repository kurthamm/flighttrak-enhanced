# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlightTrak is a unified real-time aircraft monitoring and alert system that tracks specific aircraft using ADS-B data, performs intelligent pattern analysis, and sends email notifications. The system has been refactored for efficiency and maintainability.

## Refactored Architecture (2025)

The system now consists of these core modules:

### Core Services
- **flight_monitor.py**: Unified monitoring service (replaces multiple fa*.py files)
- **email_service.py**: Centralized Gmail SMTP email handling
- **config_manager.py**: Unified configuration management
- **utils.py**: Shared utility functions

### Intelligence Modules
- **ai_intelligence_service.py**: AI-powered event detection and intelligence
- **anomaly_detector.py**: Flight anomaly detection
- **contextual_intelligence.py**: Context gathering from multiple sources

### Dashboard and Web Interface
- **enhanced_dashboard.py**: Flask web dashboard with real-time updates
- **templates/enhanced_dashboard.html**: Interactive dashboard with maps and analytics

### Data Management
- **aircraft_list.json**: Tracked aircraft database
- **config.json**: System configuration
- **.env**: Environment variables (optional)

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the unified flight monitor (recommended)
python flight_monitor.py

# Run the enhanced dashboard
python enhanced_dashboard.py

# Run AI intelligence service
python ai_intelligence_service.py

# Legacy commands (still work)
python fa_enhanced_v2.py  # Legacy flight alert service
python caf.py             # Aircraft validation
python merge_plane_data.py # Merge Excel data
```

## Configuration

### Unified Configuration (config.json)
```json
{
  "home": {"lat": 34.1133171, "lon": -80.9024019},
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "kurt@hamm.me",
    "password": "app_password",
    "use_tls": true
  },
  "alert_config": {
    "tracked_aircraft_alerts": {"enabled": true, "recipients": ["user@example.com"]},
    "ai_intelligence_alerts": {"enabled": true, "recipients": ["user@example.com"]},
    "anomaly_alerts": {"enabled": true, "recipients": ["user@example.com"]}
  },
  "intelligence_apis": {
    "newsapi_key": "your_key",
    "mapbox_token": "your_token",
    "claude_api_key": "your_key"
  }
}
```

### Environment Variables (optional)
```bash
HOME_LAT=34.1133171
HOME_LON=-80.9024019
EMAIL_SENDER=kurt@hamm.me
EMAIL_PASSWORD=app_password
DASHBOARD_PORT=5030
```

## System Features

### 1. Aircraft Tracking
- Real-time monitoring of tracked aircraft
- Distance calculations from home location
- Rich HTML email alerts with tracking links
- Detection logging to `detected_aircraft.txt`

### 2. Anomaly Detection
- Emergency squawk code detection (7500/7600/7700)
- Rapid altitude/speed changes
- Unusual flight patterns
- Configurable severity levels

### 3. AI Intelligence
- Machine learning pattern recognition
- Multi-source contextual analysis
- Natural language event reporting
- Confidence scoring and thresholds

### 4. Web Dashboard
- Real-time aircraft display
- Interactive maps with Leaflet.js
- Statistics and analytics
- Mobile-responsive design
- Available on port 5030

### 5. Email System
- Gmail SMTP (no more SendGrid costs)
- HTML email templates
- Multi-recipient support
- Service notifications

## Data Sources

### Primary
- **planes.hamm.me**: Remote dump1090 data via Cloudflare tunnel
- **aircraft_list.json**: Tracked aircraft database

### Intelligence Sources
- NewsAPI for aviation news
- Reddit aviation communities
- Weather services
- NOTAM feeds
- MapBox for geographic data

## File Structure

```
flighttrak/
├── Core Services
│   ├── flight_monitor.py      # Unified monitoring
│   ├── email_service.py       # Email handling
│   ├── config_manager.py      # Configuration
│   └── utils.py               # Shared utilities
├── Intelligence
│   ├── ai_intelligence_service.py
│   ├── ai_event_intelligence.py
│   ├── anomaly_detector.py
│   └── contextual_intelligence.py
├── Dashboard
│   ├── enhanced_dashboard.py
│   └── templates/enhanced_dashboard.html
├── Data
│   ├── config.json
│   ├── aircraft_list.json
│   └── detected_aircraft.txt
├── Legacy (kept for compatibility)
│   ├── fa_enhanced_v2.py
│   ├── fa.py
│   └── web_dashboard.py
└── Utilities
    ├── caf.py
    ├── merge_plane_data.py
    └── checkaf.py
```

## Installation and Setup

```bash
# 1. Clone and setup
cd /root/flighttrak
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp config.example.json config.json
# Edit config.json with your settings

# 3. Run services
# Option A: Unified monitor (recommended)
python flight_monitor.py

# Option B: Separate services
python enhanced_dashboard.py &
python ai_intelligence_service.py &

# 4. Access dashboard
# Open http://your-server:5030
```

## Common Tasks

### Adding Aircraft
1. Edit `aircraft_list.json` directly
2. Or use Excel file and run `python merge_plane_data.py`
3. Service will reload automatically

### Troubleshooting
```bash
# Check logs
tail -f flighttrak_monitor.log
tail -f flightalert.log

# Test email
python -c "from email_service import EmailService; from config_manager import config; EmailService(config.get_email_config()).send_email('test@example.com', 'Test', '<h1>Test</h1>')"

# Check configuration
python -c "from config_manager import config; print(config.get('home'))"
```

### Service Management
```bash
# SystemD services
sudo systemctl status flighttrak-dashboard.service
sudo systemctl status flighttrak-ai-intelligence.service

# Manual restart
sudo systemctl restart flighttrak-dashboard.service
```

## API Endpoints

### Dashboard API
- `GET /api/stats` - System statistics
- `GET /api/aircraft` - Current aircraft data
- `GET /api/ai-intelligence` - AI system status

## Security Notes

1. **Email**: Now uses Gmail SMTP with app passwords
2. **API Keys**: Store in environment variables when possible
3. **Logs**: Automatic rotation to prevent disk fill
4. **Access**: Dashboard should be behind reverse proxy in production

## Performance Optimizations

1. **Unified Services**: Reduced memory footprint
2. **Efficient Polling**: Configurable check intervals
3. **Caching**: Aircraft data caching
4. **Database**: SQLite for persistent storage
5. **Async Operations**: Non-blocking email sending

## Migration from Legacy

If migrating from old fa.py system:
1. Update configuration to new format
2. Switch from SendGrid to Gmail SMTP
3. Use `flight_monitor.py` instead of `fa_enhanced_v2.py`
4. Update systemd services to new entry points

## Development

```bash
# Code formatting
black *.py

# Linting  
flake8 *.py

# Testing
pytest tests/

# Dependencies
pip install -r requirements.txt
```

## Refactoring Summary (2025)

### What Was Improved
1. **Eliminated Redundancy**: Consolidated multiple email functions into `email_service.py`
2. **Unified Configuration**: Single `config_manager.py` handles all settings
3. **Shared Utilities**: Common functions moved to `utils.py`
4. **Service Consolidation**: `flight_monitor.py` replaces multiple monitoring scripts
5. **Cost Reduction**: Switched from SendGrid API to Gmail SMTP
6. **Better Error Handling**: Centralized logging and error management
7. **Performance**: Reduced memory usage and improved efficiency

### Legacy Files (Kept for Compatibility)
- `fa.py`, `fa_enhanced.py`, `fa_enhanced_v2.py`: Original flight alert services
- `web_dashboard.py`: Original dashboard (enhanced version recommended)
- Individual utility scripts still work but use refactored core modules

### Testing Commands
```bash
# Test unified monitor
python flight_monitor.py

# Test email service
python -c "
from email_service import EmailService
from config_manager import config
service = EmailService(config.get_email_config())
print('Email service initialized successfully')
"

# Test configuration
python -c "
from config_manager import config
print(f'Home: {config.get_home_coordinates()}')
print(f'Alerts enabled: {config.is_alert_enabled(\"tracked_aircraft\")}')
"
```