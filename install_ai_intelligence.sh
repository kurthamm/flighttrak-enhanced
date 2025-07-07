#!/bin/bash

echo "🧠 Installing FlightTrak AI Intelligence System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing AI dependencies..."
pip install -r requirements.txt

# Test Claude API connection
echo "Testing Claude API connection..."
python3 -c "
import requests
import json

config_file = 'config.json'
try:
    with open(config_file) as f:
        config = json.load(f)
    
    api_key = config.get('claude_api_key')
    if not api_key:
        print('❌ No Claude API key found in config.json')
        exit(1)
    
    # Test API call
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    
    data = {
        'model': 'claude-3-haiku-20240307',
        'max_tokens': 100,
        'messages': [{
            'role': 'user',
            'content': 'Test connection - respond with OK'
        }]
    }
    
    response = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers=headers,
        json=data,
        timeout=10
    )
    
    if response.status_code == 200:
        print('✅ Claude API connection successful!')
    else:
        print(f'❌ Claude API error: {response.status_code}')
        print(response.text)
        
except Exception as e:
    print(f'❌ Error testing Claude API: {e}')
"

echo ""
echo "🚀 Installation complete!"
echo ""
echo "To start the AI Intelligence System:"
echo "1. source venv/bin/activate"
echo "2. python ai_intelligence_service.py"
echo ""
echo "To test individual components:"
echo "- python ai_event_intelligence.py"
echo "- python contextual_intelligence.py"
echo "- python claude_intelligence_enhancement.py"

chmod +x install_ai_intelligence.sh