#!/usr/bin/env python3

import smtplib
from email.mime.text import MIMEText
import sys
import json

def load_config(filename):
    try:
        print(f"Loading configuration from {filename}...")
        with open(filename, 'r') as file:
            config = json.load(file)
            print("Configuration loaded successfully.")
            return config
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not parse {filename}.")
        return None

# Function to send a notification email using SendGrid's SMTP relay
def send_notification(subject, body, email_config):
    print(f"Preparing to send notification email with subject: {subject}")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_config['sender']
    msg['To'] = email_config['notification_email']

    try:
        print("Connecting to SendGrid SMTP server...")
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()  # Start TLS for security
            print("Logging in to the email server...")
            server.login("apikey", email_config['password'])  # Use "apikey" as the username
            print("Sending email...")
            server.sendmail(email_config['sender'], [email_config['notification_email']], msg.as_string())
            print(f"Notification email sent: {subject}")
    except Exception as e:
        print(f"Error sending notification email: {e}")

if __name__ == "__main__":
    # Load the config
    config = load_config('config.json')

    # Exit if config is not loaded
    if not config:
        sys.exit(1)

    email_config = config['email_config']

    # Determine the action (start/reload)
    if len(sys.argv) > 1 and sys.argv[1] == 'start':
        send_notification("FlightAlert Service Started", "The FlightAlert service has started.", email_config)
    elif len(sys.argv) > 1 and sys.argv[1] == 'reload':
        send_notification("FlightAlert Service Reloaded", "The FlightAlert service has reloaded.", email_config)
    else:
        print("Unknown action.")
