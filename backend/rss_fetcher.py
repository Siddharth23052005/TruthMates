import feedparser
from core.logging import get_logger

logger = get_logger("truthmates.rss_fetcher")

FEEDS = {
    "AltNews": "https://www.altnews.in/feed/",
    "BoomLive": "https://www.boomlive.in/feed",
    "Snopes": "https://www.snopes.com/feed/"
}

def fetch_rss_feeds() -> list[dict]:
    results = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                logger.warning(f"Malformed feed from {source}: {feed.bozo_exception}")
            
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                published = entry.get("published", "")
                
                if not title or len(title) < 10:
                    continue
                
                title_lower = title.lower()
                if any(x in title_lower for x in ["about", "contact", "privacy", "advertise", "subscribe"]):
                    continue
                
                results.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": source
                })
        except Exception as exc:
            logger.error(f"Failed to fetch {source} feed: {exc}")
    
    return results
