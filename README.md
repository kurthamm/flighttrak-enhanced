# FlightTrak Enhanced 🛩️

A sophisticated real-time aircraft monitoring and alert system with AI-powered intelligence and pattern detection capabilities.

## Features

### 🎯 Core Functionality  
- **Real-time Aircraft Tracking**: Monitor aircraft using ADS-B data from dump1090
- **Smart Email Alerts**: Gmail SMTP notifications when tracked aircraft are detected
- **Distance Calculations**: Monitor aircraft within range of your location
- **Remote Monitoring**: Connect to remote dump1090 instances via Cloudflare tunnels

### 🧠 AI Intelligence & Pattern Detection
- **Emergency Detection**: Automatic alerts for emergency squawk codes (7500/7600/7700)
- **AI Event Analysis**: Machine learning pattern recognition with confidence scoring
- **Anomaly Detection**: Detect circling, rapid altitude changes, abnormal speeds
- **Contextual Intelligence**: Multi-source data correlation (news, weather, NOTAMs)
- **Rich Email Alerts**: Beautiful HTML emails with aircraft details and tracking links

### 📊 Enhanced Web Dashboard
- **Interactive Maps**: Live aircraft visualization with Leaflet.js
- **Real-time Statistics**: Color-coded distances and flight analytics
- **AI Intelligence Status**: Monitor AI system health and detection confidence
- **Event Feed**: Live stream of detected patterns and AI alerts
- **Mobile Responsive**: Works on desktop and mobile devices

### ✈️ Aircraft Tracking
Pre-configured to monitor interesting aircraft including:
- **Government Aircraft**: Air Force One, Marine One, military aircraft
- **Celebrity Jets**: Taylor Swift, Elon Musk, Jeff Bezos, Bill Gates
- **Historic Aircraft**: B-29 FIFI, Ford Trimotor, various warbirds
- **Business Aviation**: Private jets of notable individuals

## Quick Start

### Prerequisites
- Python 3.10+
- dump1090 or remote access to ADS-B data
- Gmail account with app password for email alerts

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/flighttrak-enhanced.git
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
   cp config.example.json config.json
   # Edit config.json with your settings and Gmail credentials
   ```

4. **Set up Gmail App Password**
   - Enable 2-factor authentication on your Gmail account
   - Generate an app password for FlightTrak
   - Use this app password in your configuration

5. **Start the unified monitoring service**
   ```bash
   # Option A: Run unified monitor (recommended)
   python flight_monitor.py
   
   # Option B: Run services separately
   python enhanced_dashboard.py &    # Dashboard on port 5030
   python ai_intelligence_service.py # AI intelligence
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
    "ai_intelligence_alerts": {
      "enabled": true,
      "recipients": ["ai_alerts@example.com"],
      "min_confidence": 0.6
    },
    "anomaly_alerts": {
      "enabled": true,
      "recipients": ["anomaly_alerts@example.com"]
    }
  },
  "intelligence_apis": {
    "newsapi_key": "your_newsapi_key",
    "mapbox_token": "your_mapbox_token",
    "claude_api_key": "your_claude_key"
  }
}
```

### Environment Variables (Optional)
You can also use environment variables to override config.json:

```env
# Gmail Configuration
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Home Location
HOME_LAT=34.1133171
HOME_LON=-80.9024019

# Dashboard
DASHBOARD_PORT=5030
```

### Aircraft List
Edit `aircraft_list.json` to add/remove aircraft you want to track.

## Usage

### Running Components

```bash
# Unified monitoring service (recommended)
python flight_monitor.py

# Enhanced web dashboard with AI intelligence
python enhanced_dashboard.py
# Access at http://localhost:5030

# AI intelligence service (if running separately)  
python ai_intelligence_service.py

# Utility commands
python caf.py          # Validate aircraft data with FlightAware API
python checkaf.py      # Check tail numbers in aircraft list
python merge_plane_data.py  # Import from Excel spreadsheet

# Legacy services (if needed)
python legacy/fa_enhanced_v2.py  # Legacy flight monitoring
python legacy/web_dashboard.py   # Basic dashboard
```

### Service Management

```bash
# View logs
tail -f flighttrak_monitor.log     # Unified monitor logs
tail -f flightalert.log            # Legacy service logs
tail -f dashboard_enhanced.log     # Dashboard logs

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

## AI Intelligence & Pattern Detection

The system features advanced AI-powered analysis:

### 🧠 AI Event Detection
- **Machine Learning Classification**: Pattern recognition with confidence scoring
- **Multi-Source Intelligence**: News, weather, and aviation data correlation
- **Natural Language Reporting**: AI-generated event summaries
- **Configurable Thresholds**: Adjust confidence levels for alerts

### 🔍 Anomaly Detection
- **🚨 Emergency Situations**: Hijack, radio failure, general emergency (7500/7600/7700)
- **🔄 Circling Patterns**: Aircraft loitering in small areas
- **📈 Rapid Altitude Changes**: Unusual climb/descent rates
- **⚡ Speed Anomalies**: Very high or suspiciously low speeds
- **🆔 Identity Changes**: Aircraft switching callsigns mid-flight

### 📊 Contextual Intelligence
- **News Correlation**: Aviation incident news matching
- **Weather Integration**: Weather impact analysis
- **Geographic Analysis**: Location-based intelligence
- **Historical Patterns**: Learning from past events

## Enhanced Web Dashboard

Access the dashboard at `http://localhost:5030` to see:
- **Interactive Map**: Live aircraft positions with Leaflet.js
- **AI Intelligence Status**: Real-time AI system monitoring
- **Pattern Analysis Metrics**: Anomaly detection results
- **Event Feed**: Live stream of AI alerts and detections
- **Distance-based Color Coding**: Visual proximity indicators
- **Flight Tracking Links**: Direct links to FlightAware, FlightRadar24, ADS-B Exchange

## Unified Architecture

```
flighttrak/
├── Core Services
│   ├── flight_monitor.py      # Unified monitoring service
│   ├── email_service.py       # Gmail SMTP email handling
│   ├── config_manager.py      # Centralized configuration
│   └── utils.py               # Shared utility functions
├── Intelligence
│   ├── ai_intelligence_service.py # AI event detection
│   ├── ai_event_intelligence.py   # ML pattern engine
│   ├── anomaly_detector.py        # Anomaly detection
│   └── contextual_intelligence.py # Multi-source analysis
├── Dashboard
│   ├── enhanced_dashboard.py      # Web dashboard
│   └── templates/enhanced_dashboard.html
├── Data
│   ├── aircraft_list.json         # Tracked aircraft
│   └── config.json               # System configuration
├── legacy/                        # Archived legacy files
└── Utilities
    ├── caf.py                     # Aircraft validation
    ├── merge_plane_data.py        # Excel data import
    └── checkaf.py                 # Tail number checker
```

## Security & Privacy

### 🔒 Email Security
- **Gmail SMTP**: Uses encrypted connection with app passwords
- **No API Costs**: Free Gmail SMTP eliminates per-email charges
- **TLS Encryption**: All email traffic encrypted in transit

### 🛡️ Configuration Security
- **Environment Variables**: Support for secure credential storage
- **Git Exclusions**: Sensitive files automatically excluded from commits
- **App Passwords**: Use Gmail app passwords instead of main account password
- **Key Rotation**: Easy credential rotation without code changes

### 📋 Compliance
Ensure compliance with:
- Aviation regulations in your jurisdiction
- API terms of service (FlightAware, Gmail, etc.)
- Privacy laws regarding aircraft tracking
- Data retention policies

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

### Common Issues
- **Email not sending**: Check Gmail app password and 2FA setup
- **AI intelligence offline**: Verify Claude API key and internet connection
- **No aircraft detected**: Confirm planes.hamm.me accessibility
- **Dashboard not loading**: Check port 5030 availability

### Log Analysis
```bash
# Monitor real-time logs
tail -f flighttrak_monitor.log    # Main service
tail -f dashboard_enhanced.log    # Dashboard
tail -f ai_intelligence_service.log # AI system

# Check for errors
grep -i error *.log
grep -i "email.*fail" *.log
```

## Migration from Legacy

If upgrading from the old SendGrid-based system:

1. **Update configuration** to use Gmail SMTP format
2. **Generate Gmail app password** and update config
3. **Switch to unified services**: Use `flight_monitor.py` instead of `fa_enhanced_v2.py`
4. **Update service files** to point to new entry points
5. **Test email delivery** before disabling legacy services

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with your Gmail configuration
4. Ensure all documentation reflects Gmail usage
5. Submit a pull request

## Support

- **Configuration**: Check `config_manager.py` for settings validation
- **Email Issues**: Verify Gmail app password and SMTP settings
- **AI Intelligence**: Monitor AI service logs for detection confidence
- **Network**: Ensure connectivity to planes.hamm.me and API endpoints

---

**Disclaimer**: This software is for educational purposes. Users are responsible for complying with all applicable laws and regulations regarding aircraft tracking and privacy.