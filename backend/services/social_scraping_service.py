"""
Social media scraping service — India civic misinformation focus.

Uses the most reliable method per platform:
  - Reddit  → Public JSON API (no auth needed, very reliable)
  - Twitter → Nitter instances (public Twitter mirrors)
  - YouTube → Search page HTML (lightweight, no JS needed)
  - Instagram → Hashtag explore via StealthyFetcher

Hard-capped at 50 posts per crawl cycle.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional
from urllib.parse import quote_plus

from core.logging import get_logger, log_event, stage_duration_ms, stage_start
from models.social_schemas import ScrapedSocialPost

logger = get_logger("truthmates.social_scraping")

_MAX_POSTS = 50

# ── India-focused default keywords ──────────────────────────────────────────

INDIA_KEYWORDS = [
    "india government scam",
    "modi fake news",
    "BJP misleading",
    "Congress fake claim",
    "aadhaar data leak",
    "UPI fraud",
    "indian army fake",
    "PIB fact check india",
    "india election fake",
    "pradhan mantri yojana fraud",
    "digital india scam",
    "ayushman bharat fake",
    "indian politics misinformation",
    "hindu muslim fake news india",
    "farmer protest fake",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _post_id(platform: str, content: str, url: str = "") -> str:
    return sha256(f"{platform}|{url}|{content[:200]}".encode()).hexdigest()[:16]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_engagement(raw: str) -> str:
    """Convert '12.5K' style strings to readable format."""
    raw = _clean(raw)
    if not raw or raw == "0":
        return ""
    return raw


# ── Reddit (JSON API — most reliable) ───────────────────────────────────────

async def crawl_reddit(keywords: list[str], max_posts: int = 15) -> list[ScrapedSocialPost]:
    """Use Reddit's public JSON API — no auth, no HTML parsing."""
    started = stage_start()
    posts: list[ScrapedSocialPost] = []

    try:
        from scrapling.fetchers import Fetcher
    except ImportError:
        log_event(logger, "import_error", platform="reddit", error="scrapling not installed")
        return posts

    for kw in keywords:
        if len(posts) >= max_posts:
            break
        try:
            url = f"https://www.reddit.com/search.json?q={quote_plus(kw)}&sort=new&t=week&limit=10"
            resp = await asyncio.to_thread(
                Fetcher.get, url,
                stealthy_headers=True,
            )

            # Reddit JSON API returns raw JSON
            raw_text = resp.text if hasattr(resp, 'text') else str(resp)
            
            # Try to parse as JSON
            try:
                data = json.loads(raw_text)
            except (json.JSONDecodeError, TypeError):
                # If Scrapling returns an Adaptor, try to get body text
                body_els = resp.css("body") if hasattr(resp, 'css') else []
                if body_els:
                    raw_text = body_els[0].text
                    data = json.loads(raw_text)
                else:
                    continue

            children = data.get("data", {}).get("children", [])
            for child in children:
                if len(posts) >= max_posts:
                    break
                d = child.get("data", {})
                title = _clean(d.get("title", ""))
                selftext = _clean(d.get("selftext", ""))
                content = f"{title}. {selftext}" if selftext else title
                if not content or len(content) < 15:
                    continue

                subreddit = d.get("subreddit", "")
                author = d.get("author", "unknown")
                permalink = d.get("permalink", "")
                post_url = f"https://reddit.com{permalink}" if permalink else ""
                score = d.get("score", 0)
                num_comments = d.get("num_comments", 0)
                created = d.get("created_utc")
                posted_at = datetime.fromtimestamp(created, tz=timezone.utc) if created else None

                posts.append(ScrapedSocialPost(
                    platform="reddit",
                    post_id=_post_id("reddit", content, post_url),
                    author_handle=f"u/{author}",
                    author_name=author,
                    content=content,
                    post_url=post_url,
                    posted_at=posted_at,
                    engagement={"upvotes": str(score), "comments": str(num_comments), "subreddit": f"r/{subreddit}"},
                    scraped_at=_now(),
                ))

            log_event(logger, "reddit_keyword_done", keyword=kw, found=len(posts))
        except Exception as exc:
            log_event(logger, "reddit_error", keyword=kw, error=str(exc)[:200])

    log_event(logger, "reddit_done", total=len(posts), ms=stage_duration_ms(started))
    return posts[:max_posts]


# ── Twitter via Nitter ───────────────────────────────────────────────────────

_NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.cz",
]

async def crawl_twitter(keywords: list[str], max_posts: int = 15) -> list[ScrapedSocialPost]:
    """Scrape Twitter via Nitter — public mirrors with simple HTML."""
    started = stage_start()
    posts: list[ScrapedSocialPost] = []

    try:
        from scrapling.fetchers import Fetcher
    except ImportError:
        log_event(logger, "import_error", platform="twitter", error="scrapling not installed")
        return posts

    for kw in keywords:
        if len(posts) >= max_posts:
            break

        scraped = False
        for instance in _NITTER_INSTANCES:
            if scraped or len(posts) >= max_posts:
                break
            try:
                url = f"{instance}/search?f=tweets&q={quote_plus(kw)}"
                page = await asyncio.to_thread(
                    Fetcher.get, url,
                    stealthy_headers=True,
                )

                # Nitter uses .timeline-item for each tweet
                items = page.css(".timeline-item") or page.css(".tweet-body") or []
                for item in items:
                    if len(posts) >= max_posts:
                        break

                    # Tweet content
                    content_el = item.css(".tweet-content") or item.css(".media-body")
                    content = _clean(content_el[0].text if content_el else "")
                    if not content or len(content) < 15:
                        continue

                    # Author
                    handle_el = item.css(".username") or item.css("a.tweet-link")
                    handle = _clean(handle_el[0].text if handle_el else "")
                    name_el = item.css(".fullname")
                    name = _clean(name_el[0].text if name_el else handle)

                    # Link
                    link_el = item.css("a.tweet-link")
                    href = link_el[0].attrib.get("href", "") if link_el else ""
                    tweet_url = f"https://x.com{href}" if href.startswith("/") else ""

                    # Engagement
                    engagement = {}
                    stat_els = item.css(".tweet-stat") or []
                    stat_labels = ["replies", "retweets", "likes"]
                    for i, stat in enumerate(stat_els[:3]):
                        val = _clean(stat.text)
                        if val and i < len(stat_labels):
                            engagement[stat_labels[i]] = val

                    posts.append(ScrapedSocialPost(
                        platform="twitter",
                        post_id=_post_id("twitter", content, tweet_url),
                        author_handle=handle if handle.startswith("@") else f"@{handle}",
                        author_name=name or "Unknown",
                        content=content,
                        post_url=tweet_url,
                        posted_at=None,
                        engagement=engagement,
                        scraped_at=_now(),
                    ))

                scraped = True
                log_event(logger, "nitter_ok", instance=instance, keyword=kw, found=len(posts))
            except Exception as exc:
                log_event(logger, "nitter_fail", instance=instance, keyword=kw, error=str(exc)[:100])

    log_event(logger, "twitter_done", total=len(posts), ms=stage_duration_ms(started))
    return posts[:max_posts]


# ── YouTube ──────────────────────────────────────────────────────────────────

async def crawl_youtube(keywords: list[str], max_posts: int = 15) -> list[ScrapedSocialPost]:
    """Scrape YouTube search results page."""
    started = stage_start()
    posts: list[ScrapedSocialPost] = []

    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        log_event(logger, "import_error", platform="youtube", error="scrapling not installed")
        return posts

    for kw in keywords:
        if len(posts) >= max_posts:
            break
        try:
            url = f"https://www.youtube.com/results?search_query={quote_plus(kw)}"
            page = await asyncio.to_thread(
                StealthyFetcher.fetch, url,
                headless=True,
                network_idle=True,
            )

            # Extract from ytInitialData JSON embedded in page
            scripts = page.css("script") or []
            for script in scripts:
                text = script.text or ""
                if "ytInitialData" not in text:
                    continue

                # Extract JSON from var ytInitialData = {...};
                match = re.search(r'var\s+ytInitialData\s*=\s*(\{.*?\});\s*</', text, re.DOTALL)
                if not match:
                    match = re.search(r'ytInitialData\s*=\s*(\{.*?\});\s*', text, re.DOTALL)
                if not match:
                    continue

                try:
                    yt_data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

                # Navigate to video renderers
                contents = (
                    yt_data.get("contents", {})
                    .get("twoColumnSearchResultsRenderer", {})
                    .get("primaryContents", {})
                    .get("sectionListRenderer", {})
                    .get("contents", [])
                )

                for section in contents:
                    items = section.get("itemSectionRenderer", {}).get("contents", [])
                    for item in items:
                        if len(posts) >= max_posts:
                            break
                        renderer = item.get("videoRenderer")
                        if not renderer:
                            continue

                        title_runs = renderer.get("title", {}).get("runs", [])
                        title = " ".join(r.get("text", "") for r in title_runs)
                        title = _clean(title)
                        if not title or len(title) < 10:
                            continue

                        video_id = renderer.get("videoId", "")
                        video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

                        channel = _clean(
                            renderer.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                        )
                        views = _clean(
                            renderer.get("viewCountText", {}).get("simpleText", "")
                        )

                        # Get description snippet
                        desc_runs = renderer.get("detailedMetadataSnippets", [{}])
                        desc = ""
                        if desc_runs:
                            snippet_runs = desc_runs[0].get("snippetText", {}).get("runs", [])
                            desc = " ".join(r.get("text", "") for r in snippet_runs)

                        content = f"{title}. {_clean(desc)}" if desc else title

                        posts.append(ScrapedSocialPost(
                            platform="youtube",
                            post_id=_post_id("youtube", title, video_url),
                            author_handle=channel or "unknown",
                            author_name=channel or "Unknown Channel",
                            content=content,
                            post_url=video_url,
                            posted_at=None,
                            engagement={"views": views} if views else {},
                            scraped_at=_now(),
                        ))

                break  # Only need first ytInitialData script

            # Fallback: parse HTML if JSON extraction failed
            if not posts:
                title_els = page.css("a#video-title") or []
                for el in title_els[:max_posts]:
                    title = _clean(el.text)
                    if not title or len(title) < 10:
                        continue
                    href = el.attrib.get("href", "")
                    video_url = f"https://www.youtube.com{href}" if href.startswith("/") else href
                    posts.append(ScrapedSocialPost(
                        platform="youtube",
                        post_id=_post_id("youtube", title, video_url),
                        author_handle="unknown",
                        author_name="YouTube",
                        content=title,
                        post_url=video_url,
                        posted_at=None,
                        engagement={},
                        scraped_at=_now(),
                    ))

            log_event(logger, "youtube_keyword_done", keyword=kw, found=len(posts))
        except Exception as exc:
            log_event(logger, "youtube_error", keyword=kw, error=str(exc)[:200])

    log_event(logger, "youtube_done", total=len(posts), ms=stage_duration_ms(started))
    return posts[:max_posts]


# ── Instagram ────────────────────────────────────────────────────────────────

async def crawl_instagram(keywords: list[str], max_posts: int = 10) -> list[ScrapedSocialPost]:
    """Lightweight Instagram scraper — extracts from hashtag pages."""
    started = stage_start()
    posts: list[ScrapedSocialPost] = []

    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        log_event(logger, "import_error", platform="instagram", error="scrapling not installed")
        return posts

    for kw in keywords:
        if len(posts) >= max_posts:
            break
        try:
            tag = re.sub(r"[^a-zA-Z0-9]", "", kw.lower())
            url = f"https://www.instagram.com/explore/tags/{tag}/"
            page = await asyncio.to_thread(
                StealthyFetcher.fetch, url,
                headless=True,
                network_idle=True,
            )

            # Try og:description meta (contains post counts and descriptions)
            meta_els = page.css('meta[property="og:description"]') or []
            for meta in meta_els:
                desc = _clean(meta.attrib.get("content", ""))
                if desc and len(desc) > 20:
                    posts.append(ScrapedSocialPost(
                        platform="instagram",
                        post_id=_post_id("instagram", desc, url),
                        author_handle=f"#{tag}",
                        author_name=f"#{tag}",
                        content=desc,
                        post_url=url,
                        posted_at=None,
                        engagement={},
                        scraped_at=_now(),
                    ))

            # Extract image alt texts (often contain captions)
            img_els = page.css("img[alt]") or []
            for img in img_els:
                if len(posts) >= max_posts:
                    break
                alt = _clean(img.attrib.get("alt", ""))
                if not alt or len(alt) < 20 or "photo" in alt.lower() and len(alt) < 40:
                    continue
                link_els = img.parent.css("a[href*='/p/']") if img.parent else []
                post_url_ig = ""
                if link_els:
                    href = link_els[0].attrib.get("href", "")
                    post_url_ig = f"https://www.instagram.com{href}" if href.startswith("/") else href

                posts.append(ScrapedSocialPost(
                    platform="instagram",
                    post_id=_post_id("instagram", alt, post_url_ig or url),
                    author_handle="unknown",
                    author_name="Instagram User",
                    content=alt,
                    post_url=post_url_ig or url,
                    posted_at=None,
                    engagement={},
                    scraped_at=_now(),
                ))

            log_event(logger, "instagram_keyword_done", keyword=kw, found=len(posts))
        except Exception as exc:
            log_event(logger, "instagram_error", keyword=kw, error=str(exc)[:200])

    log_event(logger, "instagram_done", total=len(posts), ms=stage_duration_ms(started))
    return posts[:max_posts]


# ── Dispatcher ───────────────────────────────────────────────────────────────

_CRAWLERS = {
    "twitter": crawl_twitter,
    "youtube": crawl_youtube,
    "reddit": crawl_reddit,
    "instagram": crawl_instagram,
}


async def crawl_all_platforms(
    keywords: list[str] | None = None,
    platforms: list[str] | None = None,
    max_posts: int = _MAX_POSTS,
) -> list[ScrapedSocialPost]:
    """Crawl all platforms concurrently. Defaults to India-focused keywords."""
    if not keywords:
        keywords = INDIA_KEYWORDS[:8]  # Use top 8 India keywords

    if not platforms:
        platforms = list(_CRAWLERS.keys())

    per_platform = max(5, max_posts // len(platforms))

    tasks = []
    for p in platforms:
        crawler = _CRAWLERS.get(p)
        if crawler:
            tasks.append(crawler(keywords, max_posts=per_platform))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_posts: list[ScrapedSocialPost] = []
    for r in results:
        if isinstance(r, list):
            all_posts.extend(r)
        elif isinstance(r, Exception):
            log_event(logger, "crawl_exception", error=str(r)[:200])

    # Deduplicate
    seen: set[str] = set()
    deduped: list[ScrapedSocialPost] = []
    for post in all_posts:
        if post.post_id not in seen:
            seen.add(post.post_id)
            deduped.append(post)

    return deduped[:max_posts]
