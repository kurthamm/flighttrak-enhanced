#!/usr/bin/env python3
"""
Claude AI Enhancement Module for FlightTrak Intelligence
Integrates Anthropic's Claude API for advanced natural language intelligence generation
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ClaudeAnalysis:
    """Structured Claude AI analysis result"""
    narrative: str
    confidence_assessment: str
    recommended_actions: List[str]
    severity_explanation: str
    context_synthesis: str
    prediction: str

class ClaudeIntelligenceEnhancer:
    """Enhances event intelligence using Claude AI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        logging.info("Claude Intelligence Enhancement initialized")
    
    def call_claude_api(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """Make API call to Claude"""
        try:
            data = {
                "model": "claude-3-haiku-20240307",  # Fast, efficient model for real-time analysis
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            else:
                logging.error(f"Claude API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Error calling Claude API: {e}")
            return None
    
    def enhance_event_analysis(self, event_data: Dict) -> ClaudeAnalysis:
        """Use Claude to enhance event analysis with sophisticated reasoning"""
        
        # Prepare comprehensive prompt for Claude
        prompt = f"""
You are a professional aviation intelligence analyst with expertise in interpreting aircraft movement patterns and operational behavior. Analyze the following aircraft event data and provide a comprehensive intelligence assessment.

EVENT DATA:
- Event Type: {event_data.get('event_type', 'Unknown')}
- Confidence: {event_data.get('confidence', 0)}
- Aircraft Count: {len(event_data.get('aircraft_involved', []))}
- Location: {event_data.get('location', 'Unknown')}
- Time: {event_data.get('timestamp', time.time())}

PATTERN ANALYSIS:
- Formation Type: {event_data.get('pattern_signature', {}).get('formation_type', 'Unknown')}
- Spread Radius: {event_data.get('pattern_signature', {}).get('spread_radius', 0)} miles
- Average Altitude: {event_data.get('pattern_signature', {}).get('avg_altitude', 0)} feet
- Average Speed: {event_data.get('pattern_signature', {}).get('avg_speed', 0)} knots

CONTEXTUAL FACTORS:
{event_data.get('contextual_analysis', {}).get('explanatory_factors', ['None available'])}

AIRCRAFT INVOLVED:
{', '.join(event_data.get('aircraft_involved', ['None']))}

Please provide a detailed intelligence analysis including:

1. EXECUTIVE SUMMARY: A concise, professional assessment of what is likely occurring

2. TACTICAL ANALYSIS: Detailed interpretation of the aircraft movement patterns and what they indicate

3. CONFIDENCE ASSESSMENT: Your professional judgment on the reliability of this analysis and any caveats

4. CONTEXTUAL SIGNIFICANCE: How external factors might be influencing or explaining this activity

5. OPERATIONAL IMPLICATIONS: What this activity suggests about resources, duration, and scope

6. PREDICTIVE ASSESSMENT: What is likely to happen next based on these patterns

7. RECOMMENDED MONITORING: What additional indicators to watch for

Format your response as a professional intelligence brief suitable for a decision-maker. Be specific, analytical, and actionable while acknowledging uncertainty where appropriate.
"""

        # Get Claude's analysis
        claude_response = self.call_claude_api(prompt, max_tokens=1500)
        
        if not claude_response:
            # Fallback to basic analysis if Claude fails
            return self.create_fallback_analysis(event_data)
        
        # Parse Claude's structured response
        return self.parse_claude_analysis(claude_response, event_data)
    
    def parse_claude_analysis(self, claude_response: str, event_data: Dict) -> ClaudeAnalysis:
        """Parse Claude's response into structured analysis"""
        
        # Extract sections from Claude's response
        sections = {
            'executive_summary': '',
            'tactical_analysis': '',
            'confidence_assessment': '',
            'contextual_significance': '',
            'operational_implications': '',
            'predictive_assessment': '',
            'recommended_monitoring': ''
        }
        
        # Simple parsing - in production you'd want more robust parsing
        current_section = None
        for line in claude_response.split('\n'):
            line = line.strip()
            
            # Identify section headers
            if 'EXECUTIVE SUMMARY' in line.upper():
                current_section = 'executive_summary'
            elif 'TACTICAL ANALYSIS' in line.upper():
                current_section = 'tactical_analysis'
            elif 'CONFIDENCE ASSESSMENT' in line.upper():
                current_section = 'confidence_assessment'
            elif 'CONTEXTUAL SIGNIFICANCE' in line.upper():
                current_section = 'contextual_significance'
            elif 'OPERATIONAL IMPLICATIONS' in line.upper():
                current_section = 'operational_implications'
            elif 'PREDICTIVE ASSESSMENT' in line.upper():
                current_section = 'predictive_assessment'
            elif 'RECOMMENDED MONITORING' in line.upper():
                current_section = 'recommended_monitoring'
            elif current_section and line:
                sections[current_section] += line + ' '
        
        # Create comprehensive narrative combining all sections
        narrative = f"""
🎯 EXECUTIVE SUMMARY:
{sections['executive_summary'].strip()}

🔍 TACTICAL ANALYSIS:
{sections['tactical_analysis'].strip()}

📊 OPERATIONAL IMPLICATIONS:
{sections['operational_implications'].strip()}

🔮 PREDICTIVE ASSESSMENT:
{sections['predictive_assessment'].strip()}
        """.strip()
        
        return ClaudeAnalysis(
            narrative=narrative,
            confidence_assessment=sections['confidence_assessment'].strip(),
            recommended_actions=sections['recommended_monitoring'].strip().split('. ') if sections['recommended_monitoring'].strip() else [],
            severity_explanation=sections['contextual_significance'].strip(),
            context_synthesis=sections['contextual_significance'].strip(),
            prediction=sections['predictive_assessment'].strip()
        )
    
    def create_fallback_analysis(self, event_data: Dict) -> ClaudeAnalysis:
        """Create basic analysis if Claude API is unavailable"""
        event_type = event_data.get('event_type', 'unknown_activity')
        aircraft_count = len(event_data.get('aircraft_involved', []))
        confidence = event_data.get('confidence', 0.5)
        
        basic_narrative = f"""
🎯 EXECUTIVE SUMMARY:
{aircraft_count} aircraft detected in coordinated {event_type.replace('_', ' ')} pattern. 
Analysis confidence: {confidence:.2f}

🔍 TACTICAL ANALYSIS:
Aircraft formation and movement patterns consistent with {event_type.replace('_', ' ')} operations.
Coordinated behavior suggests planned operational activity.

📊 OPERATIONAL IMPLICATIONS:
Multi-aircraft deployment indicates significant resource commitment.
Pattern suggests operation duration of 1-4 hours based on historical data.

🔮 PREDICTIVE ASSESSMENT:
Activity likely to continue at current intensity for next 30-60 minutes.
Additional aircraft may join operation if situation escalates.
        """.strip()
        
        return ClaudeAnalysis(
            narrative=basic_narrative,
            confidence_assessment=f"Moderate confidence ({confidence:.2f}) based on pattern matching",
            recommended_actions=["Continue monitoring aircraft positions", "Watch for additional aircraft joining"],
            severity_explanation="Moderate significance based on aircraft count and coordination",
            context_synthesis="Limited contextual data available",
            prediction="Continued activity expected"
        )
    
    def generate_enhanced_alert_email(self, event_data: Dict, claude_analysis: ClaudeAnalysis) -> str:
        """Generate enhanced HTML email with Claude's analysis"""
        
        event_type = event_data.get('event_type', 'unknown').replace('_', ' ').title()
        severity = event_data.get('severity', 'MEDIUM')
        location = event_data.get('location', (0, 0))
        
        # Severity colors
        severity_colors = {
            'CRITICAL': '#ff4757',
            'HIGH': '#ff6b6b',
            'MEDIUM': '#ffa502',
            'LOW': '#3742fa'
        }
        color = severity_colors.get(severity, '#666')
        
        html_content = f"""
        <html><body style='font-family:Arial,sans-serif;line-height:1.4;background:#0a0e27;color:#e0e6ed;padding:20px;'>
            <div style='max-width:900px;margin:0 auto;background:#1a1f3a;padding:25px;border-radius:12px;border:1px solid #2a3f5f;box-shadow:0 4px 6px rgba(0,0,0,0.3);'>
                
                <!-- Header -->
                <div style='text-align:center;margin-bottom:25px;padding-bottom:20px;border-bottom:2px solid #2a3f5f;'>
                    <h1 style='color:{color};margin:0;font-size:24px;'>🧠 FlightTrak AI Intelligence Alert</h1>
                    <h2 style='color:#4fc3f7;margin:10px 0;font-size:20px;'>{event_type}</h2>
                    <p style='color:#feca57;font-size:14px;margin:5px 0;'>Enhanced by Claude AI Analysis</p>
                </div>
                
                <!-- Claude AI Analysis -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>🤖 Claude AI Intelligence Assessment</h3>
                    <div style='white-space: pre-line; color:#e0e6ed; line-height: 1.6; font-size: 14px;'>
                        {claude_analysis.narrative}
                    </div>
                </div>
                
                <!-- Confidence & Predictions -->
                <div style='display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0;'>
                    <div style='background:#2a3f5f;padding:20px;border-radius:8px;'>
                        <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>📊 Confidence Assessment</h3>
                        <div style='color:#e0e6ed;font-size:14px;'>
                            {claude_analysis.confidence_assessment}
                        </div>
                    </div>
                    <div style='background:#2a3f5f;padding:20px;border-radius:8px;'>
                        <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>🔮 Predictive Analysis</h3>
                        <div style='color:#e0e6ed;font-size:14px;'>
                            {claude_analysis.prediction}
                        </div>
                    </div>
                </div>
                
                <!-- Recommended Actions -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>⚡ Recommended Monitoring</h3>
                    <ul style='color:#e0e6ed;margin:0;padding-left:20px;'>
                        {''.join([f'<li>{action.strip()}</li>' for action in claude_analysis.recommended_actions if action.strip()])}
                    </ul>
                </div>
                
                <!-- Technical Details -->
                <div style='background:#2a3f5f;padding:20px;border-radius:8px;margin:20px 0;'>
                    <h3 style='color:#4fc3f7;margin:0 0 15px 0;'>📋 Technical Details</h3>
                    <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;color:#e0e6ed;font-size:14px;'>
                        <div><strong>Aircraft Count:</strong> {len(event_data.get('aircraft_involved', []))}</div>
                        <div><strong>Severity:</strong> <span style='color:{color};'>{severity}</span></div>
                        <div><strong>ML Confidence:</strong> {event_data.get('confidence', 0):.2f}</div>
                        <div><strong>Formation:</strong> {event_data.get('pattern_signature', {}).get('formation_type', 'Unknown')}</div>
                        <div><strong>Spread:</strong> {event_data.get('pattern_signature', {}).get('spread_radius', 0):.1f} mi</div>
                        <div><strong>Avg Altitude:</strong> {event_data.get('pattern_signature', {}).get('avg_altitude', 0):.0f} ft</div>
                    </div>
                </div>
                
                <!-- Map Links -->
                <div style='text-align:center;margin:30px 0;'>
                    <a href='https://maps.google.com/?q={location[0]},{location[1]}&z=13' 
                       style='background:#4fc3f7;color:#0a0e27;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 10px;display:inline-block;'>
                       📍 View Location
                    </a>
                    <a href='https://www.flightradar24.com/{location[0]},{location[1]}/13' 
                       style='background:#feca57;color:#0a0e27;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;margin:0 10px;display:inline-block;'>
                       ✈️ Live Aircraft View
                    </a>
                </div>
                
                <!-- Footer -->
                <div style='text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #2a3f5f;'>
                    <p style='font-size:12px;color:#8892b0;margin:5px 0;'>
                        FlightTrak AI Intelligence System • Enhanced by Claude AI
                    </p>
                    <p style='font-size:11px;color:#8892b0;margin:5px 0;'>
                        Machine Learning Pattern Recognition + Advanced Language AI
                    </p>
                </div>
            </div>
        </body></html>
        """
        
        return html_content
    
    def enhance_contextual_analysis(self, contextual_data: Dict) -> str:
        """Use Claude to synthesize contextual information"""
        
        if not contextual_data.get('relevant_news') and not contextual_data.get('weather_factors'):
            return "No significant contextual factors identified."
        
        prompt = f"""
As an intelligence analyst, synthesize the following contextual information to explain how it might relate to the aircraft activity patterns we're observing:

RELEVANT NEWS:
{json.dumps(contextual_data.get('relevant_news', []), indent=2)}

WEATHER ALERTS:
{json.dumps(contextual_data.get('weather_factors', []), indent=2)}

AVIATION NOTICES:
{json.dumps(contextual_data.get('aviation_notices', []), indent=2)}

Provide a brief synthesis explaining:
1. How these factors might explain or relate to unusual aircraft activity
2. Whether they suggest the activity is routine or exceptional
3. Any implications for operational tempo or duration

Keep the response concise but analytical - 2-3 paragraphs maximum.
"""
        
        claude_response = self.call_claude_api(prompt, max_tokens=500)
        return claude_response or "Contextual analysis unavailable - Claude API error."

def integrate_claude_with_ai_system(api_key: str):
    """Integration function to add Claude to existing AI system"""
    
    # This would be integrated into the main AI event intelligence system
    # by modifying the send_intelligence_alert function to use Claude enhancement
    
    claude_enhancer = ClaudeIntelligenceEnhancer(api_key)
    
    def enhanced_alert_generator(event_data: Dict) -> str:
        """Enhanced alert generation with Claude AI"""
        
        # Get Claude's analysis
        claude_analysis = claude_enhancer.enhance_event_analysis(event_data)
        
        # Generate enhanced email
        enhanced_email = claude_enhancer.generate_enhanced_alert_email(event_data, claude_analysis)
        
        return enhanced_email
    
    return enhanced_alert_generator

# Example usage and testing
def test_claude_integration():
    """Test the Claude integration with sample data"""
    
    # Sample event data
    sample_event = {
        'event_type': 'search_rescue',
        'confidence': 0.87,
        'aircraft_involved': ['A12345', 'B67890', 'C11111'],
        'location': (34.1133, -80.9024),
        'timestamp': time.time(),
        'severity': 'HIGH',
        'pattern_signature': {
            'formation_type': 'search_pattern',
            'spread_radius': 3.2,
            'avg_altitude': 1500,
            'avg_speed': 85
        },
        'contextual_analysis': {
            'explanatory_factors': ['Recent missing person report in local news']
        }
    }
    
    # Note: You would need to provide your actual API key here
    # claude_enhancer = ClaudeIntelligenceEnhancer("your-api-key-here")
    # analysis = claude_enhancer.enhance_event_analysis(sample_event)
    # print(analysis.narrative)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_claude_integration()