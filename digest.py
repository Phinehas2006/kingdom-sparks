from dotenv import load_dotenv
import os
import smtplib
import ssl
from email.message import EmailMessage
from html import escape

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

AGENT = "KingdomSparksDigest/1.0"

# How many items to keep in each section
TOP_NEWS = 5
TOP_HUMOUR = 4
TOP_LOCAL = 10

# Words that make an item more useful for an edifying page
BOOST = ["youth", "faith", "hope", "love", "prayer", "scholarship",
         "children", "community", "miracle", "testimony", "gospel",
         "revival", "devotional"]

# Words that push an item out of the digest (edit freely)
AVOID = ["arrest", "remand", "allegation", "alleged", "scandal",
         "prison", "court"]

# ---------- SOURCES ----------

news_feeds = {
    "Christian News Network": "https://christiannews.net/feed/",
    "Christianity Daily": "https://www.christianitydaily.com/rss",
    "Religion News Service": "https://religionnews.com/feed/",
    "Christian News Now": "https://christiannewsnow.com/feed/",
    "Christian Today": "https://www.christiantoday.com/rss/",
    "The Christian Post": "https://www.christianpost.com/rss",
}

humour_feeds = {
    "r/DankChristianMemes": "https://www.reddit.com/r/dankchristianmemes/top/.rss?t=day",
    "r/ChristianMemes": "https://www.reddit.com/r/ChristianMemes/top/.rss?t=day",
}

# search phrase -> a LOWERCASE word that must appear in the headline
people = {
    "Michael Orokpo": "orokpo",
    "Arome Osayi": "arome",
    "Benson Idahosa": "idahosa",
    "Johnson Suleman": "suleman",
    "Abel Damina": "damina",
    "David Ibiyeomie": "ibiyeomie",
    "David Oyedepo": "oyedepo",
    "Joshua Selman": "selman",
    "Paul Enenche": "enenche",
    "Chris Oyakhilome": "oyakhilome",
    "E.A. Adeboye": "adeboye",
    "Eugene Awe": "eugene awe",
    "Sam Adeyemi": "sam adeyemi",
    "David Abioye": "abioye",
    "Joel Ogebe": "joel ogebe",
    "Sound of Salem": "sound of salem",
    "Tunde Bakare": "bakare",
    "Enoch Adeyemi": "enoch adeyemi",
    "Full Gospel Mission": "full gospel",
    "Fathers of Faith": "fathers of faith",
    "Nigeria church news": "",
    "Cameroon church news": "",
    "Apostle N.F Roland": "roland",
    "Apostle E Paul Mbuagbor": "mbuagbor",
}

# These searches use Google's Cameroon edition instead of Nigeria's
CAMEROON = {"Cameroon church news", "Apostle N.F Roland",
            "Apostle E Paul Mbuagbor"}

# ---------- FUNCTIONS ----------

def clean(text):
    """Remove HTML tags and return plain text."""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def short_summary(raw_html, limit=160):
    """Plain-text summary, cut at a word boundary."""
    text = clean(raw_html).split("Read More")[0].strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "..."
    return text


def score(title):
    """Higher is better. -99 means 'leave this out'."""
    t = title.lower()
    if any(word in t for word in AVOID):
        return -99
    return sum(1 for word in BOOST if word in t)


def google_news_url(query, exact, country="NG"):
    """Build a Google News RSS search address."""
    q = f'"{query}"' if exact else query
    return ("https://news.google.com/rss/search?q="
            + quote(q + " when:3d")
            + f"&hl=en-{country}&gl={country}&ceid={country}:en")


def get_bible_verse():
    """Fetch a random World English Bible verse."""
    try:
        response = requests.get("https://bible-api.com/data/web/random", timeout=15)
        response.raise_for_status()
        verse = response.json()["random_verse"]
        reference = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
        text = verse["text"].strip()
        return f"{reference} (World English Bible)\n{text}"
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        print(f"WARNING: could not fetch Bible verse: {error}")
        return "Today's verse is unavailable. Please try again later."


def collect(feeds, per_feed, with_summary=False, must_match=None):
    """Read each feed and return a list of items."""
    items = []
    for name, url in feeds.items():
        feed = feedparser.parse(url, agent=AGENT)
        if not feed.entries:
            print(f"WARNING: no items from {name}")
            continue
        for entry in feed.entries[:per_feed]:
            title = entry.title
            if must_match is not None and must_match[name] not in title.lower():
                continue
            summary = ""
            if with_summary:
                summary = short_summary(entry.get("summary", ""))
            items.append({
                "source": name,
                "title": title,
                "link": entry.link,
                "summary": summary,
                "score": score(title),
            })
    return items


def pick_top(items, n, max_per_source):
    """Keep the best n items, with no repeats."""
    items = [i for i in items if i["score"] > -50]
    items.sort(key=lambda i: i["score"], reverse=True)
    chosen, seen, count = [], set(), {}
    for i in items:
        key = i["title"].lower()
        if key in seen or count.get(i["source"], 0) >= max_per_source:
            continue
        seen.add(key)
        count[i["source"]] = count.get(i["source"], 0) + 1
        chosen.append(i)
        if len(chosen) == n:
            break
    return chosen


def add_section(lines, heading, items):
    lines.append(f"=== {heading} ===")
    if not items:
        lines.append("(nothing worth posting today)")
    for number, item in enumerate(items, start=1):
        lines.append(f"{number}. [{item['source']}] {item['title']}")
        if item["summary"]:
            lines.append(f"   {item['summary']}")
        lines.append(f"   {item['link']}")
        lines.append("")
    lines.append("")


def add_text_section(lines, heading, text):
    lines.append(f"=== {heading} ===")
    lines.append(text)
    lines.append("")


def build_html(news, humour, local, now):
    """Build an email-safe HTML version of the digest."""
    def render_section(title, items, heading_color):
        cards = []
        if not items:
            cards.append(
                '<tr><td style="padding:16px;color:#334155;font-size:15px;'
                'line-height:1.5;">Nothing worth posting today.</td></tr>'
            )
        for item in items:
            source = escape(str(item.get("source", "")))
            headline = escape(str(item.get("title", "")))
            link = escape(str(item.get("link", "")), quote=True)
            summary = escape(str(item.get("summary", "")))
            summary_html = (
                f'<p style="margin:10px 0 0;color:#334155;font-size:14px;'
                f'line-height:1.6;">{summary}</p>'
                if summary else ""
            )
            cards.append(
                '<tr><td style="padding:14px 16px;background-color:#f8fafc;'
                'border:1px solid #e2e8f0;border-radius:8px;">'
                f'<p style="margin:0 0 6px;color:#475569;font-size:12px;'
                f'font-weight:bold;letter-spacing:.3px;">{source}</p>'
                f'<a href="{link}" style="color:#1d4ed8;font-size:16px;'
                f'font-weight:bold;line-height:1.45;text-decoration:underline;">'
                f'{headline}</a>{summary_html}</td></tr>'
                '<tr><td height="10" style="font-size:0;line-height:0;">&nbsp;'
                '</td></tr>'
            )
        return (
            '<tr><td style="padding:24px 24px 8px;">'
            f'<h2 style="margin:0;color:{heading_color};font-size:20px;'
            f'line-height:1.3;">{title}</h2></td></tr>'
            '<tr><td style="padding:0 24px 8px;"><table role="presentation" '
            'width="100%" cellpadding="0" cellspacing="0" border="0">'
            + "".join(cards) + '</table></td></tr>'
        )

    safe_now = escape(str(now))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Kingdom Sparks Daily Digest</title></head>'
        '<body style="margin:0;padding:0;background-color:#eef2f7;'
        'font-family:Arial,Helvetica,sans-serif;color:#172033;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="background-color:#eef2f7;"><tr><td align="center" '
        'style="padding:24px 12px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0" style="width:100%;max-width:600px;background-color:#ffffff;'
        'border:1px solid #dbe3ee;border-radius:12px;overflow:hidden;">'
        '<tr><td style="padding:28px 24px;background-color:#142b4a;color:#ffffff;">'
        '<h1 style="margin:0;font-size:25px;line-height:1.25;color:#ffffff;">'
        'Kingdom Sparks Daily Digest</h1>'
        f'<p style="margin:8px 0 0;color:#e2e8f0;font-size:14px;">{safe_now}</p>'
        '</td></tr>'
        + render_section("Top Headlines", news, "#1d4ed8")
        + render_section("Humour Corner", humour, "#047857")
        + render_section("Nigeria &amp; Cameroon Religious Space", local, "#7c3aed")
        + '<tr><td style="padding:18px 24px 24px;color:#64748b;font-size:12px;'
        'line-height:1.5;border-top:1px solid #e2e8f0;">'
        'Prepared for Kingdom Sparks</td></tr></table></td></tr></table>'
        '</body></html>'
    )


def send_email(subject, body, html_body):
    """Send the digest by Gmail."""
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    receiver = os.environ.get("EMAIL_TO", sender)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender, password)
        server.send_message(msg)


# ---------- COLLECT ----------

news = pick_top(collect(news_feeds, 8, with_summary=True), TOP_NEWS, 1)
humour = pick_top(collect(humour_feeds, 10), TOP_HUMOUR, 4)
bible_verse = get_bible_verse()

local_feeds = {
    name: google_news_url(
        name,
        exact=(word != ""),
        country="CM" if name in CAMEROON else "NG",
    )
    for name, word in people.items()
}
local = pick_top(
    collect(local_feeds, 6, must_match=people), TOP_LOCAL, 1
)

# ---------- BUILD THE DIGEST ----------

now = datetime.now().strftime("%Y-%m-%d %H:%M")
lines = [f"KINGDOM SPARKS DAILY DIGEST - {now}", ""]
html_body = build_html(news, humour, local, now)

add_section(lines, "TOP HEADLINES", news)
add_section(lines, "JOKE IDEAS & HUMOUR FROM REDDIT", humour)
add_text_section(lines, "BIBLE VERSE OF THE DAY", bible_verse)
add_section(lines, "NIGERIA & CAMEROON RELIGIOUS SPACE", local)

digest = "\n".join(lines)

with open("digest.txt", "w", encoding="utf-8") as f:
    f.write(digest)

print(f"Done. Kept {len(news)} headlines, {len(humour)} humour, "
      f"{len(local)} Nigeria/Cameroon items.")

# ---------- SEND THE EMAIL ----------

if "EMAIL_PASSWORD" in os.environ:
    send_email(f"Kingdom Sparks Digest - {now}", digest, html_body)
    print("Email sent.")
else:
    print("Email skipped (no EMAIL_PASSWORD set).")
