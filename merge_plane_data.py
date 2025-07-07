#!/usr/bin/env python3
import json
import pandas as pd
import re
import os

# Paths – adjust if needed
EXCEL_PATH = "TheAirTraffic Database.xlsx"
JSON_IN    = "aircraft_list.json"
JSON_OUT   = "aircraft_list_merged.json"

# 1. Load existing JSON list
with open(JSON_IN, "r") as f:
    data = json.load(f)
existing = data["aircraft_to_detect"]

# Build lookup sets for fast membership tests
existing_icaos = {entry["icao"].upper() for entry in existing}
existing_tails = {entry["tail_number"].upper() for entry in existing}

# 2. Load the spreadsheet (no header row assumed)
df = pd.read_excel(EXCEL_PATH, header=None)

# Identify which columns hold tail, owner, model:
#   - tails in col 2
#   - owner in col 56
#   - model in col 59
tails_col = df[2].dropna().astype(str)
owner_col = df[56].astype(str)
model_col = df[59].astype(str)

# Regex for valid ICAO hex (6 hex digits) or tail (e.g. ‘N123AB’, ‘G-XXXX’)
hex_re  = re.compile(r"^[0-9A-F]{6}$")
tail_re = re.compile(r"^[A-Z0-9\-]{1,7}$")

new_entries = []

# 3. Iterate rows, split comma-separated tails, extract new entries
for idx, cell in tails_col.items():
    owner = owner_col.get(idx, "").strip()
    model = model_col.get(idx, "").strip()
    # split multiple tails if comma-separated
    for raw in cell.split(","):
        tail = raw.strip().upper()
        icao = tail  # use same string for ICAO placeholder
        # only accept if valid pattern
        if (hex_re.match(icao) or tail_re.match(tail)) \
           and icao not in existing_icaos \
           and tail not in existing_tails:
            new_entries.append({
                "icao":        icao,
                "tail_number": tail,
                "model":       model,
                "owner":       owner,
                "description": ""
            })
            existing_icaos.add(icao)
            existing_tails.add(tail)

# 4. Append new entries and write out merged JSON
if new_entries:
    print(f"Found {len(new_entries)} new aircraft—appending to list.")
    data["aircraft_to_detect"].extend(new_entries)
    with open(JSON_OUT, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Merged list saved as '{JSON_OUT}'.")
else:
    print("No new aircraft found; your list is already up to date.")
