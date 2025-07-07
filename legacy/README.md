# Legacy Files

This directory contains legacy FlightTrak files that have been replaced by the unified architecture (2025 refactoring).

## Files

### Legacy Flight Alert Services
- **fa.py**: Original flight alert service (basic ADS-B monitoring)
- **fa_enhanced.py**: Enhanced version with pattern detection
- **fa_enhanced_v2.py**: Latest legacy version with Gmail SMTP

**Replaced by**: `flight_monitor.py` (unified monitoring service)

### Legacy Dashboard
- **web_dashboard.py**: Original web dashboard
- **dashboard.html**: Original dashboard template

**Replaced by**: `enhanced_dashboard.py` with `templates/enhanced_dashboard.html`

### Broken/Temporary Files
- **ai_event_intelligence.py.broken**: Broken AI intelligence module

## Migration Notes

These files are kept for reference but should not be used in production. The new unified architecture provides:

- Better performance and reduced memory usage
- Centralized configuration and error handling  
- Elimination of code duplication
- Gmail SMTP instead of SendGrid API (cost savings)
- Improved maintainability

## If You Need Legacy Functionality

If you need to run legacy services temporarily:

```bash
# From the legacy directory
python fa_enhanced_v2.py  # Latest legacy flight monitor
python web_dashboard.py   # Legacy dashboard
```

However, it's recommended to use the new unified services:

```bash
# From the main directory  
python flight_monitor.py     # Unified monitoring
python enhanced_dashboard.py # Enhanced dashboard
```