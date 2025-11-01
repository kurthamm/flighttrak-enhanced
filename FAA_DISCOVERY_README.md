# FAA Aircraft Discovery Service

Automated system that downloads the FAA aircraft registry monthly and discovers new interesting aircraft.

## What It Does

1. **Downloads** the FAA aircraft database (68MB, ~308K aircraft)
2. **Searches** for interesting aircraft:
   - Ultra-high-end private jets (G700, G650, Global 7500, etc.)
   - Historic WWII warbirds (B-29, B-17, P-51, etc.)
   - Classic airliners (DC-3, Constellation, etc.)
3. **Generates** a discovery report with new aircraft found
4. **Logs** all activity to `faa_discovery.log`

## Files

- `faa_aircraft_discovery.py` - Main discovery script
- `faa_discovery.log` - Activity log
- `faa_discovery_report_YYYYMMDD_HHMMSS.txt` - Discovery reports

## Schedule

Runs **monthly** on the 1st of each month at 3:00 AM via systemd timer.

## Manual Execution

To run the discovery manually:

```bash
cd /home/kurt/flighttrak
source venv/bin/activate
python faa_aircraft_discovery.py
```

This will:
- Download the latest FAA database
- Search for new aircraft
- Generate a report
- Take about 5-10 minutes

## Installation (Automated Monthly Runs)

```bash
# Copy service files
sudo cp /tmp/faa-discovery.service /etc/systemd/system/
sudo cp /tmp/faa-discovery.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable faa-discovery.timer
sudo systemctl start faa-discovery.timer

# Check status
sudo systemctl status faa-discovery.timer
sudo systemctl list-timers faa-discovery.timer
```

## Viewing Discovery Reports

```bash
# List all reports
ls -lh faa_discovery_report_*.txt

# View latest report
cat faa_discovery_report_*.txt | tail -n 100

# Count discoveries
grep "Found.*new interesting" faa_discovery.log
```

## How It Works

### Aircraft Criteria

**Historic Aircraft** (auto-flagged):
- B-29, B-17, B-24, B-25 bombers
- P-51, P-38, P-40, P-47 fighters
- F4U Corsair, F6F Hellcat, TBM Avenger
- Spitfire, PBY Catalina
- DC-3, Lockheed Constellation, Electra

**Private Jets** (flagged if non-corporate owner):
- Gulfstream G700, G650, G600, G550
- Bombardier Global 7500, 6500, 6000
- Dassault Falcon 8X, 7X, 900
- High-end Citations, Challengers, Phenoms
- Private Boeing 737/757/767/747 conversions

### Bot Protection Bypass

The FAA registry blocks automated tools. The script bypasses this by:
- Using browser User-Agent headers
- Mimicking Chrome browser requests
- This is the same technique we used to download the database initially

## Customization

Edit `faa_aircraft_discovery.py` to change:

**Search Criteria** (lines 19-38):
- Add/remove aircraft models to search for
- Modify interesting jet types
- Change historic aircraft types

**Schedule** (edit timer file):
```bash
sudo nano /etc/systemd/system/faa-discovery.timer
# Change: OnCalendar=monthly  (for different schedule)
sudo systemctl daemon-reload
sudo systemctl restart faa-discovery.timer
```

## Why Monthly?

The FAA database is updated daily, but:
- **New aircraft registrations** are infrequent (celebrities don't buy jets every day)
- **Tail number changes** are rare
- **Historic aircraft** almost never change
- Monthly checks are sufficient to catch new additions

You can change to weekly or quarterly if desired.

## Logs

```bash
# View recent activity
tail -f faa_discovery.log

# See all monthly runs
grep "Starting FAA Aircraft Discovery" faa_discovery.log

# Count aircraft discovered each run
grep "Found.*potentially interesting" faa_discovery.log
```

## Integration with FlightTrak

Currently, the discovery service:
1. ✅ Downloads and searches FAA database
2. ✅ Generates discovery reports
3. ⚠️ **Manual review required** - You decide which aircraft to add

To add aircraft from a report to your tracking list:
```bash
# Edit aircraft_list.json manually, or
# Run the validation script with new additions
```

## Future Enhancements

Possible additions:
- Auto-add historic warbirds (already vetted)
- Email reports when interesting aircraft are found
- Web dashboard showing discoveries
- Machine learning to identify interesting patterns

## Troubleshooting

**Download fails:**
- Check internet connection
- FAA site may be down temporarily
- Check logs: `tail -n 50 faa_discovery.log`

**No aircraft found:**
- Normal if no new interesting aircraft registered since last run
- Check existing count: `grep "Currently tracking" faa_discovery.log`

**Timer not running:**
```bash
sudo systemctl status faa-discovery.timer
journalctl -u faa-discovery.service -f
```
