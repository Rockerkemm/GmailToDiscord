import os
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from ratelimit import limits, sleep_and_retry
from filelock import FileLock
from dotenv import load_dotenv
import sys
import time
import pytz

# Load environment variables
load_dotenv()

# Constants
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
DISCORD_MONITOR_WEBHOOK_URL = os.getenv('DISCORD_MONITOR_WEBHOOK_URL')
LAST_PROCESSED_FILE = 'last_processed.json'
ERROR_QUEUE_FILE = 'error_queue.json'
TOKEN_FILE = 'token.json'

# Discord formatting
DISCORD_FORMATTING = {
    'incoming': {
        'emoji': '📬',
        'color': 3447003,  # Blue
        'username': 'Nue jmael :)',
        'title_prefix': 'New Email Received'
    },
    'outgoing': {
        'emoji': '✈️',
        'color': 4437377,  # Green
        'username': 'Nue jmael :)',
        'title_prefix': 'New Email Sent'
    }
}

# Discord rate limiting
@sleep_and_retry
@limits(calls=25, period=60)  # Stay under Discord's 30/minute limit
def send_to_discord(webhook_url, payload):
    response = requests.post(webhook_url, json=payload, timeout=10)
    response.raise_for_status()
    
    # Handle Discord rate limits
    if response.status_code == 429:
        retry_after = response.json().get('retry_after', 5)
        time.sleep(retry_after / 1000)  # Discord returns milliseconds
        return False
    return True

def get_local_now():
    # Use system local timezone
    return datetime.now().astimezone()

def format_datetime(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        dt = dt.astimezone()  # Convert to local time
        return dt.strftime("%d %B %Y - %H:%M")
    except Exception:
        return date_str

def create_discord_message(message_type, subject, sender, recipient, date):
    format_config = DISCORD_FORMATTING[message_type]
    def format_email(email):
        email = email.split(',')[0].strip()
        return email
    
    if message_type == 'incoming':
        main_contact = format_email(sender)
        direction = "**From: **"
        title = f"📬 **New Email Received**"
    
    else:
        main_contact = format_email(recipient)
        direction = "**To: **"
        title = f"✈️ **New Email Sent**"
        
    subject_text = subject if subject else ""
    formatted_date = format_datetime(date)
    description = (
        f"{direction}"
        f"{main_contact}\n"

        f"**Subject:** "
        f"{subject_text}\n"

        f"**Time: **"
        f"{formatted_date}"
    )
    return {
        "username": format_config['username'],
        "avatar_url": "https://cdn.discordapp.com/attachments/1344663464987066519/1412166376692645928/hehe.jpeg?ex=68b74dec&is=68b5fc6c&hm=c52e41a186fd02181a80a20ba0a5d1264933be72a816c570e254e28c0caba7e9&",
        "embeds": [{
            "title": title,
            "description": description,
            "color": format_config['color']
        }]
    }


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitoringWebhook:
    def queue_error(self, error_data):
        try:
            if os.path.exists(ERROR_QUEUE_FILE):
                with open(ERROR_QUEUE_FILE, 'r') as f:
                    queue = json.load(f)
            else:
                queue = []
            queue.append(error_data)
            with open(ERROR_QUEUE_FILE, 'w') as f:
                json.dump(queue, f)
        except Exception as e:
            logger.error(f"Failed to queue error for Discord: {e}")

    def flush_error_queue(self):
        if not os.path.exists(ERROR_QUEUE_FILE):
            return
        try:
            with open(ERROR_QUEUE_FILE, 'r') as f:
                queue = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read error queue: {e}")
            return
        new_queue = []
        for error_data in queue:
            try:
                self.send_error(error_data, _is_internal_error=True, _from_queue=True)
            except Exception as e:
                logger.error(f"Failed to resend queued error: {e}")
                new_queue.append(error_data)
        if new_queue:
            try:
                with open(ERROR_QUEUE_FILE, 'w') as f:
                    json.dump(new_queue, f)
            except Exception as e:
                logger.error(f"Failed to update error queue: {e}")
        else:
            os.remove(ERROR_QUEUE_FILE)
    def __init__(self):
        self.webhook_url = DISCORD_MONITOR_WEBHOOK_URL
        self.log_batch = []
        self.last_log_send = self.load_last_log_send()
        self.batch_size = 1000
        self.weekly_interval = 7 * 24 * 60 * 60

    def load_last_log_send(self):
        try:
            with open('last_log_send.txt', 'r') as f:
                timestamp = f.read().strip()
                return datetime.fromisoformat(timestamp).astimezone()
        except (FileNotFoundError, ValueError):
            return get_local_now() - timedelta(days=7)

    def save_last_log_send(self):
        with open('last_log_send.txt', 'w') as f:
            f.write(get_local_now().isoformat())

    def send_error(self, error_data, _is_internal_error=False, _from_queue=False):
        # Prevent recursive error reporting except for queue flush
        if _is_internal_error and not _from_queue:
            logger.error(f"Failed to send error to Discord: {error_data['error']}")
            self.queue_error(error_data)
            return
        try:
            discord_payload = {
                "username": "Gmail Monitor - Error",
                "avatar_url": "https://cdn.discordapp.com/attachments/1344663464987066519/1412166880122376212/chart5.png?ex=68b74e65&is=68b5fce5&hm=f5b4f0933f8b6721276a329962cd4372f782a8f96e50bf048433513476b16104&",
                "embeds": [
                    {
                        "title": "❌ Error Alert",
                        "description": f"**Type:** `{error_data['type']}`\n**Time:** {error_data['timestamp']}\n**Error:**\n```\n{error_data['error']}\n```",
                        "color": 15158332
                    }
                ]
            }
            send_to_discord(self.webhook_url, discord_payload)
            logger.info("Error sent to Discord monitoring channel")
        except Exception as e:
            # Only log, and queue the error for later retry
            logger.error(f"Failed to send error to Discord: {e}")
            if not _from_queue:
                self.queue_error(error_data)


class Config:
    def __init__(self):
        self.config = {
            'max_messages': 50,
            'check_interval': 300,  # 5 minutes
            'webhook_timeout': 10,
            'batch_size': 10,
            'retry_attempts': 3
        }
    
    def load_from_file(self, filename='config.json'):
        try:
            with open(filename, 'r') as f:
                self.config.update(json.load(f))
        except FileNotFoundError:
            logger.warning(f"Config file {filename} not found, using defaults")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {filename}, using defaults")


class MessageCache:
    def __init__(self, max_size=1000):
        self.cache = set()
        self.max_size = max_size
    
    def is_processed(self, message_id):
        return message_id in self.cache
    
    def mark_processed(self, message_id):
        if len(self.cache) >= self.max_size:
            self.cache.pop()
        self.cache.add(message_id)

def get_service():
    try:
        with open(TOKEN_FILE, 'r') as token:
            creds_data = json.load(token)
        creds = Credentials.from_authorized_user_info(creds_data)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed credentials back to token.json
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            else:
                raise Exception("Token is invalid and cannot be refreshed")
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Error creating Gmail service: {str(e)}")
        raise

def ensure_single_instance():
    lock = FileLock("gmail_monitor.lock")
    try:
        lock.acquire(timeout=1)
        return lock
    except Exception:
        logger.error("Another instance is already running")
        sys.exit(1)

def get_last_processed_ids():
    try:
        with open(LAST_PROCESSED_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'incoming': None, 'outgoing': None}

def save_last_processed_ids(incoming_id=None, outgoing_id=None):
    current_ids = get_last_processed_ids()
    if incoming_id:
        current_ids['incoming'] = incoming_id
    if outgoing_id:
        current_ids['outgoing'] = outgoing_id
    
    with open(LAST_PROCESSED_FILE, 'w') as f:
        json.dump(current_ids, f)

def process_messages(service, query, last_id, message_type):
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=config.config['max_messages']
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            logger.info(f'No {message_type} messages found.')
            return last_id

        # Gmail returns newest-first
        newest_message_id = messages[0]['id']

        if last_id:
            #collect only messages newer than last_id
            new_messages = []
            for message in messages:
                if message['id'] == last_id:
                    break
                new_messages.append(message)
            # Reverse so they’re sent oldest → newest
            new_messages = list(reversed(new_messages))
        else:
            #First run, only send the newest message
            new_messages = [messages[0]]

        if not new_messages:
            logger.info(f"No new {message_type} messages to process.")
            return last_id or newest_message_id

        for message in new_messages:
            try:
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
                recipient = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'No Recipient')
                date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')

                discord_payload = create_discord_message(
                    message_type, subject, sender, recipient, date
                )

                if send_to_discord(DISCORD_WEBHOOK_URL, discord_payload):
                    logger.info(f"Sent {message_type} message {message['id']} to Discord")
                else:
                    logger.warning(f"Failed to send {message_type} message {message['id']} (rate limited?)")

            except Exception as e:
                logger.error(f"Error processing message {message['id']}: {str(e)}")
                continue

        return newest_message_id

    except Exception as e:
        logger.error(f"Error processing {message_type} messages: {str(e)}")
        return last_id

def main():
    monitor = MonitoringWebhook()
    process_messages._monitor = monitor

    lock = ensure_single_instance()
    monitor.flush_error_queue()
    last_error_flush = time.time()
    global config, message_cache

    config = Config()
    config.load_from_file()
    message_cache = MessageCache()
    try:
        service = get_service()
        last_processed = get_last_processed_ids()

        while True:
            try:
                # Process incoming emails
                incoming_query = 'in:inbox -label:draft -category:promotions -category:social'
                new_incoming_id = process_messages(
                    service, incoming_query, last_processed['incoming'], 'incoming'
                )

                # Process outgoing emails
                outgoing_query = 'in:sent -label:draft'
                new_outgoing_id = process_messages(
                    service, outgoing_query, last_processed['outgoing'], 'outgoing'
                )

                # Update last_processed dict so next loop uses new IDs
                last_processed['incoming'] = new_incoming_id
                last_processed['outgoing'] = new_outgoing_id
                save_last_processed_ids(new_incoming_id, new_outgoing_id)

            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                try:
                    monitor.send_error({
                        'timestamp': get_local_now().isoformat(),
                        'error': str(e),
                        'type': type(e).__name__
                    }, _is_internal_error=True)
                except Exception:
                    pass

            now = time.time()
            if now - last_error_flush >= 3600:
                monitor.flush_error_queue()
                last_error_flush = now

            time.sleep(config.config['check_interval'])

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        try:
            monitor.send_error({
                'timestamp': get_local_now().isoformat(),
                'error': str(e),
                'type': type(e).__name__
            }, _is_internal_error=True)
        except Exception:
            pass
        monitor.flush_error_queue()

    finally:
        lock.release()

if __name__ == '__main__':
    main()
