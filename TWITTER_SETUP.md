# Twitter/X Integration Setup Guide

## Overview

FlightTrak can automatically post interesting aircraft detections to Twitter/X with privacy-respecting delays and filters. This feature is designed to share public aviation information responsibly while respecting privacy concerns.

## What Gets Posted

### Aircraft Categories

1. **Historic Aircraft** (Post Immediately)
   - Rare warbirds (B-29 FIFI, Ford Trimotor, etc.)
   - Vintage aircraft on tour
   - Museum pieces in flight
   - Example: "✈️ B-29 FIFI spotted! #warbird #avgeek"

2. **Military/VIP** (Post Immediately)
   - Air Force One
   - Other government VIP aircraft
   - Already public information
   - Example: "🇺🇸 Air Force One detected #AirForceOne #POTUS"

3. **Celebrity Aircraft** (24-Hour Delay)
   - Taylor Swift, Elon Musk, Drake, etc.
   - Posted 24 hours after detection for privacy
   - Vague location only ("South Carolina area")
   - No exact coordinates
   - Example: "✈️ Taylor Swift's Falcon 7X was in the South Carolina area. Detected: January 15, 2025"

4. **Government** (2-Hour Delay)
   - Other government aircraft
   - Short delay with vague location

5. **Skip** (Never Posted)
   - Most regular tracked aircraft
   - Default: don't post unless specifically classified

## Privacy Features

- **24-hour delay** for celebrity aircraft (following Jack Sweeney's approach)
- **Vague locations** only ("Over South Carolina" vs exact coordinates)
- **No real-time tracking** of private individuals
- **Dry-run mode** by default (test before posting)
- **Classification system** prevents accidental posting of sensitive aircraft

## Installation

### 1. Install tweepy Library

```bash
cd /home/kurt/flighttrak
source venv/bin/activate
pip install tweepy>=4.14.0
```

### 2. Get Twitter API Credentials

You need to apply for Twitter Developer access:

1. Go to https://developer.twitter.com/
2. Create a Developer Account (Free tier is sufficient)
3. Create a new Project and App
4. Generate credentials:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Access Token
   - Access Token Secret
   - Bearer Token

**Important**: Apply for "Elevated" access to enable write permissions (posting tweets).

### 3. Configure Credentials

Edit `/home/kurt/flighttrak/config.json`:

```json
"twitter": {
  "enabled": false,           // Set to true when ready to post
  "dry_run": true,            // Keep true for testing
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET",
  "access_token": "YOUR_ACCESS_TOKEN",
  "access_secret": "YOUR_ACCESS_SECRET",
  "bearer_token": "YOUR_BEARER_TOKEN",
  "post_historic": true,
  "post_military_vip": true,
  "post_celebrity": true,
  "celebrity_delay_hours": 24
}
```

## Testing

### Phase 1: Dry-Run Mode (Recommended)

Keep `dry_run: true` to see what would be posted without actually posting:

```bash
# Restart the service
sudo systemctl restart flightalert.service

# Watch the logs for dry-run posts
tail -f flighttrak_monitor.log | grep "DRY RUN"
```

You'll see output like:
```
[DRY RUN] Would post tweet:
✈️ B-29 FIFI spotted!
Reg: N529B | Type: Boeing B-29 Superfortress
Alt: 5,000ft | Speed: 180kt
One of only two flying B-29s worldwide
Location: South Carolina
#avgeek #warbird #aviation
```

### Phase 2: Enable Posting

Once satisfied with dry-run output:

1. Set `dry_run: false` in config.json
2. Set `enabled: true` in config.json
3. Restart service: `sudo systemctl restart flightalert.service`

## Aircraft Classification

The system automatically classifies aircraft based on `aircraft_list.json`:

```python
# Classification logic in twitter_poster.py
if 'fifi' in description or 'b-29' in model or 'trimotor' in model:
    classification = 'historic'
elif 'air force one' in owner or 'marine one' in owner:
    classification = 'military_vip'
elif any(celeb in owner for celeb in ['swift', 'musk', 'bezos', 'kardashian', 'drake', 'trump', 'gates']):
    classification = 'celebrity'
elif 'government' in owner:
    classification = 'government'
else:
    classification = 'skip'  # Don't post by default
```

## Tweet Format Examples

### Historic Aircraft
```
✈️ Commemorative Air Force (FIFI) spotted!
Reg: N529B | Type: Boeing B-29 Superfortress
Alt: 5,000ft | Speed: 180kt
One of only two flying B-29s worldwide - Historic WWII bomber on AirPower Tour
Location: South Carolina
#avgeek #warbird #aviation
```

### Military VIP
```
🇺🇸 U.S. Air Force (Air Force One) detected
ICAO: ADFDF8 | Tail: 82-8000
Alt: 35,000ft | Speed: 450kt
Location: South Carolina
#AirForceOne #POTUS #aviation
```

### Celebrity (24-hour delay)
```
✈️ Taylor Swift's Dassault Falcon 7X was in the South Carolina area
Reg: N621MM
Detected: January 15, 2025
#avgeek #aviation
```

## Monitoring

### Check Twitter Queue
```bash
# See queued posts waiting for delay
tail -f flighttrak_monitor.log | grep "Queued Twitter post"
```

Output:
```
Queued Twitter post for Taylor Swift (A47CB5) - posting in 24h
Queued Twitter post for Commemorative Air Force (FIFI) (A6AA76) - posting immediately
```

### Check Posted Tweets
```bash
# See successful posts
tail -f flighttrak_monitor.log | grep "Posted tweet"
```

## Safety Features

1. **Dry-run mode default**: System defaults to `dry_run: true` even if `enabled: true`
2. **Character limit**: Tweets automatically truncated to 280 characters
3. **Classification required**: Only classified aircraft get posted
4. **Queue system**: Delayed posts stored in memory queue
5. **Error handling**: Failed posts logged but don't crash the service

## Troubleshooting

### No tweets being posted
- Check `enabled: true` and `dry_run: false` in config.json
- Verify Twitter API credentials are correct
- Check logs: `tail -f flighttrak_monitor.log`
- Verify tweepy is installed: `pip show tweepy`

### Authentication errors
```
ERROR:root:Failed to initialize Twitter API: 401 Unauthorized
```
- Verify API credentials in config.json
- Ensure you have "Elevated" access in Twitter Developer Portal
- Regenerate tokens if needed

### Import errors
```
WARNING:root:tweepy not installed - Twitter posting disabled
```
- Install tweepy: `pip install tweepy>=4.14.0`
- Verify virtual environment is activated

### No aircraft being queued
- Check aircraft classifications in `aircraft_list.json`
- Most aircraft default to 'skip' category
- Add keywords like 'historic', 'government', celebrity names to owner/description fields

## Advanced Configuration

### Customize Delays
Edit `twitter_poster.py` AIRCRAFT_CATEGORIES:

```python
AIRCRAFT_CATEGORIES = {
    'celebrity': {
        'delay_hours': 48,  # Change from 24 to 48 hours
        ...
    }
}
```

### Add Custom Classifications
Edit `twitter_poster.py` _load_aircraft_classifications():

```python
elif 'specific_owner' in owner.lower():
    classifications[icao] = 'historic'
```

### Customize Tweet Format
Edit `twitter_poster.py` _generate_tweet_text():

```python
if category == 'historic':
    tweet = f"🛩️ {owner} overhead!\n"  # Custom emoji and text
```

## Legal and Ethical Considerations

1. **Public Data**: All ADS-B data is publicly broadcast and available
2. **Privacy Delays**: 24-hour delays for private individuals
3. **Vague Locations**: Never post exact coordinates for private aircraft
4. **Following Precedent**: Based on @ElonJet and similar accounts
5. **Twitter ToS**: Ensure compliance with Twitter's Terms of Service

## Support

For issues with Twitter integration:
1. Check logs: `tail -f flighttrak_monitor.log`
2. Test in dry-run mode first
3. Review Twitter Developer documentation: https://developer.twitter.com/docs

## References

- Jack Sweeney's approach to celebrity aircraft tracking
- Twitter API v2 documentation: https://developer.twitter.com/en/docs/twitter-api
- tweepy documentation: https://docs.tweepy.org/
