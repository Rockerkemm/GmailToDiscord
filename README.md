# Gmail to Discord Webhook - OAuth 2.0 Setup Guide

This application monitors Gmail for new emails and sends notifications to Discord via webhooks. It uses OAuth 2.0 authentication and is designed for headless server deployment.

## 📋 Prerequisites

- Docker and Docker Compose installed
- Google Cloud Platform account
- Discord server with webhook permissions
- Gmail account (personal or Google Workspace)
- **Local machine with browser** (for initial OAuth setup)

## 🚀 Complete Setup Guide

### Step 1: Google Cloud Console Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Gmail API**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "+ CREATE CREDENTIALS" > "OAuth client ID"
   - Choose "Desktop application"
   - Name: `Gmail Discord Webhook Desktop`
   - Click "Create"
   - Download the JSON file and rename it to `credentials.json`

### Step 2: Discord Webhook Setup

1. **Create Discord Webhook**
   - Go to your Discord server
   - Right-click on the channel where you want notifications
   - Select "Edit Channel" > "Integrations" > "Webhooks"
   - Click "New Webhook"
   - Copy the webhook URL

### Step 3: Server Setup

1. **Clone/Download the project files to your server**
   ```bash
   git clone <your-repo-url>
   cd GmailToDiscord
   ```

2. **Copy OAuth credentials to server**
   ```bash
   # Copy the downloaded credentials.json to your server
   scp credentials.json user@server:/path/to/GmailToDiscord/
   ```

3. **Create environment file**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit the .env file with your values
   nano .env
   ```

4. **Configure environment variables**
   Edit the `.env` file:
   ```env
   # Discord webhook URL
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   
   # OAuth 2.0 configuration
   CREDENTIALS_FILE=credentials.json
   TOKEN_FILE=token.json
   ```

5. **Create required directories**
   ```bash
   mkdir -p data
   ```

### Step 4: OAuth Token Generation (Local Machine)

Since the server is headless, you need to generate the OAuth token on your local machine:


1. **Copy files to your local machine**
   ```bash
   # Copy credentials.json from server to local machine
   scp user@server:/path/to/GmailToDiscord/credentials.json ./
   
   # Copy the token generator script (if available)
   scp user@server:/path/to/GmailToDiscord/generate_token.py ./
   ```

2. **Install dependencies on local machine**
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

3. **Generate OAuth token**
   ```bash
   python generate_token.py
   ```
   
   This will:
   - Open your browser for Gmail authentication
   - Generate a `token.json` file
   - Display instructions for copying to server

4. **Copy token back to server**
   ```bash
   # Copy the generated token.json to server
   scp token.json user@server:/path/to/GmailToDiscord/data/
   ```

2. **Install dependencies on your local machine**
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

3. **Copy credentials.json to your local machine**
   ```bash
   # Copy the credentials.json file from server to local machine
   scp user@server:/path/to/GmailToDiscord/credentials.json ./
   ```

4. **Run the token generation script**
   ```bash
   python generate_token.py
   ```
   
   This will:
   - Verify your credentials.json file is valid
   - Open your browser for Gmail authentication
   - Generate a `token.json` file
   - Display detailed instructions for copying to server

5. **Copy the generated token to your server**
   ```bash
   # Copy the generated token.json to server
   scp token.json user@server:/path/to/GmailToDiscord/data/token.json
   ```

#### Important Notes for Token Generation

- **Browser Required**: The token generation must be done on a machine with browser access
- **Gmail Account**: Sign in with the Gmail account you want to monitor
- **Token Security**: The `token.json` file contains access tokens - keep it secure
- **Token Expiry**: Tokens refresh automatically, but if refresh fails, regenerate the token
- **One-Time Setup**: After initial setup, the server runs headlessly

### Step 5: Docker Deployment

1. **Build and start the container**:
   ```bash
   docker-compose up -d
   ```

2. **Check if it's running**:
   ```bash
   docker-compose ps
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f gmail-webhook
   ```

4. **You should see**:
   ```
   🚀 Starting Gmail to Discord webhook with OAuth 2.0...
   🔐 Loaded existing OAuth credentials
   🔐 OAuth 2.0 authentication successful
   🎉 First time running! Will process the most recent email.
   🔄 Starting continuous monitoring (checking every 10 seconds)
   ```

## 📁 Project Structure

```
GmailToDiscord/
├── gmail_webhook.py      # Main application
├── generate_token.py     # OAuth token generator (run locally)
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
├── .env                # Environment variables (create this)
├── .env.example        # Environment template
├── credentials.json    # OAuth 2.0 credentials (download from Google)
├── data/               # Persistent data directory
│   ├── token.json      # OAuth token (generated locally, copied here)
│   ├── last_processed.json
│   └── error_queue.json
└── README.md
```

## 🔧 Configuration

### Environment Variables (.env file)
```env
# Discord webhook URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url_here

# OAuth 2.0 configuration
CREDENTIALS_FILE=credentials.json
TOKEN_FILE=token.json
```

### Gmail Scopes
The application uses the minimal required scope:
- `https://www.googleapis.com/auth/gmail.readonly` - Read-only access to Gmail

### Message Filtering
The application automatically filters out:
- Draft messages (`DRAFT` label)
- Scheduled messages (`SCHEDULED` label)

## 🚨 Troubleshooting

### OAuth Token Issues

**Problem**: "OAuth token required - please generate token.json on a local machine"
```bash
# Follow the detailed token generation steps in Step 4 above
# Make sure token.json is copied to data/token.json on the server
ls -la data/token.json
```

**Problem**: "Failed to load existing credentials"
```bash
# Check if token.json exists and is valid JSON
cat data/token.json | python -m json.tool
```

**Problem**: "Failed to refresh credentials"
```bash
# The refresh token may be invalid, regenerate the token
# Run generate_token.py on your local machine again
# Follow Step 4 instructions above for complete process
```

### Authentication Flow Issues

**Problem**: "OAuth credentials file not found"
```bash
# Ensure credentials.json exists
ls -la credentials.json

# If missing, download from Google Cloud Console
```