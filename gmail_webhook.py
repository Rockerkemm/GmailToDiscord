import os
import os.path
import json
import time
import signal
import threading
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Configuration
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")  # Get from .env file
TOKEN_FILE = os.getenv("TOKEN_FILE", "data/token.json")  # Path to store the token

# Use data directory for persistent files
DATA_DIR = "/app/data" if os.path.exists("/app/data") else "data"
# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "last_processed.json")
ERROR_QUEUE_FILE = os.path.join(DATA_DIR, "error_queue.json")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")  # Store token in data directory

CHECK_INTERVAL = 10  # Check for new emails every 10 seconds

# Global flag for graceful shutdown
running = True

# Discord formatting configuration
DISCORD_FORMATTING = {
    'incoming': {
        'emoji': '📬',
        'color': 3447003,  # Blue
        'username': 'Nue jmael :)',
        'title_prefix': 'New Email Received',
    },
    'outgoing': {
        'emoji': '✈️',
        'color': 4437377,  # Green
        'username': 'Nue jmael :)',
        'title_prefix': 'New Email Sent',
    }
}

class DiscordRateLimiter:
    """Handle Discord rate limiting with proper header parsing"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.requests_made = 0
        self.rate_limit_remaining = None
        self.rate_limit_reset_after = None
        self.min_delay = 1.0  # Minimum delay between requests
    
    def wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits"""
        with self.lock:
            current_time = time.time()
            
            # If we have active rate limit info, respect it
            if self.rate_limit_reset_after:
                reset_time = self.last_request_time + self.rate_limit_reset_after
                if current_time < reset_time:
                    wait_time = reset_time - current_time
                    print(f"Rate limit active, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                else:
                    # Reset period has passed
                    self.rate_limit_remaining = None
                    self.rate_limit_reset_after = None
            
            # Ensure minimum delay between requests
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                time.sleep(wait_time)
            
            self.last_request_time = time.time()
    
    def update_rate_limit_info(self, response):
        """Update rate limit info from Discord response headers"""
        with self.lock:
            # Parse Discord rate limit headers
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
            
            if 'X-RateLimit-Reset-After' in response.headers:
                self.rate_limit_reset_after = float(response.headers['X-RateLimit-Reset-After'])
            
            # Handle 429 Too Many Requests
            if response.status_code == 429:
                if 'Retry-After' in response.headers:
                    retry_after = float(response.headers['Retry-After'])
                    self.rate_limit_reset_after = retry_after
                    print(f"Hit rate limit, retry after {retry_after}s")
            
            # Log rate limit status
            if self.rate_limit_remaining is not None:
                print(f"Rate limit: {self.rate_limit_remaining} requests remaining")

# Global rate limiter instance
discord_rate_limiter = DiscordRateLimiter()

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global running
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    running = False

def authenticate_gmail():
    """Authenticate with Gmail using OAuth 2.0 (headless server mode)"""
    creds = None
    
    # Load existing token if it exists
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            print("Loaded existing OAuth credentials")
        except Exception as e:
            print(f"Failed to load existing credentials: {e}")
            creds = None
    
    # If there are no valid credentials available, request authorization
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired OAuth credentials...")
                creds.refresh(Request())
                print("Successfully refreshed OAuth credentials")
                
                # Save the refreshed credentials
                try:
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                    print(f"Refreshed OAuth credentials saved to {TOKEN_PATH}")
                except Exception as e:
                    print(f"Failed to save refreshed credentials: {e}")
                
                return creds
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                print("Need to re-authenticate...")
                creds = None
        
        if not creds:
            # No valid OAuth token found
            print("No valid OAuth token found.")
            raise Exception("OAuth token required - please follow the README to generate token.json")
    
    return creds

def load_state():
    """Load the last processed message ID and check if it's first run"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_processed_message_id', None), False
        except:
            # If file is corrupted, treat as first run
            return None, True
    else:
        # File doesn't exist - first time running
        return None, True

def save_state(message_id):
    """Save the last processed message ID"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'last_processed_message_id': message_id}, f)
        print(f"State saved: {message_id}")
    except Exception as e:
        print(f"Failed to save state: {e}")

def load_error_queue():
    """Load queued error messages"""
    if os.path.exists(ERROR_QUEUE_FILE):
        try:
            with open(ERROR_QUEUE_FILE, 'r') as f:
                return json.load(f)
        except:
            # If file is corrupted, create new one with empty list
            save_error_queue([])
            return []
    else:
        # Create file if it doesn't exist
        save_error_queue([])
        return []

def save_error_queue(error_queue):
    """Save queued error messages"""
    try:
        with open(ERROR_QUEUE_FILE, 'w') as f:
            json.dump(error_queue, f)
        print(f"Error queue saved with {len(error_queue)} items")
    except Exception as e:
        print(f"Failed to save error queue: {e}")

def format_email(email_string):
    """Extract clean email or name from email string"""
    if '<' in email_string and '>' in email_string:
        # Format: "Name <email@domain.com>"
        name_part = email_string.split('<')[0].strip().strip('"')
        email_part = email_string.split('<')[1].split('>')[0]
        return f"{name_part} ({email_part})" if name_part else email_part
    return email_string

def convert_to_discord_timestamp(date_string):
    """Convert email date to Discord timestamp format"""
    try:
        # Parse the email date
        dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
        # Convert to Unix timestamp for Discord
        unix_timestamp = int(dt.timestamp())
        return f"<t:{unix_timestamp}:f>"  # Discord timestamp format (full date/time)
    except:
        return date_string

def is_filtered_message(headers, labels):
    """Check if message should be filtered out (drafts, scheduled, etc.)"""
    # Filter out drafts
    if 'DRAFT' in labels:
        return True
    
    # Filter out scheduled messages
    if 'SCHEDULED' in labels:
        return True
    
    return False

def send_to_discord(message_data, message_type='incoming'):
    """Send formatted message to Discord with rate limiting"""
    try:
        config = DISCORD_FORMATTING[message_type]
        
        # Determine direction and main contact
        if message_type == 'incoming':
            main_contact = format_email(message_data['sender'])
            direction = "**From: **"
        else:
            main_contact = format_email(message_data['recipient'])
            direction = "**To: **"
        
        title = f"{config['emoji']} **{config['title_prefix']}**"
        
        description = (
            f"{direction}"
            f"{main_contact}\n"
            f"**Subject:** "
            f"{message_data['subject']}\n"
            f"**Time: **"
            f"{message_data['formatted_date']}"
        )
        
        embed = {
            "title": title,
            "description": description,
            "color": config['color'],
        }
        
        payload = {
            "username": config['username'],
            "embeds": [embed]
        }
        
        # Add custom avatar if specified
        if 'avatar_url' in config:
            payload['avatar_url'] = config['avatar_url']
        
        # Apply rate limiting before making request
        discord_rate_limiter.wait_for_rate_limit()
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
        
        # Update rate limit info from response
        discord_rate_limiter.update_rate_limit_info(response)
        
        # Handle rate limit response
        if response.status_code == 429:
            print(f"Rate limited by Discord, message queued for retry")
            # Queue the message for retry
            error_queue = load_error_queue()
            error_queue.append({
                'type': 'rate_limited_message',
                'data': message_data,
                'message_type': message_type,
                'timestamp': datetime.now().isoformat()
            })
            save_error_queue(error_queue)
            return False
        
        response.raise_for_status()
        
        print(f"Sent {message_type} email notification to Discord")
        return True
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout sending to Discord - Subject: {message_data['subject'][:50]}..."
        print(f"Timeout: {error_msg}")
        send_error_to_discord(error_msg)
        return False
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error sending to Discord - Subject: {message_data['subject'][:50]}..., Error: {e}"
        print(f"Network error: {error_msg}")
        send_error_to_discord(error_msg)
        return False
        
    except Exception as e:
        error_msg = f"Failed to send email to Discord - Subject: {message_data['subject'][:50]}..., Type: {message_type}, Error: {e}"
        print(f"Error: {error_msg}")
        send_error_to_discord(error_msg)
        return False

def send_error_to_discord(error_message):
    """Send error notification to Discord"""
    try:
        embed = {
            "title": "⚠️ **Gmail Webhook Error**",
            "description": f"```{error_message}```",
            "color": 15158332,  # Red
        }
        
        payload = {
            "username": "Gmail Error Bot",
            "embeds": [embed]
        }
        
        # Apply rate limiting before making request
        discord_rate_limiter.wait_for_rate_limit()
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
        
        # Update rate limit info from response
        discord_rate_limiter.update_rate_limit_info(response)
        
        # Handle rate limit response
        if response.status_code == 429:
            print(f"Error message rate limited, queuing for retry")
            # Queue the error if rate limited
            error_queue = load_error_queue()
            error_queue.append({
                'type': 'error_message',
                'message': error_message,
                'timestamp': datetime.now().isoformat()
            })
            save_error_queue(error_queue)
            return False
        
        response.raise_for_status()
        return True
        
    except:
        # Queue the error if Discord is unreachable
        error_queue = load_error_queue()
        error_queue.append({
            'type': 'error_message',
            'message': error_message,
            'timestamp': datetime.now().isoformat()
        })
        save_error_queue(error_queue)
        return False

def process_queued_errors():
    """Process queued error messages"""
    error_queue = load_error_queue()
    if not error_queue:
        return
    
    processed = []
    for error_data in error_queue:
        try:
            if error_data.get('type') == 'rate_limited_message':
                # Retry sending the original message
                success = send_to_discord(error_data['data'], error_data['message_type'])
                if success:
                    processed.append(error_data)
                    print(f"Successfully sent queued message")
            elif error_data.get('type') == 'error_message':
                # Send the error message
                if send_error_to_discord(error_data['message']):
                    processed.append(error_data)
                    print(f"Successfully sent queued error")
            else:
                # Legacy format - treat as error message
                message = error_data.get('message', str(error_data))
                if send_error_to_discord(message):
                    processed.append(error_data)
                    print(f"Successfully sent legacy queued error")
        except Exception as e:
            print(f"Failed to process queued item: {e}")
    
    # Remove processed errors
    remaining_errors = [e for e in error_queue if e not in processed]
    save_error_queue(remaining_errors)
    
    if processed:
        print(f"Processed {len(processed)} queued items, {len(remaining_errors)} remaining")

def get_new_messages(service, last_processed_id=None, first_run=False):
    """Get new messages in batches until we find the last processed message ID"""
    try:
        if first_run:
            # On first run, get only the most recent message
            results = service.users().messages().list(
                userId="me", 
                maxResults=1
            ).execute()
            messages = results.get("messages", [])
            return messages
        
        if not last_processed_id:
            # No previous state, get recent messages
            results = service.users().messages().list(
                userId="me", 
                maxResults=20
            ).execute()
            messages = results.get("messages", [])
            return messages
        
        # Fetch messages in batches until we find the last processed ID
        all_new_messages = []
        page_token = None
        found_last_processed = False
        
        while not found_last_processed:
            # Get batch of 20 messages
            kwargs = {
                "userId": "me",
                "maxResults": 20
            }
            if page_token:
                kwargs["pageToken"] = page_token
                
            results = service.users().messages().list(**kwargs).execute()
            messages = results.get("messages", [])
            
            if not messages:
                # No more messages
                break
            
            # Check if we found the last processed message
            for message in messages:
                if message["id"] == last_processed_id:
                    found_last_processed = True
                    break
                all_new_messages.append(message)
            
            # Get next page token for pagination
            page_token = results.get("nextPageToken")
            if not page_token:
                # No more pages
                break
        
        return all_new_messages
        
    except Exception as e:
        error_msg = f"Failed to fetch messages: {e}"
        send_error_to_discord(error_msg)
        return []

def process_message(service, message_id):
    """Process a single message and extract relevant information"""
    try:
        message = service.users().messages().get(userId="me", id=message_id).execute()
        
        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        labels = message.get("labelIds", [])
        
        # Check if message should be filtered
        if is_filtered_message(headers, labels):
            return None, None
        
        # Extract message information
        subject = "No Subject"
        sender = "Unknown Sender"
        recipient = "Unknown Recipient"
        date = "Unknown Date"
        internal_date = int(message.get("internalDate", 0)) / 1000
        
        for header in headers:
            name = header["name"]
            value = header["value"]
            
            if name == "Subject":
                subject = value
            elif name == "From":
                sender = value
            elif name == "To":
                recipient = value
            elif name == "Date":
                date = value
        
        # Format the date
        formatted_date = convert_to_discord_timestamp(date)
        
        # Determine message type
        message_type = 'outgoing' if 'SENT' in labels else 'incoming'
        
        message_data = {
            'subject': subject,
            'sender': sender,
            'recipient': recipient,
            'date': date,
            'formatted_date': formatted_date,
            'internal_date': internal_date,
            'message_id': message_id
        }
        
        return message_data, message_type
        
    except Exception as e:
        error_msg = f"Failed to process message {message_id}: {e}"
        send_error_to_discord(error_msg)
        return None, None

def main():
    """Main function with continuous email monitoring"""
    global running
    
    print("Starting Gmail to Discord webhook with OAuth 2.0...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Process any queued errors first
    process_queued_errors()
    
    # Authenticate with Gmail using OAuth 2.0
    try:
        credentials = authenticate_gmail()
        print("OAuth 2.0 authentication successful")
    except Exception as e:
        error_msg = f"Failed to authenticate with Gmail: {e}"
        print(f"Failed to authenticate: {error_msg}")
        print("\nApplication stopping - OAuth token required.")
        return
    
    try:
        service = build("gmail", "v1", credentials=credentials)
        
        # Load last processed message ID and check if first run
        last_message_id, is_first_run = load_state()
        if is_first_run:
            print("First time running! Will process the most recent email.")
        else:
            print(f"Last processed message ID: {last_message_id}")
        
        print(f"Starting continuous monitoring (checking every {CHECK_INTERVAL} seconds)")
        print("   Press Ctrl+C to stop gracefully")
        
        while running:
            try:
                # Get new messages
                messages = get_new_messages(service, last_message_id, first_run=is_first_run)
                
                if messages:
                    if is_first_run:
                        print(f"Processing the most recent email for first-time setup")
                        is_first_run = False  # Mark as no longer first run
                    else:
                        print(f"Found {len(messages)} new messages to process")
                    
                    # Process messages chronologically (oldest first)
                    processed_messages = []
                    latest_message_id = last_message_id
                    latest_internal_date = 0
                    
                    for msg in reversed(messages):  # Reverse to get oldest first
                        if not running:  # Check if we should stop
                            break
                            
                        message_data, message_type = process_message(service, msg["id"])
                        
                        if message_data:
                            processed_messages.append((message_data, message_type))
                            # Track the most recent message ID based on internal_date
                            if message_data['internal_date'] > latest_internal_date:
                                latest_internal_date = message_data['internal_date']
                                latest_message_id = message_data['message_id']
                    
                    # Send to Discord in chronological order
                    for message_data, message_type in processed_messages:
                        if not running:  # Check if we should stop
                            break
                            
                        success = send_to_discord(message_data, message_type)
                        if success:
                            print(f"Processed: {message_data['subject'][:50]}...")
                        else:
                            print(f"Failed to send: {message_data['subject'][:50]}...")
                    
                    # Save the latest message ID
                    if latest_message_id and latest_message_id != last_message_id:
                        save_state(latest_message_id)
                        last_message_id = latest_message_id
                        print(f"Saved new message ID: {latest_message_id}")
                        
                else:
                    if is_first_run:
                        print("No messages found in Gmail.")
                        is_first_run = False
                    else:
                        # Only print this occasionally to avoid spam
                        current_time = datetime.now().strftime("%H:%M:%S")
                        print(f"No new messages ({current_time})")
                
                # Process any queued errors periodically
                if messages:  # Only process when we had activity
                    process_queued_errors()
                
                # Wait for the next check
                if running:
                    print(f"Waiting {CHECK_INTERVAL} seconds before next check...")
                    for i in range(CHECK_INTERVAL):
                        if not running:
                            break
                        time.sleep(1)
                        
            except HttpError as error:
                # Handle credential refresh for expired tokens
                if error.resp.status == 401:
                    print("Token expired, attempting to refresh...")
                    try:
                        credentials = authenticate_gmail()
                        service = build("gmail", "v1", credentials=credentials)
                        print("Successfully refreshed credentials")
                        continue
                    except Exception as refresh_error:
                        error_msg = f"Failed to refresh credentials: {refresh_error}"
                        print(f"Failed to refresh: {error_msg}")
                        send_error_to_discord(error_msg)
                        break
                
                error_msg = f"Gmail API error: {error}"
                print(f"API error: {error_msg}")
                send_error_to_discord(error_msg)
                
                # Wait before retrying on API errors
                if running:
                    print(f"Waiting 30 seconds before retrying after API error...")
                    for i in range(30):
                        if not running:
                            break
                        time.sleep(1)
                        
            except Exception as error:
                error_msg = f"Unexpected error: {error}"
                print(f"Unexpected error: {error_msg}")
                send_error_to_discord(error_msg)
                
                # Wait before retrying on unexpected errors
                if running:
                    print(f"Waiting 30 seconds before retrying after unexpected error...")
                    for i in range(30):
                        if not running:
                            break
                        time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, shutting down...")
        running = False
    except Exception as critical_error:
        error_msg = f"Critical error in main loop: {critical_error}"
        print(f"Critical error: {error_msg}")
        send_error_to_discord(error_msg)
    finally:
        print("Gmail to Discord webhook stopped")
        # Process any remaining queued errors before exit
        try:
            process_queued_errors()
        except:
            pass

if __name__ == "__main__":
    main()
