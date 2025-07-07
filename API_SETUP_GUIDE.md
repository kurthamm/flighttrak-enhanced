# 🚀 FlightTrak Enhanced Intelligence API Setup Guide

## 🎯 Quick Start (Get These First!)

### 1. NewsAPI (500 free requests/day) - **PRIORITY 1**
- **URL:** https://newsapi.org/register
- **What you get:** Comprehensive news aggregation from 80,000+ sources
- **Setup:** 
  1. Sign up with email
  2. Get your API key
  3. Add to config.json: `"newsapi_key": "YOUR_KEY_HERE"`

### 2. MapBox (100k free requests/month) - **PRIORITY 2**
- **URL:** https://account.mapbox.com/auth/signup/
- **What you get:** Enhanced geocoding, place data, demographics
- **Setup:**
  1. Sign up with email
  2. Go to Account → Access Tokens
  3. Copy your default public token
  4. Add to config.json: `"mapbox_token": "YOUR_TOKEN_HERE"`

### 3. What3Words (1k free requests/day) - **PRIORITY 3**
- **URL:** https://developer.what3words.com/public-api
- **What you get:** Precise 3-word location addresses (e.g., "filled.count.soap")
- **Setup:**
  1. Sign up for developer account
  2. Create a new API key
  3. Add to config.json: `"what3words_key": "YOUR_KEY_HERE"`

## 🔧 Additional Services (Optional but Recommended)

### 4. HERE Maps (1k free requests/day)
- **URL:** https://developer.here.com/sign-up
- **What you get:** Professional geocoding, traffic data, place details
- **Setup:**
  1. Sign up for HERE developer account
  2. Create a project
  3. Generate API key
  4. Add to config.json: `"here_api_key": "YOUR_KEY_HERE"`

### 5. Reddit API (60 requests/minute)
- **URL:** https://www.reddit.com/prefs/apps
- **What you get:** Local community discussions, breaking news, real-time events
- **Setup:**
  1. Create Reddit app at the URL above
  2. Choose "script" type
  3. Get your client ID and secret
  4. Add to config.json:
     ```json
     "reddit_client_id": "YOUR_CLIENT_ID",
     "reddit_client_secret": "YOUR_CLIENT_SECRET"
     ```

### 6. Broadcastify (Emergency Scanner Feeds)
- **URL:** https://www.broadcastify.com/developer/
- **What you get:** Live emergency scanner feeds, dispatch audio
- **Note:** Currently limited availability, contact Broadcastify for API access

## 📝 Configuration File Location

Edit: `/root/flighttrak/config.json`

Look for the `intelligence_apis` section:

```json
{
  "intelligence_apis": {
    "newsapi_key": "YOUR_NEWSAPI_KEY_HERE",
    "mapbox_token": "YOUR_MAPBOX_TOKEN_HERE", 
    "here_api_key": "YOUR_HERE_API_KEY_HERE",
    "what3words_key": "YOUR_WHAT3WORDS_KEY_HERE",
    "reddit_client_id": "YOUR_REDDIT_CLIENT_ID_HERE",
    "reddit_client_secret": "YOUR_REDDIT_CLIENT_SECRET_HERE",
    "broadcastify_key": "YOUR_BROADCASTIFY_KEY_HERE",
    "aviationapi_key": "YOUR_AVIATIONAPI_KEY_HERE"
  }
}
```

## 🚀 After Adding API Keys

1. **Restart the service:**
   ```bash
   systemctl restart flighttrak-ai-intelligence
   ```

2. **Check that services are active:**
   ```bash
   python3 intelligence_config.py
   ```

3. **Monitor logs for enhanced intelligence:**
   ```bash
   tail -f ai_intelligence_service.log | grep -E "(Enhanced|Intelligence)"
   ```

## 💡 What You'll Get With Each Service

| Service | Location Data | News Coverage | Special Features |
|---------|---------------|---------------|------------------|
| **Free (Always Active)** | ✅ Basic address | ✅ Google News RSS | OpenStreetMap, Overpass API |
| **+ NewsAPI** | ✅ Basic address | ✅✅✅ 80k+ sources | Breaking news, incident reports |
| **+ MapBox** | ✅✅✅ Enhanced geocoding | ✅ Google News RSS | Demographics, neighborhoods |
| **+ What3Words** | ✅✅✅ Precise 3-word address | ✅ Google News RSS | Exact location sharing |
| **+ HERE Maps** | ✅✅✅ Professional geocoding | ✅ Google News RSS | Traffic, detailed places |
| **+ Reddit API** | ✅✅✅ Enhanced | ✅✅ Local communities | Real-time local discussions |

## 🎯 Enhanced Alert Example

With all APIs configured, your alerts will include:

```
📍 Location Intelligence
Location: 123 Main Street, Downtown District, San Francisco, CA
Place Type: Commercial Area, High-Rise Building
Risk Assessment: HIGH
What3Words: filled.count.soap
Nearby Landmarks:
• San Francisco General Hospital (0.3 mi)
• City Hall (0.5 mi) 
• Financial District (0.7 mi)

📰 Related News (5 sources)
🚨 "Emergency response underway in downtown SF"
   Source: KTVU Fox 2 (Relevance: 0.9) | 🔗 Read Article

📍 "Multiple agencies responding to incident on Main St"
   Source: Reddit r/sanfrancisco (Relevance: 0.8) | 🔗 Read Article

⚠️ "Traffic advisory: Downtown area closed"
   Source: SF Chronicle (Relevance: 0.7) | 🔗 Read Article
```

## 🔒 Security Notes

- **Keep API keys secure** - Don't commit them to git
- **Monitor usage** - Check your API dashboards periodically  
- **Rate limits** - The system automatically respects API rate limits
- **Fallbacks** - System works with just free sources if APIs fail

## 🛠️ Troubleshooting

**"HTTP 401 Unauthorized"** = Invalid API key
**"HTTP 429 Too Many Requests"** = Rate limit exceeded (system will pause)
**"Geographic Intelligence not available"** = All API keys missing (basic mode)
**"Enhanced Intelligence not available"** = Module import error

Start with NewsAPI and MapBox - they provide the biggest intelligence boost!