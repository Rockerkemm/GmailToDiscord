import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Configuration - update these paths as needed
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "client_secret.json"  # Download this from Google Cloud Console
TOKEN_FILE = "token.json"  # This will be generated

def generate_oauth_token():
    """Generate OAuth token for Gmail access"""
    
    print("Gmail OAuth Token Generator")
    print("=" * 40)
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Error: {CREDENTIALS_FILE} not found!")
        print("Please download OAuth credentials from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Navigate to 'APIs & Services' > 'Credentials'")
        print("4. Create OAuth 2.0 Client ID for Desktop Application")
        print("5. Download the JSON file and name it 'client_secret.json'")
        return False
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        
        # Try local server first, fall back to console if needed
        try:
            creds = flow.run_local_server(port=0)
            print("OAuth authentication completed successfully")
        except Exception as e:
            print(f"Local server failed ({e}), trying manual flow...")
            print("Please copy the authorization code from your browser")
            creds = flow.run_console()
            print("Manual OAuth authentication completed successfully")
        
        # Save the token
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        
        print(f"Token saved to {TOKEN_FILE}")
        print()
        print("NEXT STEPS:")
        print(f"1. Copy {TOKEN_FILE} to your server at the same path")
        print("2. Make sure the data/ directory exists on your server")
        print("3. After copying, restart your Docker container or application")
        
        # Display token info (without sensitive data)
        print("\nToken Information:")
        token_data = json.loads(creds.to_json())
        print(f"   Scopes: {', '.join(token_data.get('scopes', []))}")
        print(f"   Expires: {token_data.get('expiry', 'N/A')}")
        print(f"   Has refresh token: {'Yes' if token_data.get('refresh_token') else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"Authentication failed: {e}")
        return False

def verify_credentials_file():
    """Verify the credentials file is valid"""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
            
        if 'installed' not in data:
            print("Error: client_secret.json should contain 'installed' section")
            print("Make sure you downloaded OAuth credentials for Desktop Application")
            return False
            
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        missing_fields = [field for field in required_fields if field not in data['installed']]
        
        if missing_fields:
            print(f"Error: Missing required fields in client_secret.json: {missing_fields}")
            return False
            
        print("client_secret.json is valid")
        return True
        
    except json.JSONDecodeError:
        print("Error: client_secret.json is not valid JSON")
        return False
    except Exception as e:
        print(f"Error reading client_secret.json: {e}")
        return False

if __name__ == "__main__":
    print("Gmail to Discord Webhook - Token Generator")
    print("This script generates OAuth tokens for server deployment")
    print()
    
    # Verify credentials file first
    if verify_credentials_file():
        generate_oauth_token()
    else:
        print("\n Please fix the client_secret.json file and try again.")