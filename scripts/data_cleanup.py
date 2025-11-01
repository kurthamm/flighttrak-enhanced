#!/usr/bin/env python3
"""
FlightTrak Data Cleanup and Rotation System
Manages the detected aircraft data to prevent unlimited growth
"""

import os
import time
import json
import shutil
from datetime import datetime, timedelta
from collections import defaultdict

class DataManager:
    def __init__(self, config_file='config.json'):
        self.detected_file = 'detected_aircraft.txt'
        self.backup_dir = 'data_backups'
        self.max_detected_age_days = 30  # Keep detections for 30 days
        self.max_file_size_mb = 10       # Rotate when file exceeds 10MB
        
    def get_file_size_mb(self, filepath):
        """Get file size in MB"""
        if os.path.exists(filepath):
            return os.path.getsize(filepath) / (1024 * 1024)
        return 0
    
    def backup_detected_file(self):
        """Create backup of detected aircraft file"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{self.backup_dir}/detected_aircraft_{timestamp}.txt"
        
        if os.path.exists(self.detected_file):
            shutil.copy2(self.detected_file, backup_file)
            print(f"✅ Backed up detected aircraft to: {backup_file}")
            return backup_file
        return None
    
    def clean_old_backups(self, keep_days=90):
        """Remove backup files older than specified days"""
        if not os.path.exists(self.backup_dir):
            return
            
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        removed_count = 0
        
        for filename in os.listdir(self.backup_dir):
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                os.remove(filepath)
                removed_count += 1
                
        if removed_count > 0:
            print(f"🗑️  Removed {removed_count} old backup files")
    
    def rotate_detected_aircraft(self):
        """Rotate the detected aircraft file if it's too large"""
        file_size = self.get_file_size_mb(self.detected_file)
        
        if file_size > self.max_file_size_mb:
            print(f"📊 Detected aircraft file is {file_size:.1f}MB (limit: {self.max_file_size_mb}MB)")
            
            # Backup current file
            backup_file = self.backup_detected_file()
            
            if backup_file:
                # Start fresh with empty file
                open(self.detected_file, 'w').close()
                print(f"🔄 Rotated detected aircraft file - started fresh")
                return True
        return False
    
    def get_stats(self):
        """Get statistics about the data files"""
        stats = {
            'detected_file_size_mb': self.get_file_size_mb(self.detected_file),
            'detected_count': 0,
            'backup_files': 0,
            'oldest_backup': None,
            'newest_backup': None
        }
        
        # Count detected aircraft
        if os.path.exists(self.detected_file):
            with open(self.detected_file, 'r') as f:
                stats['detected_count'] = sum(1 for line in f if line.strip())
        
        # Count backup files
        if os.path.exists(self.backup_dir):
            backup_files = [f for f in os.listdir(self.backup_dir) if f.endswith('.txt')]
            stats['backup_files'] = len(backup_files)
            
            if backup_files:
                backup_paths = [os.path.join(self.backup_dir, f) for f in backup_files]
                mod_times = [os.path.getmtime(f) for f in backup_paths]
                stats['oldest_backup'] = datetime.fromtimestamp(min(mod_times)).strftime('%Y-%m-%d')
                stats['newest_backup'] = datetime.fromtimestamp(max(mod_times)).strftime('%Y-%m-%d')
        
        return stats
    
    def cleanup_all(self):
        """Perform full cleanup routine"""
        print("🧹 Starting FlightTrak data cleanup...")
        
        # Show current stats
        stats = self.get_stats()
        print(f"📊 Current stats:")
        print(f"   • Detected aircraft: {stats['detected_count']:,}")
        print(f"   • File size: {stats['detected_file_size_mb']:.1f}MB")
        print(f"   • Backup files: {stats['backup_files']}")
        
        # Rotate if needed
        rotated = self.rotate_detected_aircraft()
        
        # Clean old backups
        self.clean_old_backups()
        
        # Show final stats
        final_stats = self.get_stats()
        print(f"✅ Cleanup complete:")
        print(f"   • Detected aircraft: {final_stats['detected_count']:,}")
        print(f"   • File size: {final_stats['detected_file_size_mb']:.1f}MB")
        print(f"   • Backup files: {final_stats['backup_files']}")

if __name__ == '__main__':
    manager = DataManager()
    manager.cleanup_all()