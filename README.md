# FlightTrak Enhanced 🛩️

A sophisticated real-time aircraft monitoring and alert system with advanced pattern detection capabilities.

## Features

### 🎯 Core Functionality
- **Real-time Aircraft Tracking**: Monitor aircraft using ADS-B data from dump1090
- **Email Alerts**: Get notified when tracked aircraft are detected
- **Distance Calculations**: Monitor aircraft within range of your location
- **Remote Monitoring**: Connect to remote dump1090 instances via Cloudflare tunnels

### 🔍 Advanced Pattern Detection
- **Emergency Detection**: Automatic alerts for emergency squawk codes (7500/7600/7700)
- **Unusual Flight Patterns**: Detect circling, rapid altitude changes, abnormal speeds
- **Behavior Analysis**: Track multiple callsigns, flight duration, and movement patterns
- **Rich Email Alerts**: Beautiful HTML emails with aircraft details and tracking links

### 📊 Web Dashboard
- **Real-time Visualization**: Live aircraft data with color-coded distances
- **Pattern Analysis**: Visual indicators for unusual behavior
- **Event Feed**: Live stream of detected patterns and alerts
- **Statistics**: Track closest approaches, total aircraft seen, and more

### ✈️ Aircraft Tracking
Pre-configured to monitor interesting aircraft including:
- **Government Aircraft**: Air Force One, Marine One
- **Celebrity Jets**: Taylor Swift, Elon Musk, Jeff Bezos, Bill Gates
- **Historic Aircraft**: B-29 FIFI, Ford Trimotor, various warbirds
- **Business Aviation**: Private jets of notable individuals

## Quick Start

### Prerequisites
- Python 3.10+
- dump1090 or remote access to ADS-B data
- SendGrid account for email alerts

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

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Install as system service**
   ```bash
   sudo ./install_service.sh
   ```

5. **Start the service**
   ```bash
   sudo systemctl start flightalert
   ```

## Configuration

### Environment Variables
Create a `.env` file with your configuration:

```env
# FlightAware API
FLIGHTAWARE_API_KEY=your_api_key_here

# SendGrid Email
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_SENDER=your_email@example.com
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Home Location (for distance calculations)
HOME_LAT=34.1133171
HOME_LON=-80.9024019

# Monitoring Settings
ALIVE_INTERVAL=86400
DUMP1090_HOST=127.0.0.1
DUMP1090_PORT=30002
```

### Aircraft List
Edit `aircraft_list.json` to add/remove aircraft you want to track.

## Usage

### Running Components

```bash
# Main tracking service (runs automatically as systemd service)
python3 fa_enhanced.py

# Web dashboard
python3 enhanced_dashboard.py
# Access at http://localhost:5030

# Pattern analyzer (standalone)
python3 flight_analyzer.py

# Aircraft data utilities
python3 caf.py          # Validate aircraft data
python3 checkaf.py      # Check tail numbers
```

### Service Management

```bash
# Service status
sudo systemctl status flightalert

# View logs
sudo journalctl -u flightalert -f
tail -f flightalert.log

# Restart service
sudo systemctl restart flightalert
```

## Pattern Detection

The system automatically detects and alerts on:

- **🚨 Emergency Situations**: Hijack, radio failure, general emergency
- **🔄 Circling Patterns**: Aircraft loitering in small areas
- **📈 Rapid Altitude Changes**: Unusual climb/descent rates
- **⚡ Speed Anomalies**: Very high or suspiciously low speeds
- **🆔 Identity Changes**: Aircraft switching callsigns mid-flight

## Web Dashboard

Access the enhanced dashboard to see:
- Live aircraft positions and data
- Pattern analysis metrics
- Real-time event feed
- Distance-based color coding
- Direct links to FlightAware

## File Structure

```
flighttrak-enhanced/
├── fa_enhanced.py              # Main enhanced service
├── enhanced_dashboard.py       # Web dashboard with patterns
├── flight_analyzer.py          # Standalone pattern analyzer
├── web_dashboard.py           # Basic web dashboard
├── caf.py                     # Aircraft validation utility
├── checkaf.py                 # Tail number checker
├── merge_plane_data.py        # Excel data merger
├── send_service_notification.py # Service notifications
├── config_manager.py          # Centralized configuration
├── aircraft_list.json         # Aircraft to track
├── aircraft_additions.json    # Suggested additions
├── flightalert.service        # systemd service file
├── install_service.sh         # Service installation script
├── templates/                 # HTML templates
│   ├── dashboard.html
│   └── enhanced_dashboard.html
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── CLAUDE.md                 # Development notes
```

## Security Notes

- Never commit API keys or sensitive configuration
- Use environment variables for all credentials
- The `.gitignore` file excludes sensitive files
- Rotate API keys regularly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and personal use. Ensure compliance with:
- Aviation regulations in your jurisdiction
- API terms of service (FlightAware, SendGrid)
- Privacy laws regarding aircraft tracking

## Support

- Check logs in `flightalert.log`
- Review systemd status: `sudo systemctl status flightalert`
- Verify network connectivity to data sources
- Ensure API keys are valid and have proper permissions

---

**Disclaimer**: This software is for educational purposes. Users are responsible for complying with all applicable laws and regulations regarding aircraft tracking and privacy.