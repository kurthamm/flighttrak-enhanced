#!/usr/bin/env python3
"""
Reset FlightTrak detected aircraft data
Backs up current data and starts fresh
"""

import os
import shutil
from datetime import datetime

def reset_detected_aircraft():
    detected_file = 'detected_aircraft.txt'
    backup_dir = 'data_backups'
    
    # Create backup directory
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Create backup with timestamp
    if os.path.exists(detected_file):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/detected_aircraft_reset_{timestamp}.txt"
        shutil.copy2(detected_file, backup_file)
        
        # Get file stats
        file_size = os.path.getsize(detected_file) / (1024 * 1024)
        with open(detected_file, 'r') as f:
            line_count = sum(1 for line in f if line.strip())
        
        print(f"📊 Current data stats:")
        print(f"   • Aircraft tracked: {line_count:,}")
        print(f"   • File size: {file_size:.1f}MB")
        print(f"✅ Backed up to: {backup_file}")
        
        # Reset the file
        open(detected_file, 'w').close()
        print(f"🔄 Reset detected aircraft file - starting fresh!")
        print(f"📈 'Total Tracked' will now start from 0")
        
        return True
    else:
        print(f"❌ File {detected_file} not found")
        return False

if __name__ == '__main__':
    print("🚀 FlightTrak Data Reset")
    print("=" * 30)
    
    reset_detected_aircraft()
    
    print("\n🎯 What happens next:")
    print("   • Dashboard 'Total Tracked' starts at 0")
    print("   • System continues monitoring normally")
    print("   • Historical data is safely backed up")
    print("   • Restart service to see changes: sudo systemctl restart flightalert")