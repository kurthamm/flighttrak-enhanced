#!/bin/bash

echo "🧠 Updating FlightTrak to AI Intelligence Service..."

# Stop existing services
echo "Stopping existing FlightTrak services..."
sudo systemctl stop flightalert.service 2>/dev/null || true
sudo systemctl stop flighttrak-dashboard.service 2>/dev/null || true

# Install AI dependencies
echo "Installing AI dependencies..."
cd /root/flighttrak
source venv/bin/activate
pip install -r requirements.txt

# Copy new service file
echo "Installing new AI Intelligence service..."
sudo cp flighttrak-ai-intelligence.service /etc/systemd/system/

# Reload systemd and enable new service
echo "Configuring systemd..."
sudo systemctl daemon-reload
sudo systemctl enable flighttrak-ai-intelligence.service

# Start the new AI Intelligence service
echo "Starting AI Intelligence Service..."
sudo systemctl start flighttrak-ai-intelligence.service

# Wait a moment for startup
sleep 5

# Check status
echo ""
echo "🔍 Service Status:"
sudo systemctl status flighttrak-ai-intelligence.service --no-pager -l

echo ""
echo "📊 Recent logs:"
sudo journalctl -u flighttrak-ai-intelligence.service --no-pager -l -n 20

echo ""
echo "✅ AI Intelligence Service Update Complete!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status flighttrak-ai-intelligence.service"
echo "  sudo systemctl restart flighttrak-ai-intelligence.service"
echo "  sudo journalctl -u flighttrak-ai-intelligence.service -f"
echo "  tail -f /root/flighttrak/ai_intelligence_service.log"