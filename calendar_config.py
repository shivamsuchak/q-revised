"""
Configuration for Google Calendar integration.
This file helps set up the OAuth flow needed for Google Calendar access.
"""
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_calendar_config():
    """
    Set up configuration for Google Calendar integration.
    
    Returns:
        dict: Configuration settings for Google Calendar
    """
    # Default scopes needed for calendar operations
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    # Check for client_secret.json file
    client_secret_path = os.path.join(os.path.dirname(__file__), 'client_secret.json')
    
    if os.path.exists(client_secret_path):
        # Use the client_secret.json file if it exists
        return {
            'client_secret_file': client_secret_path,
            'scopes': SCOPES,
            'token_file': os.path.join(os.path.dirname(__file__), 'token.json')
        }
    else:
        # Create credentials from environment variables if file doesn't exist
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError(
                "Google Calendar credentials not found. Please either create a client_secret.json file "
                "or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
            )
        
        # Create a temporary client_secret.json file
        temp_client_secret = {
            "installed": {
                "client_id": client_id,
                "project_id": "q-hack-calendar",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost:8080"]
            }
        }
        
        # Write to a temporary file
        with open(client_secret_path, 'w') as f:
            json.dump(temp_client_secret, f)
        
        return {
            'client_secret_file': client_secret_path,
            'scopes': SCOPES,
            'token_file': os.path.join(os.path.dirname(__file__), 'token.json')
        }

# Default calendar configuration
calendar_config = setup_calendar_config()