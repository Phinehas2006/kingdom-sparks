# Kingdom Sparks Daily Digest

Kingdom Sparks Daily Digest is a Python script that gathers Christian news and humour, selects headlines for a daily update, and sends the digest by email.

## What it does

When you run `digest.py`, it:

1. Reads Christian news articles from RSS feeds.
2. Collects humour posts from Christian meme communities on Reddit.
3. Searches Google News RSS for Nigeria and Cameroon church and ministry headlines.
4. Ranks and filters headlines, removes duplicates, and limits how many items come from each source.
5. Fetches a random World English Bible verse.
6. Writes a plain-text digest to `digest.txt` and prepares an HTML version for email, with the plain text as a fallback.
7. Sends the email through Gmail when the required email environment variables are set.

## Requirements

- Python 3
- The packages listed in `requirements.txt`
- A Gmail address and Gmail app password for sending email

## Setup

In PowerShell, from the project folder, create and activate a virtual environment, then install the packages:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set the email settings in the same PowerShell session where you will run the script. Use a Gmail app password for `EMAIL_PASSWORD`:

```powershell
$env:EMAIL_ADDRESS = "your-address@gmail.com"
$env:EMAIL_PASSWORD = "your-gmail-app-password"
$env:EMAIL_TO = "recipient@example.com"
```

`EMAIL_TO` is optional; if it is not set, the digest is sent to `EMAIL_ADDRESS`. The script reads these values from the process environment. Then run:

```powershell
python digest.py
```

If `EMAIL_PASSWORD` is not set, the script still creates or replaces `digest.txt` but skips sending the email.

## Other file

`scrapper.py` is a small feed-checking script that prints the number of articles found in several feeds and shows a few headlines.
