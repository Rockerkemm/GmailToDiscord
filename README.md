# GmailToDiscord

This project forwards emails from a Gmail account to a Discord channel using a webhook.

## Features
- Monitors Gmail inbox for new messages
- Sends email content to a specified Discord channel via webhook
- Docker support for easy deployment

## Setup
## How to Obtain `token.json`

`token.json` is required for Gmail API authentication. This program does NOT generate `token.json` directly. You must generate `token.json` separately using the official Gmail API Python Quickstart.

### How to Generate `token.json`
1. Go to the [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python).
2. Follow the instructions to enable the Gmail API and create OAuth client credentials.
3. Download the `credentials.json` file from Google Cloud Console.
4. Download the quickstart script from the  page.
5. Place `credentials.json` and `quickstart.py` in the same folder on your local machine.
6. Run the quickstart script:
	```sh
	python quickstart.py
	```
	- The script will prompt you to authorize access via a URL. Complete the authorization in your browser and paste the code back if prompted.
	- After successful authentication, `token.json` will be generated in the same directory.
7. Copy `token.json` to your GmailToDiscord project root.

**Note:** This GmailToDiscord program requires `token.json` to exist before it can access your Gmail account. It does not handle the OAuth flow or generate tokens itself.

For more details, see the [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python).


### 1. Clone the repository
```sh
git clone https://github.com/Rockerkemm/GmailToDiscord.git
cd GmailToDiscord
```


### 2. Install dependencies
```sh
pip install -r requirements.txt
```


### 3. Obtain `token.json` for Gmail API
Refer to the section above on "How to Obtain `token.json`" using the official Gmail API Python Quickstart. You must generate `token.json` separately and place it in your project root before running this program.


### 4. Get your Discord webhook URL
- Go to your Discord server
- Open the channel settings where you want to receive emails
- Go to **Integrations > Webhooks**
- Create a new webhook and copy the URL

For more info, see [Discord Webhooks Guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).


### 5. Configure environment variables
Create a `.env` file in the project root with the following variables:
```
DISCORD_WEBHOOK_URL=<your main Discord webhook URL>
DISCORD_MONITOR_WEBHOOK_URL=<your monitor Discord webhook URL>
```

**How to get Discord webhook URLs:**
- Go to your Discord server
- Open the channel settings where you want to receive emails or monitor events
- Go to **Integrations > Webhooks**
- Create a new webhook for each channel and copy the URLs


### 6. Run the application
#### Locally
```sh
python gmail_webhook.py
```

#### With Docker

Make sure your `.env` and `token.json` files are present in your project root before building the Docker image.

```sh
docker build -t gmail-to-discord .
```

To run with Docker Compose, use the provided `docker-compose.yml` from the repository:
```sh
docker-compose up
```

This will automatically use the correct environment variables and mount your `token.json` file as configured in the repository.

## License
MIT

## Resources
- [Gmail API Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Discord Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)


