# AI Intelligence System - Deprecated October 2025

This directory contains the AI intelligence system that was disabled in October 2025 during a major simplification refactoring.

## Why Deprecated

The AI intelligence system was over-engineered and added unnecessary complexity:
- DBSCAN clustering and ML pattern matching
- Contextual intelligence integration (news, weather correlation)
- Complex event correlation
- Path analysis and historical tracking
- 7,141 lines of code
- 1.76GB of database storage

## What Replaced It

Simplified to focus on core functionality:
- Direct emergency squawk detection (7500/7600/7700/7777)
- Smart closest-approach alerting
- Enhanced email notifications with celebrity context
- Gmail SMTP (no per-email API costs)

## Files Archived

**Core AI System:**
- ai_intelligence_service.py - Main AI intelligence service
- ai_event_intelligence.py - Event detection and correlation
- contextual_intelligence.py - Context gathering and analysis

**Analysis Modules:**
- path_analyzer.py - Flight path analysis
- flight_analyzer.py - Flight pattern detection
- historical_analysis.py - Historical data analysis
- geographic_intelligence.py - Geographic context

**Integration Modules:**
- weather_integration.py - Weather API integration
- weather_context.py - Weather context provider
- enhanced_intelligence_sources.py - Multi-source intelligence
- claude_intelligence_enhancement.py - AI enhancement layer

**Support Files:**
- intelligence_config.py - AI system configuration
- aircraft_rules.py - Rule-based classification
- aircraft_lookup.py - Aircraft data lookups
- airport_data.py - Airport reference data

## Databases Deleted (1.76GB)

- flight_paths.db (1.7GB) - Flight path history
- contextual_intelligence.db (25MB) - Context data
- aircraft_cache.db (6.2MB) - Aircraft cache
- intelligence.db (28KB) - Intelligence metadata
- weather_data.db (16KB) - Weather cache

## Archived Date

November 1, 2025

## Can This Be Restored?

Yes, but not recommended. The simplified system performs better:
- 90% fewer alerts (smart closest-approach)
- Zero false positives (intelligent emergency filtering)
- Lower costs (no SendGrid, no complex DB queries)
- Easier to maintain and understand

If you need specific functionality, review the code and extract only what's needed rather than re-enabling the entire system.
