#!/usr/bin/env python3
"""
Test script to generate and preview a weekly report
Generates report for the current week without sending email
"""

import sys
from weekly_report import generate_weekly_summary, format_html_report

def main():
    print("Generating weekly summary report...")

    result = generate_weekly_summary()

    if result is None:
        print("\n❌ No detections found for this week")
        sys.exit(0)

    summary, detections = result

    print(f"\n✅ Report generated successfully!")
    print(f"   Period: {summary['start_date'].strftime('%B %d, %Y')} - {summary['end_date'].strftime('%B %d, %Y')}")
    print(f"   Total Detections: {summary['total_detections']}")
    print(f"   Unique Aircraft: {summary['unique_aircraft']}")
    print(f"   Emergency Alerts: {summary['total_emergencies']}")

    if summary['most_detected']:
        print(f"\n🏆 Most Detected: {summary['most_detected']['aircraft']['owner']} ({summary['most_detected']['count']} times)")

    if summary['closest_approach']:
        print(f"📍 Closest Approach: {summary['closest_approach']['owner']} at {summary['closest_approach']['distance']:.1f} miles")

    print(f"\n📊 Detections by Day:")
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days_order:
        count = summary['by_day'].get(day, 0)
        if count > 0:
            print(f"   {day}: {count}")

    # Generate HTML
    html = format_html_report(summary, detections)

    # Save to file
    output_file = 'weekly_report_preview.html'
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"\n📄 HTML report saved to: {output_file}")
    print(f"   You can open this file in a browser to preview the email")

if __name__ == '__main__':
    main()
