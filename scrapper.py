import feedparser

feeds = {
    "Christian News Network": "https://christiannews.net/feed/",
    "Christianity Daily": "https://www.christianitydaily.com/rss",
    "Religion News Service": "https://religionnews.com/feed/",
    "Christian News Now": "https://christiannewsnow.com/feed/",
}

for name, url in feeds.items():
    feed = feedparser.parse(url)
    print(f"{name}: {len(feed.entries)} articles found")
    for entry in feed.entries[:3]:
        print("  -", entry.title)
    print()