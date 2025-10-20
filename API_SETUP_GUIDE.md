# 🚀 FlightTrak Enhanced API Setup Guide

## ⚠️ IMPORTANT UPDATE (October 2025)

**The AI Intelligence System has been deprecated and removed from FlightTrak Enhanced.**

Most of the APIs described in this document are **no longer required** for the core functionality of FlightTrak. The system now focuses on:
- Specific aircraft tracking
- Emergency detection (squawk codes)
- Email alerts
- Twitter/X integration

See [AI_INTELLIGENCE_README.md](AI_INTELLIGENCE_README.md) for details about the deprecation.

---

## Required APIs

### FlightAware API (Required for aircraft validation)
- **URL:** https://flightaware.com/commercial/flightxml/
- **What you get:** Aircraft registration lookups, flight data validation
- **Setup:**
  1. Create a FlightAware account
  2. Subscribe to AeroAPI (has free tier)
  3. Get your API key
  4. Add to config.json: `"flightaware_api_key": "YOUR_KEY_HERE"`
- **Used by:** `caf.py` (Check Aircraft File utility)

### Gmail SMTP (Required for email alerts)
- **URL:** https://myaccount.google.com/apppasswords
- **What you get:** Email alert delivery
- **Setup:**
  1. Enable 2-factor authentication on Gmail
  2. Generate an app password
  3. Add to config.json under `email_config`
- **Used by:** `email_service.py` for all email alerts

### Twitter API v2 (Optional for social media)
- **URL:** https://developer.twitter.com/
- **What you get:** Automated aircraft detection posting
- **Setup:** See [TWITTER_SETUP.md](TWITTER_SETUP.md) for complete guide
- **Used by:** `twitter_poster.py` for social media integration

---

## Deprecated APIs (No Longer Needed)

The following APIs were used by the removed AI Intelligence System and are **no longer necessary** for FlightTrak operation:

### ~~NewsAPI~~ (DEPRECATED)
- **Was used for:** Contextual news correlation for AI event detection
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

### ~~MapBox~~ (DEPRECATED)
- **Was used for:** Enhanced geocoding for AI intelligence
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

### ~~What3Words~~ (DEPRECATED)
- **Was used for:** Precise location descriptions in AI alerts
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

### ~~HERE Maps~~ (DEPRECATED)
- **Was used for:** Professional geocoding and place intelligence
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

### ~~Reddit API~~ (DEPRECATED)
- **Was used for:** Local community discussions and real-time events
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

### ~~Broadcastify~~ (DEPRECATED)
- **Was used for:** Emergency scanner feeds correlation
- **Status:** No longer required
- **Can be removed from:** `config.json` (won't cause errors if left)

---

## Current Configuration

### Minimal Configuration (config.json)

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
    "password": "your_gmail_app_password",
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
  "flightaware_config": {
    "flightaware_api_key": "YOUR_FLIGHTAWARE_KEY"
  },
  "twitter": {
    "enabled": false,
    "dry_run": true,
    "api_key": "YOUR_TWITTER_API_KEY",
    "api_secret": "YOUR_TWITTER_API_SECRET",
    "access_token": "YOUR_TWITTER_ACCESS_TOKEN",
    "access_secret": "YOUR_TWITTER_ACCESS_SECRET",
    "bearer_token": "YOUR_TWITTER_BEARER_TOKEN"
  }
}
```

### Legacy Intelligence APIs Section (Optional)

If you have an existing `intelligence_apis` section in your `config.json`, it can be left in place without causing errors, but it is no longer used:

```json
{
  "intelligence_apis": {
    "newsapi_key": "not_used",
    "mapbox_token": "not_used",
    "here_api_key": "not_used",
    "what3words_key": "not_used",
    "reddit_client_id": "not_used",
    "reddit_client_secret": "not_used",
    "broadcastify_key": "not_used",
    "aviationapi_key": "not_used"
  }
}
```

---

## Setup Priority

### 1. Gmail App Password (REQUIRED)
Set this up first to receive any alerts at all.

**Steps:**
1. Go to https://myaccount.google.com/apppasswords
2. Enable 2FA if not already enabled
3. Generate app password for "Mail"
4. Copy the 16-character password
5. Add to config.json: `"password": "your_app_password"`

### 2. FlightAware API (OPTIONAL)
Only needed if using the aircraft validation utility (`caf.py`).

**Steps:**
1. Sign up at https://flightaware.com
2. Go to https://flightaware.com/commercial/flightxml/
3. Get free tier API key
4. Add to config.json: `"flightaware_api_key": "YOUR_KEY"`

### 3. Twitter API (OPTIONAL)
Only needed if you want to post aircraft detections to social media.

**Steps:**
1. Follow the complete guide in [TWITTER_SETUP.md](TWITTER_SETUP.md)
2. Get developer access at https://developer.twitter.com
3. Add all 5 credentials to config.json
4. Test with `"dry_run": true` first

---

## After Configuration

1. **Restart the service:**
   ```bash
   sudo systemctl restart flightalert.service
   ```

2. **Test email configuration:**
   ```bash
   python -c "
   from email_service import EmailService
   from config_manager import config
   service = EmailService(config.get_email_config())
   print('Gmail SMTP configured successfully')
   "
   ```

3. **Monitor logs:**
   ```bash
   tail -f flighttrak_monitor.log
   ```

---

## What You'll Get

With the minimal configuration (Gmail only):
- ✅ Real-time aircraft detection alerts
- ✅ Emergency squawk code notifications
- ✅ Rich HTML emails with tracking links
- ✅ Distance calculations from your location
- ✅ Web dashboard with interactive maps

With optional Twitter integration:
- ✅ All of the above, plus...
- ✅ Automated social media posting
- ✅ Privacy-respecting delays (24hr for celebrities)
- ✅ Aircraft classification and filtering

---

## 🔒 Security Notes

- **Keep API keys secure** - Don't commit them to git (config.json is in .gitignore)
- **Monitor usage** - Check your API dashboards periodically
- **Gmail app passwords** - Use app passwords, never your actual Gmail password
- **Twitter dry-run** - Always test with `dry_run: true` before going live

---

## 🛠️ Troubleshooting

**"Email not sending"**
- Check Gmail app password is correct
- Verify 2FA is enabled on Gmail account
- Check `smtp_server: "smtp.gmail.com"` and `smtp_port: 587`

**"FlightAware API error"**
- API key only needed for `caf.py` utility
- Core tracking works without FlightAware
- Check key at https://flightaware.com/commercial/aeroapi/portal.rvt

**"Twitter not posting"**
- See [TWITTER_SETUP.md](TWITTER_SETUP.md) for detailed troubleshooting
- Verify all 5 credentials are correct
- Check `enabled: true` and `dry_run: false` for live posting

---

## Migration from Old System

If you have an old `config.json` with unused intelligence APIs:

1. **Keep them** - They won't cause errors
2. **Or remove them** - Clean up the `intelligence_apis` section entirely
3. **Add Twitter** - If you want social media integration (optional)
4. **Test** - Restart service and check logs

The system will ignore unused API keys and continue working with just Gmail SMTP.

---

**Last Updated**: October 2025
**Status**: Simplified configuration (AI intelligence removed)
**Required APIs**: Gmail SMTP only (+ optional Twitter, FlightAware for utilities)
