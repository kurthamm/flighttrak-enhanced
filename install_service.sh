#!/bin/bash
# FlightAlert Service Installation Script

echo "Installing FlightAlert as a systemd service..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Copy service file to systemd directory
echo "Installing service file..."
cp flightalert.service /etc/systemd/system/

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "Enabling FlightAlert service..."
systemctl enable flightalert.service

# Create log file with proper permissions
touch /root/flighttrak/flightalert.log
chmod 644 /root/flighttrak/flightalert.log

echo "Installation complete!"
echo ""
echo "To manage the service, use:"
echo "  Start:   sudo systemctl start flightalert"
echo "  Stop:    sudo systemctl stop flightalert"
echo "  Status:  sudo systemctl status flightalert"
echo "  Logs:    sudo journalctl -u flightalert -f"
echo ""
echo "To start the service now, run: sudo systemctl start flightalert"