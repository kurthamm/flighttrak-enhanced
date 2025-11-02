# FlightTrak 🛩️

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-operational-success)
![ADS-B](https://img.shields.io/badge/ADS--B-dump1090-orange)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20%7C%20Linux-red)

**Real-time ADS-B aircraft tracker** with smart alerts, FlightAware integration, and emergency squawk detection. Built for dump1090 and compatible with FlightRadar24/ADS-B Exchange data sources.

An intelligent aircraft monitoring system that tracks 69 celebrity, government, and historic aircraft using **ADS-B data**. Features smart closest-approach alerting that sends ONE perfectly-timed notification per flyby, eliminating spam while maximizing engagement.

**Status**: ✅ Fully Operational (Updated November 2, 2025)

---

### 🔍 Perfect for:
- **ADS-B enthusiasts** running dump1090/readsb
- **Aviation hobbyists** tracking celebrity/government aircraft
- **FlightAware API users** wanting enhanced local tracking
- **Raspberry Pi projects** for aircraft monitoring
- Anyone interested in **real-time flight tracking** with smart alerts

## 📖 Table of Contents
- [Key Features](#-key-features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Twitter/X Integration](#twitterx-social-media-integration)
- [Emergency Detection](#emergency-detection)
- [Enhanced Email Alerts](#enhanced-email-alerts)
- [Web Dashboard](#enhanced-web-dashboard)
- [System Architecture](#system-architecture)
- [Troubleshooting](#troubleshooting)
- [Recent Updates](#recent-updates-october-2025)

## ⭐ Key Features

### 🎯 Smart Closest-Approach Alerting (NEW!)
- **Problem Solved**: No more spam - previously sent 9 alerts per flyby
- **Intelligent Tracking**: Monitors distance continuously, waits for closest approach
- **Perfect Timing**: ONE alert per aircraft at the most interesting moment
- **24-Hour Cooldown**: Same aircraft won't spam you multiple times per day
- **90% Reduction**: Dramatically reduced alert volume while improving relevance

### 🚨 Intelligent Emergency Detection (NEW!)
- **False-Positive Filtering**: Eliminates fake 7600 alerts during normal landings
- **Airport Awareness**: 40+ major US airports for accurate landing detection
- **Multi-Factor Analysis**: Checks altitude, descent rate, speed, proximity
- **100% Accuracy**: All genuine emergencies (7700, 7500, 7777) still alert

### 📧 Core Monitoring
- **69 Tracked Aircraft**: Government (6), Celebrity (55), Historic (2)
- **Rich HTML Emails**: Distance, tracking links, flight details, maps
- **Multiple Recipients**: Alert 4 family members simultaneously
- **Real-Time Dashboard**: Web interface on port 5030 with live maps
- **Remote Monitoring**: Connect via Cloudflare tunnel (planes.hamm.me)

### 🐦 Twitter/X Integration
- **Privacy-Respecting**: 24-hour delay for celebrities, immediate for historic/government
- **Vague Locations**: State-level only, no exact coordinates
- **Configured & Ready**: Settings in config.json
- **Documentation**: See [TWITTER_SETUP.md](TWITTER_SETUP.md) for setup

### 📊 Enhanced Web Dashboard
- **Interactive Maps**: Live aircraft visualization with Leaflet.js
- **Real-time Statistics**: Color-coded distances and flight analytics
- **24-Hour Tracking**: View aircraft detected in the last 24 hours
- **Flight Data Display**: Altitude, speed, heading, vertical rate
- **Mobile Responsive**: Works on desktop and mobile devices

### ✈️ Aircraft Tracking
Pre-configured to monitor interesting aircraft including:
- **Government Aircraft**: Air Force One, Marine One, military aircraft
- **Celebrity Jets**: Taylor Swift, Elon Musk, Jeff Bezos, Drake
- **Historic Aircraft**: B-29 FIFI, Ford Trimotor, various warbirds
- **Business Aviation**: Private jets of notable individuals

## Quick Start

### Prerequisites
- Python 3.10+
- dump1090 or remote access to ADS-B data
- Gmail account with app password for email alerts
- Twitter Developer account (optional, for social media posting)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kurthamm/flighttrak-enhanced.git
   cd flighttrak-enhanced
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure settings**
   ```bash
   # Edit config.json with your settings
   nano config.json
   ```

4. **Set up Gmail App Password**
   - Enable 2-factor authentication on your Gmail account
   - Generate an app password for FlightTrak
   - Add to config.json under `email_config`

5. **Set up Twitter Integration (Optional)**
   - Follow the guide in [TWITTER_SETUP.md](TWITTER_SETUP.md)
   - Get Twitter API credentials from developer.twitter.com
   - Add credentials to config.json under `twitter` section
   - Enable with `"enabled": true` and test with `"dry_run": true`

6. **Start the service**
   ```bash
   # Start unified monitoring service
   python flight_monitor.py

   # Or run as systemd service
   sudo systemctl start flightalert.service

   # Start enhanced dashboard (separate terminal)
   python enhanced_dashboard.py
   # Access at http://localhost:5030
   ```

## Configuration

### Main Configuration (config.json)
```json
{
  "home": {
    "lat": 34.1133171,
    "lon": -80.9024019
  },
  "email_config": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender": "your_email@gmail.com",
    "password": "your_app_password",
    "use_tls": true,
    "notification_email": "your_email@gmail.com"
  },
  "alert_config": {
    "tracked_aircraft_alerts": {
      "enabled": true,
      "recipients": ["alerts@example.com"]
    },
    "anomaly_alerts": {
      "enabled": true,
      "recipients": ["emergencies@example.com"]
    }
  },
  "twitter": {
    "enabled": false,
    "dry_run": true,
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "access_token": "YOUR_ACCESS_TOKEN",
    "access_secret": "YOUR_ACCESS_SECRET",
    "bearer_token": "YOUR_BEARER_TOKEN"
  }
}
```

### Aircraft List
Edit `aircraft_list.json` to add/remove aircraft you want to track. Each entry includes:
- ICAO hex code
- Tail number (registration)
- Aircraft model
- Owner/operator
- Description

## Usage

### Running Components

```bash
# Unified monitoring service (recommended)
python flight_monitor.py

# Enhanced web dashboard
python enhanced_dashboard.py
# Access at http://localhost:5030

# Utility commands
python caf.py                   # Validate aircraft with FlightAware API
python checkaf.py               # Check tail numbers
python merge_plane_data.py      # Import from Excel spreadsheet
```

### Service Management

```bash
# SystemD services
sudo systemctl status flightalert.service
sudo systemctl status flighttrak-dashboard.service
sudo systemctl restart flightalert.service

# View logs
tail -f flighttrak_monitor.log      # Unified monitor logs
tail -f dashboard.log                # Dashboard logs

# Test email configuration
python -c "
from email_service import EmailService
from config_manager import config
service = EmailService(config.get_email_config())
print('Gmail SMTP configured successfully')
"

# Check configuration
python -c "
from config_manager import config
print(f'Home coordinates: {config.get_home_coordinates()}')
print(f'Email sender: {config.get(\"email.sender\")}')
"
```

## Twitter/X Social Media Integration

FlightTrak can automatically post aircraft detections to Twitter/X with privacy-respecting features:

### What Gets Posted
- **Historic Aircraft**: B-29 FIFI, Ford Trimotor, warbirds (immediate posting)
- **Military/VIP**: Air Force One, government aircraft (immediate posting)
- **Celebrity Jets**: 24-hour delay for privacy protection
- **Location Privacy**: Only state-level location (e.g., "South Carolina area")

### Setup Twitter Integration
See the complete guide: **[TWITTER_SETUP.md](TWITTER_SETUP.md)**

Quick setup:
```bash
# 1. Install dependencies (already in requirements.txt)
pip install tweepy>=4.14.0

# 2. Get Twitter API credentials from developer.twitter.com
# 3. Add credentials to config.json
# 4. Test with dry-run mode first
# 5. Enable live posting when ready
```

### Example Tweets
```
✈️ Commemorative Air Force (FIFI) spotted!
Reg: N529B | Type: Boeing B-29 Superfortress
Alt: 5,000ft | Speed: 180kt
One of only two flying B-29s worldwide
Location: South Carolina
#avgeek #warbird #aviation
```

## Emergency Detection

FlightTrak monitors for aviation emergency codes:

### Emergency Squawk Codes
- **7500**: Hijack Alert - Aircraft has been hijacked
- **7600**: Radio Failure - Lost radio contact with ATC
- **7700**: General Emergency - Aircraft declaring emergency
- **7777**: Military Intercept - Military interception in progress

### Emergency Alerts Include
- Critical severity notification
- Aircraft details (type, registration, owner)
- Current altitude, speed, heading
- Distance from your location
- Multiple tracking links for real-time monitoring

## Enhanced Email Alerts

Email notifications include:
- **Prominent Distance Display**: Large, easy-to-read distance from home
- **Multiple Tracking Links**: FlightAware, ADS-B Exchange, Google Maps
- **Flight Information**: Callsign, altitude, speed, heading, vertical rate
- **Aircraft Details**: Owner, model, registration, ICAO hex
- **Directional Information**: Compass heading with direction (N, NE, E, etc.)
- **Rich HTML Formatting**: Professional, easy-to-read layout

## Enhanced Web Dashboard

Access the dashboard at `http://localhost:5030` to see:
- **Interactive Map**: Live aircraft positions with Leaflet.js
- **24-Hour History**: Aircraft detected in the last 24 hours
- **Statistics Dashboard**: Total tracked, currently airborne, today's detections
- **Distance-based Color Coding**: Visual proximity indicators
- **Flight Details**: Real-time altitude, speed, heading information
- **Direct Tracking Links**: One-click access to external tracking sites

## System Architecture

```
flighttrak/
├── Core Services
│   ├── flight_monitor.py      # Unified monitoring service
│   ├── email_service.py       # Gmail SMTP email handling
│   ├── config_manager.py      # Centralized configuration
│   └── utils.py               # Shared utility functions
├── Detection
│   ├── anomaly_detector.py    # Emergency squawk detection
│   └── twitter_poster.py      # Twitter/X integration (NEW!)
├── Dashboard
│   ├── enhanced_dashboard.py  # Web dashboard
│   └── templates/enhanced_dashboard.html
├── Data
│   ├── aircraft_list.json     # Tracked aircraft database
│   ├── config.json            # System configuration
│   └── detected_aircraft.txt  # Detection log
├── Documentation
│   ├── README.md              # This file
│   ├── CLAUDE.md              # Developer guide
│   ├── TWITTER_SETUP.md       # Twitter integration guide (NEW!)
│   └── API_SETUP_GUIDE.md     # API configuration guide
├── legacy/                    # Archived legacy files
└── Utilities
    ├── caf.py                 # Aircraft validation
    ├── merge_plane_data.py    # Excel data import
    └── checkaf.py             # Tail number checker
```

## Security & Privacy

### 🔒 Email Security
- **Gmail SMTP**: Uses encrypted connection with app passwords
- **No API Costs**: Free Gmail SMTP eliminates per-email charges
- **TLS Encryption**: All email traffic encrypted in transit

### 🐦 Twitter Privacy
- **24-Hour Delays**: Celebrity aircraft posted 24 hours after detection
- **Vague Locations**: State-level only, no exact coordinates
- **No Real-Time Tracking**: Prevents stalking and privacy violations
- **Dry-Run Mode**: Test before posting to verify content

### 🛡️ Configuration Security
- **Environment Variables**: Support for secure credential storage
- **Git Exclusions**: Sensitive files automatically excluded from commits
- **App Passwords**: Use Gmail app passwords instead of main account password
- **Key Rotation**: Easy credential rotation without code changes

### 📋 Compliance
Ensure compliance with:
- Aviation regulations in your jurisdiction
- API terms of service (FlightAware, Gmail, Twitter, etc.)
- Privacy laws regarding aircraft tracking
- Data retention policies
- Twitter Developer Terms of Service

## Troubleshooting

### Gmail SMTP Issues
```bash
# Test Gmail connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_app_password')
print('Gmail SMTP connection successful')
server.quit()
"
```

### Twitter Integration Issues
- **401 Unauthorized**: Check API credentials in config.json
- **403 Forbidden**: Ensure "Elevated" access in Twitter Developer Portal
- **No tweets posted**: Check `enabled: true` and `dry_run: false`
- See [TWITTER_SETUP.md](TWITTER_SETUP.md) for detailed troubleshooting

### Common Issues
- **Email not sending**: Check Gmail app password and 2FA setup
- **No aircraft detected**: Confirm planes.hamm.me accessibility
- **Dashboard not loading**: Check port 5030 availability
- **Service not starting**: Check logs in flighttrak_monitor.log

### Log Analysis
```bash
# Monitor real-time logs
tail -f flighttrak_monitor.log    # Main service
tail -f dashboard.log             # Dashboard

# Check for errors
grep -i error *.log
grep -i "email.*fail" *.log

# Check Twitter posting
grep -i twitter flighttrak_monitor.log
grep "DRY RUN\|Posted tweet" flighttrak_monitor.log
```

## Recent Updates (October 2025)

### Twitter/X Integration
- Complete social media posting system
- Privacy-respecting delays and location handling
- Aircraft classification system
- Dry-run testing mode

### Enhanced Email Alerts
- Prominent distance display
- Multiple tracking links (FlightAware, ADS-B Exchange, Google Maps)
- Directional information with compass headings
- Vertical rate and flight status

### Simplified Architecture
- Removed over-engineered AI intelligence system
- Streamlined anomaly detection (emergency squawks only)
- Updated aircraft database with detailed descriptions
- Improved documentation and setup guides

## Migration from Legacy

If upgrading from the old system:

1. **Update configuration** to use Gmail SMTP format
2. **Generate Gmail app password** and update config
3. **Switch to unified services**: Use `flight_monitor.py` instead of `fa_enhanced_v2.py`
4. **Optional: Set up Twitter integration** following [TWITTER_SETUP.md](TWITTER_SETUP.md)
5. **Update service files** to point to new entry points
6. **Test email delivery** before disabling legacy services

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with your configuration
4. Update documentation as needed
5. Submit a pull request

## Support

- **Configuration**: Check `config_manager.py` for settings validation
- **Email Issues**: Verify Gmail app password and SMTP settings
- **Twitter Issues**: See [TWITTER_SETUP.md](TWITTER_SETUP.md)
- **Network**: Ensure connectivity to planes.hamm.me
- **Documentation**: See [CLAUDE.md](CLAUDE.md) for developer guide

## License

This project is for educational and personal use. Users are responsible for complying with all applicable laws and regulations regarding aircraft tracking, privacy, and social media use.

---

**Disclaimer**: This software is for educational purposes. Users are responsible for complying with all applicable laws and regulations regarding aircraft tracking, privacy, and social media terms of service. ADS-B data is publicly broadcast, but respect privacy by implementing appropriate delays and vague location reporting when sharing information publicly.
