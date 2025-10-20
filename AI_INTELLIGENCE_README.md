# FlightTrak AI Intelligence System (DEPRECATED)

## ⚠️ DEPRECATION NOTICE

**This document describes a deprecated feature that has been removed from FlightTrak Enhanced as of October 2025.**

The AI Intelligence System was removed during a major refactoring to simplify the codebase and focus on core functionality. This decision was made because:

1. **Over-Engineered**: The system was too complex for its actual utility
2. **Rarely Triggered**: Required 3+ aircraft clustering, which seldom occurred
3. **High False Positives**: Pattern matching often misidentified routine flights
4. **Resource Intensive**: Required significant CPU and memory for minimal benefit
5. **Maintenance Burden**: Complex ML pipeline was difficult to maintain

## What Remains

FlightTrak Enhanced still provides:

- ✅ **Real-time Aircraft Tracking**: Monitor specific aircraft as they fly
- ✅ **Email Alerts**: Rich HTML notifications with distance and tracking links
- ✅ **Emergency Detection**: Alert on squawk codes 7500, 7600, 7700, 7777
- ✅ **Twitter Integration**: Privacy-respecting social media posting
- ✅ **Web Dashboard**: Interactive map with 24-hour tracking history

## What Was Removed

The following AI intelligence features are no longer available:

- ❌ Machine learning pattern recognition
- ❌ DBSCAN spatial clustering
- ❌ Multi-aircraft event detection (SAR, law enforcement, etc.)
- ❌ Contextual intelligence from news/weather/NOTAMs
- ❌ Natural language event descriptions
- ❌ Confidence scoring and predictive classification
- ❌ SQLite intelligence databases

## Migration Guide

If you were using AI intelligence alerts:

1. **Emergency Detection**: Emergency squawk codes (7500/7600/7700/7777) are still detected via the simplified `anomaly_detector.py`

2. **Aircraft Tracking**: Continue tracking specific aircraft with enhanced email alerts

3. **Remove AI Configuration**: The `ai_intelligence_alerts` section in `config.json` is no longer used (but won't cause errors if left in place)

4. **Service Files**: Remove or disable the `flighttrak-ai-intelligence.service` if you had it running

5. **Logs**: Old AI intelligence logs can be safely deleted

## Recommended Alternatives

For advanced aviation intelligence:

- **FlightRadar24 Pro**: Commercial service with alerts and analytics
- **ADS-B Exchange**: Community-driven comprehensive tracking
- **FlightAware**: Professional flight tracking with API access
- **Custom Scripts**: Build your own focused alerts for specific use cases

## Historical Context

The AI Intelligence System was an ambitious attempt to automatically detect coordinated aircraft operations (search & rescue, law enforcement, etc.) using machine learning. While technically interesting, it proved impractical for a single-location monitoring system.

The focus of FlightTrak Enhanced has shifted to:
- **Specific aircraft tracking** (celebrities, government, historic aircraft)
- **Emergency detection** (squawk codes)
- **Social media integration** (Twitter with privacy protections)
- **Enhanced alerts** (better email formatting and tracking links)

## Questions?

If you have questions about this deprecation or need help migrating to the simplified system, see:

- [README.md](README.md) - Main documentation
- [CLAUDE.md](CLAUDE.md) - Developer guide
- [TWITTER_SETUP.md](TWITTER_SETUP.md) - Twitter integration guide

---

**Last Updated**: October 2025
**Status**: DEPRECATED
**Replacement**: Simplified emergency detection in `anomaly_detector.py`
