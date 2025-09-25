import os
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
import logging
from datetime import datetime, timedelta
from ratelimit import limits, sleep_and_retry
from filelock import FileLock
from dotenv import load_dotenv
import sys
import time
from collections import deque
import traceback

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
def send_to_discord(webhook_url, payload, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 429:
            retry_after = response.json().get('retry_after', 5)
            time.sleep(retry_after / 1000)
            continue
        try:
            response.raise_for_status()
            return True
        except Exception:
            pass
    return False


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
    # 'date' is already formatted before being passed in
    description = (
        f"{direction}"
        f"{main_contact}\n"

        f"**Subject:** "
        f"{subject_text}\n"

        f"**Time: **"
        f"{date}"
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
            verbose_error_log("queue_error", e, {"error_data": error_data})

    def flush_error_queue(self):
        lock = FileLock(ERROR_QUEUE_FILE + ".lock")
        with lock:
            if not os.path.exists(ERROR_QUEUE_FILE):
                return
            try:
                with open(ERROR_QUEUE_FILE, 'r') as f:
                    queue = json.load(f)
            except Exception as e:
                verbose_error_log("flush_error_queue:read", e)
                return
            new_queue = []
            for error_data in queue:
                try:
                    self.send_error(error_data, _is_internal_error=True, _from_queue=True)
                except Exception as e:
                    verbose_error_log("flush_error_queue:send_error", e, {"error_data": error_data})
                    new_queue.append(error_data)
            if new_queue:
                try:
                    with open(ERROR_QUEUE_FILE, 'w') as f:
                        json.dump(new_queue, f)
                except Exception as e:
                    verbose_error_log("flush_error_queue:update", e)
            else:
                os.remove(ERROR_QUEUE_FILE)

    def send_error(self, error_data, _is_internal_error=False, _from_queue=False):
        if _is_internal_error and not _from_queue:
            verbose_error_log("send_error:internal", error_data.get('error', 'Unknown'), error_data)
            self.queue_error(error_data)
            return
        try:
            discord_payload = {
                "username": "Gmail Monitor - Error",
                "avatar_url": "https://cdn.discordapp.com/attachments/1344663464987066519/1412166880122376212/chart5.png?ex=68b74e65&is=68b5fce5&hm=f5b4f0933f8b6721276a329962cd4372f782a8f96e50bf048433513476b16104&",
                "embeds": [
                    {
                        "title": "❌ Error Alert",
                        "description": (
                            f"**Type:** `{error_data.get('type', 'N/A')}`\n"
                            f"**Time:** {error_data.get('timestamp', 'N/A')}\n"
                            f"**Error:**\n```\n{error_data.get('error', 'N/A')}\n```\n"
                            f"**Traceback:**\n```\n{error_data.get('traceback', 'N/A')}\n```\n"
                            f"**Error Data:**\n```\n{json.dumps(error_data, indent=2)}\n```"
                        ),
                        "color": 15158332
                    }
                ]
            }
            send_to_discord(self.webhook_url, discord_payload)
            logger.info("[send_error] Error sent to Discord monitoring channel")
        except Exception as e:
            verbose_error_log("send_error:discord", e, {"error_data": error_data})
            # Fallback: log the error data to file if Discord send fails
            try:
                self.queue_error(error_data)
            except Exception as qe:
                verbose_error_log("send_error:queue_error_fallback", qe, {"error_data": error_data})

class Config:
    def load_from_file(self, filename='config.json'):
        try:
            with open(filename, 'r') as f:
                self.config.update(json.load(f))
        except FileNotFoundError as e:
            verbose_error_log("Config.load_from_file:FileNotFoundError", e, {"filename": filename})
            MonitoringWebhook().send_error({
                'timestamp': datetime.now().isoformat(),
                'error': f"Config file {filename} not found\nTraceback: {traceback.format_exc()}",
                'type': 'FileNotFoundError',
                'traceback': traceback.format_exc()
            })
        except json.JSONDecodeError as e:
            verbose_error_log("Config.load_from_file:JSONDecodeError", e, {"filename": filename})
            MonitoringWebhook().send_error({
                'timestamp': datetime.now().isoformat(),
                'error': f"Invalid JSON in {filename}\nTraceback: {traceback.format_exc()}",
                'type': 'JSONDecodeError',
                'traceback': traceback.format_exc()
            })

def get_service():
    try:
        with open(TOKEN_FILE, 'r') as token:
            creds_data = json.load(token)
        creds = Credentials.from_authorized_user_info(creds_data)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            else:
                raise Exception("Token is invalid and cannot be refreshed")
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        verbose_error_log("get_service", e)
        raise

def ensure_single_instance():
    lock = FileLock("gmail_monitor.lock")
    try:
        lock.acquire(timeout=1)
        return lock
    except Exception as e:
        verbose_error_log("ensure_single_instance", e)
        sys.exit(1)

def get_last_processed_id():
    try:
        with open(LAST_PROCESSED_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_id')
    except (FileNotFoundError, json.JSONDecodeError) as e:
        verbose_error_log("get_last_processed_id", e)
        return None

def verbose_error_log(context, error, extra=None):
    logger.error(
        f"[{context}] Exception occurred!\n"
        f"Type: {type(error).__name__}\n"
        f"Error: {error}\n"
        f"Extra: {extra}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )

def main():
    monitor = MonitoringWebhook()
    with ensure_single_instance() as lock:
        monitor.flush_error_queue()
        last_error_flush = time.time()
        global config
        config = Config()
        config.load_from_file()
        try:
            service = get_service()
            last_id = get_last_processed_id()
            while True:
                try:
                    messages = get_combined_messages(service, last_id)
                    for msg in messages:
                        try:
                            discord_payload = create_discord_message(
                                msg['type'], msg['subject'], msg['sender'], msg['recipient'], msg['date']
                            )
                        except (KeyError, ValueError) as e:
                            verbose_error_log("main:create_discord_message", e, {"msg": msg})
                            monitor.send_error({
                                'timestamp': datetime.now().isoformat(),
                                'error': str(e),
                                'type': type(e).__name__,
                                'traceback': traceback.format_exc(),
                                'msg': msg
                            }, _is_internal_error=True)
                            continue
                        if send_to_discord(DISCORD_WEBHOOK_URL, discord_payload):
                            logger.info(f"[main] Sent {msg['type']} message {msg['id']} to Discord")
                            last_id = msg['id']
                            get_last_processed_id(last_id)
                        else:
                            logger.warning(f"[main] Failed to send {msg['type']} message {msg['id']} (rate limited?)")
                    now = time.time()
                    if now - last_error_flush >= 3600:
                        monitor.flush_error_queue()
                        last_error_flush = now
                    time.sleep(config.config['check_interval'])
                except Exception as e:
                    verbose_error_log("main loop", e)
                    try:
                        monitor.send_error({
                            'timestamp': datetime.now().isoformat(),
                            'error': str(e),
                            'type': type(e).__name__,
                            'traceback': traceback.format_exc()
                        }, _is_internal_error=True)
                    except Exception as inner_e:
                        verbose_error_log("main loop:send_error", inner_e)
        except Exception as e:
            verbose_error_log("main", e)
            try:
                monitor.send_error({
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'type': type(e).__name__,
                    'traceback': traceback.format_exc()
                }, _is_internal_error=True)
            except Exception as inner_e:
                verbose_error_log("main:fatal_send_error", inner_e)
            monitor.flush_error_queue()
