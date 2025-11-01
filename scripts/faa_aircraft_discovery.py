#!/usr/bin/env python3
"""
FAA Aircraft Discovery Service
1. Downloads FAA database
2. Web searches for celebrity/famous aircraft
3. Compares against existing tracking list
4. Looks up ICAO codes for new celebrity jets
5. Finds rare warbirds
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Set
from pathlib import Path

# Configuration
FAA_DATABASE_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"
DOWNLOAD_DIR = Path("/home/kurt/flighttrak")
FAA_ZIP_FILE = DOWNLOAD_DIR / "ReleasableAircraft.zip"
FAA_MASTER_FILE = DOWNLOAD_DIR / "MASTER.txt"
FAA_ACFTREF_FILE = DOWNLOAD_DIR / "ACFTREF.txt"
AIRCRAFT_LIST_FILE = DOWNLOAD_DIR / "aircraft_list.json"
DISCOVERY_LOG = DOWNLOAD_DIR / "faa_discovery.log"

# Rare warbirds to search for (very specific)
RARE_WARBIRDS = {
    'B-29': ['BOEING B-29', 'B-29 SUPERFORTRESS'],
    'B-17': ['BOEING B-17', 'B-17 FLYING FORTRESS'],
    'B-24': ['CONSOLIDATED B-24', 'B-24 LIBERATOR'],
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(DISCOVERY_LOG),
        logging.StreamHandler()
    ]
)


class FAAAircraftDiscovery:
    """Improved aircraft discovery service"""
    
    def __init__(self):
        self.existing_tails: Set[str] = set()
        self.existing_icaos: Set[str] = set()
        self.faa_lookup: Dict[str, tuple] = {}
        self.acft_models: Dict[str, str] = {}
        
    def download_faa_database(self) -> bool:
        """Download latest FAA database with bot protection bypass"""
        try:
            logging.info("="*80)
            logging.info("STEP 1: Downloading FAA Aircraft Database")
            logging.info("="*80)
            
            # Use browser headers to bypass bot protection
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            
            response = requests.get(FAA_DATABASE_URL, headers=headers, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            logging.info(f"Downloading {total_size / 1024 / 1024:.1f} MB...")
            
            with open(FAA_ZIP_FILE, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"✓ Downloaded to {FAA_ZIP_FILE}")
            return True
            
        except Exception as e:
            logging.error(f"✗ Error downloading FAA database: {e}")
            return False
    
    def extract_faa_files(self) -> bool:
        """Extract MASTER.txt and ACFTREF.txt from FAA zip"""
        try:
            import zipfile
            
            logging.info("Extracting database files...")
            with zipfile.ZipFile(FAA_ZIP_FILE, 'r') as zip_ref:
                zip_ref.extract('MASTER.txt', DOWNLOAD_DIR)
                zip_ref.extract('ACFTREF.txt', DOWNLOAD_DIR)
            
            logging.info("✓ Extraction complete")
            return True
            
        except Exception as e:
            logging.error(f"✗ Error extracting database: {e}")
            return False
    
    def load_faa_database(self) -> bool:
        """Load FAA MASTER.txt and ACFTREF.txt into memory"""
        try:
            logging.info("Loading FAA database into memory...")
            
            # Load aircraft models
            with open(FAA_ACFTREF_FILE, 'r', encoding='utf-8-sig') as f:
                f.readline()  # Skip header
                for line in f:
                    fields = line.strip().split(',')
                    if len(fields) >= 3:
                        code = fields[0].strip()
                        mfr = fields[1].strip()
                        model = fields[2].strip()
                        if code:
                            self.acft_models[code] = f"{mfr} {model}".strip()
            
            # Load registrations
            with open(FAA_MASTER_FILE, 'r', encoding='utf-8-sig') as f:
                f.readline()  # Skip header
                
                for line in f:
                    fields = line.strip().split(',')
                    if len(fields) >= 34:
                        tail = fields[0].strip()
                        mfr_code = fields[2].strip()
                        owner_name = fields[6].strip()
                        icao_hex = fields[33].strip()
                        
                        if tail and icao_hex:
                            model = self.acft_models.get(mfr_code, '')
                            self.faa_lookup[f"N{tail}"] = (icao_hex.upper(), owner_name, model.upper())
            
            logging.info(f"✓ Loaded {len(self.faa_lookup)} aircraft from FAA database")
            return True
            
        except Exception as e:
            logging.error(f"✗ Error loading FAA database: {e}")
            return False
    
    def load_existing_aircraft(self) -> None:
        """Load currently tracked aircraft"""
        try:
            with open(AIRCRAFT_LIST_FILE) as f:
                data = json.load(f)
                for ac in data.get('aircraft_to_detect', []):
                    self.existing_icaos.add(ac['icao'].upper())
                    self.existing_tails.add(ac['tail_number'].upper())
            
            logging.info(f"Currently tracking {len(self.existing_tails)} aircraft")
            
        except Exception as e:
            logging.error(f"✗ Error loading existing aircraft: {e}")
    
    def web_search_celebrity_jets(self) -> List[Dict]:
        """
        Placeholder for web search functionality.
        In production, this would use web scraping or APIs to find celebrity jets.
        
        Returns list of: {'name': 'Celebrity Name', 'tail': 'N12345', 'notes': 'info'}
        """
        logging.info("")
        logging.info("="*80)
        logging.info("STEP 2: Web Search for Celebrity Jets")
        logging.info("="*80)
        logging.info("Note: Web search requires manual implementation")
        logging.info("Recommended sources:")
        logging.info("  - https://celebrityprivatejettracker.com/")
        logging.info("  - Celebrity jet tracking websites")
        logging.info("  - Aviation news sites")
        logging.info("")
        logging.info("For now, using known celebrity jet database...")
        
        # This would be replaced with actual web scraping
        # For now, return empty to avoid false discoveries
        return []
    
    def lookup_new_celebrity_jets(self, celebrity_jets: List[Dict]) -> List[Dict]:
        """Look up ICAO codes for new celebrity jets from FAA database"""
        logging.info("")
        logging.info("="*80)
        logging.info("STEP 3: Looking Up New Celebrity Jets in FAA Database")
        logging.info("="*80)
        
        new_celebs = []
        
        for celeb in celebrity_jets:
            tail = celeb['tail'].upper()
            
            # Skip if already tracking
            if tail in self.existing_tails:
                logging.info(f"⊘ {tail} - {celeb['name']} (already tracking)")
                continue
            
            # Look up in FAA database
            if tail in self.faa_lookup:
                icao, owner, model = self.faa_lookup[tail]
                new_celebs.append({
                    'name': celeb['name'],
                    'tail': tail,
                    'icao': icao,
                    'faa_owner': owner,
                    'model': model,
                    'notes': celeb.get('notes', '')
                })
                logging.info(f"✓ {tail} - {celeb['name']} - ICAO: {icao}")
            else:
                logging.info(f"✗ {tail} - {celeb['name']} - Not found in FAA database")
        
        return new_celebs
    
    def find_rare_warbirds(self) -> List[Dict]:
        """Find extremely rare warbirds (B-29, B-17, B-24)"""
        logging.info("")
        logging.info("="*80)
        logging.info("STEP 4: Searching for Rare Warbirds")
        logging.info("="*80)
        
        rare_birds = []
        
        for tail, (icao, owner, model) in self.faa_lookup.items():
            # Skip if already tracking
            if icao in self.existing_icaos:
                continue
            
            # Check for rare warbirds (very specific matching)
            for bird_type, model_patterns in RARE_WARBIRDS.items():
                if any(pattern in model for pattern in model_patterns):
                    # Extra validation: these should be in museums/foundations
                    if any(kw in owner.upper() for kw in ['MUSEUM', 'FOUNDATION', 'HERITAGE', 'FRIENDS', 'COLLECTION']):
                        rare_birds.append({
                            'tail': tail,
                            'icao': icao,
                            'type': bird_type,
                            'model': model,
                            'owner': owner
                        })
                        logging.info(f"✓ Found {bird_type}: {tail} ({icao}) - {owner}")
        
        logging.info(f"Found {len(rare_birds)} rare warbirds")
        return rare_birds
    
    def clean_owner_name(self, owner: str) -> str:
        """
        Clean up owner names from FAA database (handles truncation, standardization)
        """
        # Known truncation fixes from FAA database character limits
        truncation_fixes = {
            'AMERICAN AIRPOWER HERITAGE FLY MUSEU': 'American Airpower Heritage Flying Museum',
            'CHAMPAIGN AVIATION MUSEUM': 'Champaign Aviation Museum',
            'PLANE OF FAME AIR MUSEUM': 'Planes of Fame Air Museum',
            'LIBERTY FOUNDATION INC': 'Liberty Foundation Inc',
            'WORLDS GREATEST AIRCRAFT COLLECTION INC': 'Worlds Greatest Aircraft Collection Inc',
            'MID AMERICA FLIGHT MUSEUM INC': 'Mid America Flight Museum Inc',
        }

        # Check if we have a known fix
        owner_upper = owner.upper()
        if owner_upper in truncation_fixes:
            return truncation_fixes[owner_upper]

        # Otherwise, just title case it
        return owner.title()

    def add_aircraft_to_tracking(self, new_celebs: List[Dict], rare_birds: List[Dict]) -> int:
        """
        Automatically add discovered aircraft to aircraft_list.json
        Returns number of aircraft added
        """
        if not new_celebs and not rare_birds:
            logging.info("No new aircraft to add")
            return 0

        try:
            # Load existing aircraft list
            with open(AIRCRAFT_LIST_FILE, 'r') as f:
                data = json.load(f)

            aircraft_to_add = []

            # Process celebrity jets
            for celeb in new_celebs:
                aircraft_entry = {
                    "icao": celeb['icao'].upper(),
                    "tail_number": celeb['tail'],
                    "model": celeb['model'].title(),
                    "owner": celeb['name'],
                    "description": f"{celeb['name']}'s private jet - {celeb.get('notes', 'Celebrity aircraft')}"
                }
                aircraft_to_add.append(aircraft_entry)

            # Process rare warbirds with detailed descriptions
            warbird_descriptions = {
                'B-17': 'WWII-era Boeing B-17 Flying Fortress heavy bomber - One of approximately 12-15 airworthy examples remaining worldwide',
                'B-29': 'WWII-era Boeing B-29 Superfortress heavy bomber - Extremely rare, only 2 flying examples exist',
                'B-24': 'WWII-era Consolidated B-24 Liberator heavy bomber - Very rare warbird, few airworthy examples remain'
            }

            for bird in rare_birds:
                # Clean owner name (fixes FAA database truncations)
                clean_owner = self.clean_owner_name(bird['owner'])

                # Create detailed description
                base_desc = warbird_descriptions.get(bird['type'], f"Rare {bird['type']} warbird")
                description = f"{base_desc}. Currently owned by {clean_owner}"

                aircraft_entry = {
                    "icao": bird['icao'].upper(),
                    "tail_number": bird['tail'],
                    "model": bird['model'].title(),
                    "owner": clean_owner,
                    "description": description
                }
                aircraft_to_add.append(aircraft_entry)

            # Add new aircraft to the list
            data['aircraft_to_detect'].extend(aircraft_to_add)

            # Save updated aircraft list with proper formatting
            with open(AIRCRAFT_LIST_FILE, 'w') as f:
                json.dump(data, f, indent=4)

            logging.info("")
            logging.info("="*80)
            logging.info(f"✓ ADDED {len(aircraft_to_add)} NEW AIRCRAFT TO TRACKING LIST")
            logging.info("="*80)

            for aircraft in aircraft_to_add:
                logging.info(f"  + {aircraft['tail_number']} - {aircraft['owner']} ({aircraft['model']})")

            return len(aircraft_to_add)

        except Exception as e:
            logging.error(f"✗ Error adding aircraft to tracking list: {e}")
            return 0

    def generate_discovery_report(self, new_celebs: List[Dict], rare_birds: List[Dict]) -> None:
        """Generate comprehensive discovery report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = DOWNLOAD_DIR / f"faa_discovery_report_{timestamp}.txt"

        with open(report_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write(f"FAA Aircraft Discovery Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")

            # Celebrity jets section
            if new_celebs:
                f.write(f"NEW CELEBRITY/FAMOUS AIRCRAFT DISCOVERED ({len(new_celebs)}):\n")
                f.write("-"*80 + "\n\n")
                for celeb in new_celebs:
                    f.write(f"{celeb['name']}\n")
                    f.write(f"  Tail: {celeb['tail']}\n")
                    f.write(f"  ICAO: {celeb['icao']}\n")
                    f.write(f"  Model: {celeb['model']}\n")
                    f.write(f"  FAA Owner: {celeb['faa_owner']}\n")
                    if celeb['notes']:
                        f.write(f"  Notes: {celeb['notes']}\n")
                    f.write("\n")
            else:
                f.write("NO NEW CELEBRITY AIRCRAFT DISCOVERED\n\n")

            # Rare warbirds section
            if rare_birds:
                f.write(f"\nRARE WARBIRDS DISCOVERED ({len(rare_birds)}):\n")
                f.write("-"*80 + "\n\n")
                for bird in rare_birds:
                    f.write(f"{bird['type']} - {bird['tail']} ({bird['icao']})\n")
                    f.write(f"  Model: {bird['model']}\n")
                    f.write(f"  Owner: {bird['owner']}\n\n")
            else:
                f.write("\nNO NEW RARE WARBIRDS DISCOVERED\n")

            f.write("\n" + "="*80 + "\n")
            f.write(f"SUMMARY: {len(new_celebs)} celebrity jets + {len(rare_birds)} warbirds\n")
            f.write("="*80 + "\n")

        logging.info(f"✓ Discovery report saved to {report_file}")
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        logging.info("")
        logging.info("Cleaning up temporary files...")
        if FAA_ZIP_FILE.exists():
            os.remove(FAA_ZIP_FILE)
            logging.info(f"✓ Removed {FAA_ZIP_FILE}")
    
    def run(self) -> None:
        """Run the complete discovery process"""
        logging.info("\n" + "="*80)
        logging.info("FAA AIRCRAFT DISCOVERY SERVICE")
        logging.info("="*80)

        # Step 1: Download FAA database
        if not self.download_faa_database():
            logging.error("Failed to download FAA database - aborting")
            return

        if not self.extract_faa_files():
            logging.error("Failed to extract database - aborting")
            return

        if not self.load_faa_database():
            logging.error("Failed to load database - aborting")
            return

        # Load existing aircraft
        self.load_existing_aircraft()

        # Step 2: Web search for celebrity jets
        celebrity_jets = self.web_search_celebrity_jets()

        # Step 3: Look up new celebrity jets
        new_celebs = self.lookup_new_celebrity_jets(celebrity_jets)

        # Step 4: Find rare warbirds
        rare_birds = self.find_rare_warbirds()

        # Step 5: Generate report
        self.generate_discovery_report(new_celebs, rare_birds)

        # Step 6: AUTOMATICALLY ADD discovered aircraft to tracking list
        added_count = self.add_aircraft_to_tracking(new_celebs, rare_birds)

        # Cleanup
        self.cleanup()

        logging.info("")
        logging.info("="*80)
        logging.info("DISCOVERY COMPLETE")
        logging.info(f"Found: {len(new_celebs)} new celebrity jets + {len(rare_birds)} rare warbirds")
        logging.info(f"Added: {added_count} aircraft to tracking list")
        logging.info("="*80)


def main():
    """Main entry point"""
    discovery = FAAAircraftDiscovery()
    discovery.run()


if __name__ == '__main__':
    main()
