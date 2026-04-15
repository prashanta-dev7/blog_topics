#!/usr/bin/env python3
"""
AZA Blog Agent — Content Intelligence Feed Generator (v5.1)
Fetches from 36 editorial/competitor sources, Google Trends RSS,
and pytrends keyword intelligence for IN + US markets.
Keywords are pulled LIVE from published Google Sheets CSVs.
Output: feed.json consumed by the Content Intelligence Desk (index.html)
"""

import json
import csv
import io
import feedparser
import requests
import re
import hashlib
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser

# ── Config ──────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (AZA Blog Agent/5.1; +https://www.azafashions.com)"
}
MAX_AGE_DAYS = 60
CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
GOOGLE_TRENDS_URL = "https://trends.google.com/trending/rss?geo=IN"

# ── Google Sheets Published CSV URLs ───────────────────────────────────
# These are public "Publish to web" CSV links from the AZA Keyword Tracker.
# To update keywords, edit the Google Sheet — changes auto-propagate on next run.
SHEET_KEYWORDS_IN = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRsmtSEaFevi3T7sM8E5j4wgPNgCI2M3l7TQYLEV3mOFZd0CLojejG2zASpbfNfInAj2G18a-jSfHS1/pub?gid=114123390&single=true&output=csv"
SHEET_KEYWORDS_US = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRsmtSEaFevi3T7sM8E5j4wgPNgCI2M3l7TQYLEV3mOFZd0CLojejG2zASpbfNfInAj2G18a-jSfHS1/pub?gid=1487731411&single=true&output=csv"

# ── Sources (36 sites) ─────────────────────────────────────────────────
SOURCES = [
    {"name":"AZA Blog","tier":"owned","pages":["https://www.azafashions.com/blog/"],"feeds":["https://www.azafashions.com/blog/feed"]},
    {"name":"AZA Magazine","tier":"owned","pages":["https://magazine.azafashions.com/"],"feeds":["https://magazine.azafashions.com/feed"]},
    {"name":"Kalki Fashion Blog","tier":"competitor","pages":[
        "https://blog.kalkifashion.com/",
        "https://blog.kalkifashion.com/category/real-brides/",
        "https://blog.kalkifashion.com/category/menswear/",
        "https://blog.kalkifashion.com/category/kalki-collection/"
    ],"feeds":["https://blog.kalkifashion.com/feed/"]},
    {"name":"Pernia's Pop-Up Shop","tier":"competitor","pages":["https://www.perniaspopupshop.com/blog/"],"feeds":["https://www.perniaspopupshop.com/blog/feed"]},
    {"name":"Utsav Fashion","tier":"competitor","pages":["https://www.utsavfashion.com/blog/"],"feeds":["https://www.utsavfashion.com/blog/feed"]},
    {"name":"Kalki Fashion Main","tier":"competitor","pages":["https://www.kalkifashion.com/in/blog/"],"feeds":["https://www.kalkifashion.com/in/blog/rss.xml"]},
    {"name":"FabIndia","tier":"competitor","pages":["https://www.fabindia.com/blogs/news"],"feeds":["https://www.fabindia.com/blogs/news.atom"]},
    {"name":"House of Indya","tier":"competitor","pages":["https://www.houseofindya.com/blog"],"feeds":["https://www.houseofindya.com/blogs/news.atom"]},
    {"name":"Manyavar","tier":"competitor","pages":["https://www.manyavar.com/en-in/blog","https://www.manyavar.com/blog"],"feeds":["https://www.manyavar.com/en-in/blog/feed","https://www.manyavar.com/blog/feed"]},
    {"name":"BIBA","tier":"competitor","pages":["https://www.biba.in/blogs/fashion"],"feeds":["https://www.biba.in/blogs/fashion.atom"]},
    {"name":"Anita Dongre","tier":"competitor","pages":["https://www.anitadongre.com/blogs/news"],"feeds":["https://www.anitadongre.com/blogs/news.atom"]},
    {"name":"Sabyasachi","tier":"competitor","pages":["https://www.sabyasachi.com/blog"],"feeds":["https://www.sabyasachi.com/blog/rss.xml"]},
    {"name":"Torani","tier":"competitor","pages":["https://www.torani.in/blogs/news"],"feeds":["https://www.torani.in/blogs/news.atom"]},
    {"name":"Lashkaraa","tier":"competitor","pages":["https://www.lashkaraa.com/blogs/lashkaraa/"],"feeds":["https://www.lashkaraa.com/blogs/lashkaraa.atom"]},
    {"name":"Libas","tier":"competitor","pages":["https://www.libas.in/blogs/news"],"feeds":["https://www.libas.in/blogs/news.atom"]},
    {"name":"MissMalini Style","tier":"competitor","pages":["https://www.missmalini.com/category/style"],"feeds":["https://www.missmalini.com/category/style/feed"]},
    {"name":"South India Fashion","tier":"competitor","pages":["https://www.southindiafashion.com"],"feeds":["https://www.southindiafashion.com/feed"]},
    {"name":"Saree.com","tier":"competitor","pages":["https://www.saree.com/blog"],"feeds":["https://www.saree.com/blog/feed"]},
    {"name":"Koskii","tier":"competitor","pages":["https://www.koskii.com/blog"],"feeds":["https://www.koskii.com/blogs/news.atom"]},
    {"name":"Panash India","tier":"competitor","pages":["https://www.panashindia.com/blog"],"feeds":["https://www.panashindia.com/blog/feed"]},
    {"name":"Indian Cloth Store","tier":"competitor","pages":["https://www.indianclothstore.com/blog"],"feeds":["https://www.indianclothstore.com/blog/feed"]},
    {"name":"India Today Fashion","tier":"industry","pages":["https://www.indiatoday.in/lifestyle/fashion"],"feeds":["https://www.indiatoday.in/rss/1206578"]},
    {"name":"Vogue India Fashion","tier":"industry","pages":["https://www.vogue.in/fashion","https://www.vogue.in"],"feeds":["https://www.vogue.in/feed"]},
    {"name":"Elle India Fashion","tier":"industry","pages":["https://www.elle.in/fashion","https://www.elle.in"],"feeds":["https://www.elle.in/feed/"]},
    {"name":"Grazia India Fashion","tier":"industry","pages":["https://www.grazia.co.in/fashion","https://www.grazia.co.in"],"feeds":["https://www.grazia.co.in/feed"]},
    {"name":"Vogue US","tier":"industry","pages":["https://www.vogue.com"],"feeds":["https://www.vogue.com/feed/rss"]},
    {"name":"Business of Fashion","tier":"industry","pages":["https://www.businessoffashion.com"],"feeds":["https://www.businessoffashion.com/rss"]},
    {"name":"Who What Wear","tier":"industry","pages":["https://www.whowhatwear.com"],"feeds":["https://www.whowhatwear.com/rss"]},
    {"name":"Fashionista","tier":"industry","pages":["https://fashionista.com"],"feeds":["https://fashionista.com/.rss/excerpt/"]},
    {"name":"Harper's Bazaar","tier":"industry","pages":["https://www.harpersbazaar.com"],"feeds":["https://www.harpersbazaar.com/rss/all.xml/"]},
    {"name":"Lyst","tier":"industry","pages":["https://www.lyst.com"],"feeds":["https://www.lyst.com/magazine/feed/"]},
    {"name":"Tag-Walk","tier":"industry","pages":["https://www.tag-walk.com"],"feeds":["https://www.tag-walk.com/en/feed"]},
    {"name":"The Blonde Salad","tier":"industry","pages":["https://www.theblondesalad.com"],"feeds":["https://www.theblondesalad.com/feed"]},
    {"name":"The Sartorialist","tier":"industry","pages":["https://www.thesartorialist.com"],"feeds":["https://www.thesartorialist.com/feed"]},
    {"name":"FashionBeans","tier":"industry","pages":["https://www.fashionbeans.com"],"feeds":["https://www.fashionbeans.com/feed"]},
    {"name":"Fashion Gone Rogue","tier":"industry","pages":["https://www.fashiongonerogue.com"],"feeds":["https://www.fashiongonerogue.com/feed"]},
]

# ── Fashion Intelligence ───────────────────────────────────────────────
FASHION_KEYWORDS = [
    "fashion","style","outfit","wear","dress","saree","lehenga","kurta","bridal","wedding",
    "designer","collection","runway","couture","luxury","jewellery","accessory","ethnic",
    "silk","embroidery","handloom","craft","bollywood","celebrity","trend","season","beauty",
    "model","label","brand","launch","show","gown","sari","anarkali","dupatta","festive",
    "occasion","traditional","sustainable","khadi","zari","banarasi","kanjeevaram","menswear"
]

AZA_CATEGORIES = {
    "Bridal & Wedding":["bridal","wedding","bride","lehenga","trousseau","mehendi","engagement","shaadi"],
    "Celebrity Style":["bollywood","celebrity","wore","spotted","red carpet","airport","actor","actress","star"],
    "Designer Spotlight":["designer","collection","label","launch","show","couture","debut","collaboration"],
    "Art & Craft":["craft","handloom","embroidery","weave","artisan","heritage","block print","zari","kalamkari","banarasi","kanjeevaram","sustainable"],
    "Trend Alert":["trend","season","forecast","style guide","what to wear","how to","guide","edit","resort"],
    "Occasion Dressing":["party","festive","diwali","navratri","eid","holi","occasion","gala","awards","reception"],
}


# ── Helpers ─────────────────────────────────────────────────────────────
def clean_text(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text or '')).strip()

def score_fashion(text):
    t = (text or "").lower()
    return sum(1 for kw in FASHION_KEYWORDS if kw in t)

def detect_category(text):
    t = (text or "").lower()
    best, best_score = "Fashion & Style", 0
    for cat, keywords in AZA_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in t)
        if score > best_score:
            best, best_score = cat, score
    return best

def suggest_angle(title):
    t = (title or "").lower()
    if any(w in t for w in ["bridal","bride","wedding","lehenga"]):
        return f"Bridal Edit: {title.split(':')[0].strip()} — A Complete Style Guide"
    if any(w in t for w in ["celebrity","spotted","wore","wearing","airport","red carpet"]):
        return "Get the Look: How to Style This Celebrity Trend the AZA Way"
    if any(w in t for w in ["collection","launch","debut","new season"]):
        return "Designer Spotlight: What This Collection Means for Indian Fashion"
    if any(w in t for w in ["craft","handloom","artisan","heritage","weave","embroidery"]):
        return "The Craft Story: Celebrating the Hands Behind the Fabric"
    if any(w in t for w in ["trend","forecast","season","style guide"]):
        return "Your AZA Style Guide to This Season's Biggest Trend"
    if any(w in t for w in ["festive","diwali","navratri","eid","holi","occasion"]):
        return "Festive Dressing: How to Own This Occasion"
    return f"Fashion Intelligence: {title[:70]}..."

def normalize_url(base, href):
    if not href:
        return ""
    return urljoin(base, href.split("#")[0].strip())

def looks_like_post_url(url, source_host):
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower().rstrip("/")
    if source_host not in host:
        return False
    bad_parts = [
        "/products/","/product/","/collections/","/collection/","/shop/",
        "/category/","/categories/","/tag/","/tags/","/search","/feed",
        "/page/","/cart","/checkout","/account","/wishlist","/lookbook",
        "/wp-content/",".jpg",".jpeg",".png",".webp",".svg",".pdf"
    ]
    if any(part in path for part in bad_parts):
        return False
    if "web-stories" in path:
        return False
    good_parts = ["/blog/","/blogs/","/news/","/magazine/"]
    if any(part in path for part in good_parts):
        segments = [s for s in path.split("/") if s]
        if len(segments) >= 2:
            if "blogs" in segments and len(segments) >= 3:
                return True
            if "blog" in segments and len(segments) >= 2:
                return True
            if ("news" in segments or "magazine" in segments) and len(segments) >= 2:
                return True
    if re.search(r"/20\d{2}/\d{2}/", path):
        return True
    return False

def to_datetime_from_entry(entry):
    if getattr(entry, "published_parsed", None):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    for key in ["published","updated","created"]:
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return None

def to_datetime_from_string(value):
    if not value:
        return None
    try:
        dt = dateparser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def is_recent(dt):
    return dt is not None and dt >= CUTOFF_DATE


# ── Google Sheets Keyword Loader ───────────────────────────────────────
def fetch_keywords_from_sheets():
    """
    Fetch keyword lists from published Google Sheets CSVs.
    Returns (keywords_in, keywords_us) where each is a list of (keyword, keyword_type) tuples.
    Falls back to empty lists if fetch fails.
    """
    keywords_in = []
    keywords_us = []

    # ── Keywords_IN ──
    # Expected columns: (blank), Keyword, Keyword Type, Target URL, Search Volume (IN), Active, ...
    # Header row has "Keyword" in it; data rows follow. Skip rows where Active != TRUE.
    try:
        print("Fetching Keywords_IN from Google Sheets...")
        resp = requests.get(SHEET_KEYWORDS_IN, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)

        # Find header row (contains "Keyword")
        header_idx = None
        kw_col = None
        type_col = None
        active_col = None
        vol_col = None
        for i, row in enumerate(rows):
            row_lower = [str(c).strip().lower() for c in row]
            if "keyword" in row_lower:
                header_idx = i
                for j, cell in enumerate(row_lower):
                    if cell == "keyword":
                        kw_col = j
                    elif cell == "keyword type":
                        type_col = j
                    elif cell == "active":
                        active_col = j
                    elif "search volume" in cell:
                        vol_col = j
                break

        if header_idx is not None and kw_col is not None:
            for row in rows[header_idx + 1:]:
                if len(row) <= kw_col:
                    continue
                keyword = str(row[kw_col]).strip()
                kw_type = str(row[type_col]).strip() if type_col is not None and len(row) > type_col else "Category"
                active = str(row[active_col]).strip().upper() if active_col is not None and len(row) > active_col else "TRUE"
                volume = 0
                if vol_col is not None and len(row) > vol_col:
                    try:
                        volume = int(str(row[vol_col]).replace(",", "").strip())
                    except (ValueError, TypeError):
                        volume = 0

                if keyword and active == "TRUE":
                    keywords_in.append((keyword, kw_type, volume))

            # Sort by volume descending, take top 60
            keywords_in.sort(key=lambda x: -x[2])
            keywords_in = [(k, t) for k, t, v in keywords_in[:60]]
            print(f"  → Loaded {len(keywords_in)} IN keywords (top 60 by volume)")
        else:
            print("  → Could not find header row in Keywords_IN CSV")

    except Exception as e:
        print(f"  → Failed to fetch Keywords_IN: {e}")

    # ── Keywords_US ──
    # Expected columns: (blank), Keyword, Keyword Type, Volume Type, Category, Search Volume (US), Target URL, Date Added, Trend, Active, ...
    try:
        print("Fetching Keywords_US from Google Sheets...")
        resp = requests.get(SHEET_KEYWORDS_US, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)

        header_idx = None
        kw_col = None
        type_col = None
        voltype_col = None
        active_col = None
        vol_col = None
        for i, row in enumerate(rows):
            row_lower = [str(c).strip().lower() for c in row]
            if "keyword" in row_lower:
                header_idx = i
                for j, cell in enumerate(row_lower):
                    if cell == "keyword":
                        kw_col = j
                    elif cell == "keyword type":
                        type_col = j
                    elif cell == "volume type":
                        voltype_col = j
                    elif cell == "active":
                        active_col = j
                    elif "search volume" in cell:
                        vol_col = j
                break

        if header_idx is not None and kw_col is not None:
            for row in rows[header_idx + 1:]:
                if len(row) <= kw_col:
                    continue
                keyword = str(row[kw_col]).strip()
                kw_type = str(row[type_col]).strip() if type_col is not None and len(row) > type_col else "Category"
                vol_type = str(row[voltype_col]).strip() if voltype_col is not None and len(row) > voltype_col else ""
                active = str(row[active_col]).strip().upper() if active_col is not None and len(row) > active_col else "TRUE"
                volume = 0
                if vol_col is not None and len(row) > vol_col:
                    try:
                        volume = int(str(row[vol_col]).replace(",", "").strip())
                    except (ValueError, TypeError):
                        volume = 0

                # Only Head + Torso keywords for pytrends (skip Tail — too many)
                if keyword and active == "TRUE" and vol_type in ("Head", "Torso"):
                    keywords_us.append((keyword, kw_type, volume))

            keywords_us.sort(key=lambda x: -x[2])
            keywords_us = [(k, t) for k, t, v in keywords_us[:60]]
            print(f"  → Loaded {len(keywords_us)} US keywords (top 60 Head+Torso by volume)")
        else:
            print("  → Could not find header row in Keywords_US CSV")

    except Exception as e:
        print(f"  → Failed to fetch Keywords_US: {e}")

    return keywords_in, keywords_us


# ── Feed + HTML Fetchers ───────────────────────────────────────────────
def item_from_entry(entry, src):
    title = clean_text(entry.get("title",""))
    link = entry.get("link","")
    summary = clean_text(entry.get("summary","") or entry.get("description",""))[:320]
    if not title or not link:
        return None
    combined = f"{title} {summary}"
    return {
        "id": hashlib.md5(link.encode()).hexdigest()[:12],
        "title": title,
        "link": link,
        "summary": summary,
        "source": src["name"],
        "tier": src["tier"],
        "is_competitor": src["tier"] == "competitor",
        "aza_category": detect_category(combined),
        "angle": suggest_angle(title),
        "score": score_fashion(combined),
        "published": "",
        "discovered_via": "feed"
    }

def fetch_feed_items(src):
    items = []
    for feed_url in src["feeds"]:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=20)
            if resp.status_code >= 400:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:50]:
                item = item_from_entry(entry, src)
                if not item:
                    continue
                dt = to_datetime_from_entry(entry)
                if not is_recent(dt):
                    continue
                item["published"] = dt.isoformat()
                items.append(item)
        except Exception:
            continue
    return items

def extract_candidates_from_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for selector in ["article a","h1 a","h2 a","h3 a",".post a",".entry-title a",".blog a",".card a",".article a"]:
        for a in soup.select(selector):
            href = normalize_url(base_url, a.get("href"))
            text = clean_text(a.get_text(" ", strip=True))
            if href and text and len(text) >= 12:
                candidates.append((text, href))
    for article in soup.find_all(["article","div","li"], limit=1200):
        a = article.find("a", href=True)
        if not a:
            continue
        href = normalize_url(base_url, a.get("href"))
        title = ""
        h = article.find(["h1","h2","h3","h4"])
        if h:
            title = clean_text(h.get_text(" ", strip=True))
        if not title:
            title = clean_text(a.get_text(" ", strip=True))
        if href and title and len(title) >= 12:
            candidates.append((title, href))
    dedup, seen = [], set()
    for title, href in candidates:
        key = (title.lower(), href)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((title, href))
    return dedup

def fetch_html_items(src):
    items = []
    for page_url in src["pages"]:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=20)
            if resp.status_code >= 400:
                continue
            host = urlparse(page_url).netloc.lower()
            candidates = extract_candidates_from_html(resp.text, page_url)
            for title, link in candidates[:300]:
                if not looks_like_post_url(link, host):
                    continue
                if src["tier"] == "industry" and score_fashion(title) < 1:
                    continue
                items.append({
                    "id": hashlib.md5(link.encode()).hexdigest()[:12],
                    "title": title,
                    "link": link,
                    "summary": "",
                    "source": src["name"],
                    "tier": src["tier"],
                    "is_competitor": src["tier"] == "competitor",
                    "aza_category": detect_category(title),
                    "angle": suggest_angle(title),
                    "score": score_fashion(title),
                    "published": "",
                    "discovered_via": "html"
                })
        except Exception:
            continue
    return items

def merge_items(feed_items, html_items):
    merged = {}
    for item in feed_items + html_items:
        key = item["link"]
        if key not in merged:
            merged[key] = item
        else:
            existing = merged[key]
            if not existing.get("summary") and item.get("summary"):
                existing["summary"] = item["summary"]
            if not existing.get("published") and item.get("published"):
                existing["published"] = item["published"]
            if existing.get("discovered_via") == "html" and item.get("discovered_via") == "feed":
                existing["discovered_via"] = "feed"
    return list(merged.values())

def fetch_source(src):
    feed_items = fetch_feed_items(src)
    html_items = fetch_html_items(src)
    items = merge_items(feed_items, html_items)
    filtered = []
    for item in items:
        dt = to_datetime_from_string(item.get("published"))
        if dt and is_recent(dt):
            filtered.append(item)
    items = filtered
    if src["tier"] == "industry":
        items = [x for x in items if x["score"] > 0 or x["source"] in [
            "Vogue US","Business of Fashion","Vogue India Fashion",
            "Elle India Fashion","Grazia India Fashion","Harper's Bazaar"
        ]]
    items = sorted(items, key=lambda x: x.get("published",""), reverse=True)[:40]
    print(f"{src['name']}: {len(items)} items ({len(feed_items)} feed, {len(html_items)} html)")
    return items


# ── Google Trends RSS ──────────────────────────────────────────────────
def fetch_trends_rss():
    fashion_hits = []
    general_hits = []
    try:
        resp = requests.get(GOOGLE_TRENDS_URL, headers=HEADERS, timeout=15)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:40]:
            title = clean_text(entry.get("title",""))
            summary = clean_text(entry.get("summary","") or entry.get("description",""))
            item = {
                "term": title,
                "summary": summary[:240],
                "angle": suggest_angle(title),
                "aza_category": detect_category(title),
            }
            general_hits.append(item)
            if score_fashion(title) > 0:
                fashion_hits.append(item)
    except Exception:
        pass
    if fashion_hits:
        return fashion_hits[:12]
    return general_hits[:12]


# ── pytrends Keyword Intelligence ──────────────────────────────────────
def fetch_keyword_trends(keywords_in, keywords_us):
    """
    Use pytrends to get related queries (rising + top) for AZA's
    tracked keywords in IN and US markets.
    Keywords are passed in from the Google Sheets loader.
    Falls back gracefully if pytrends is unavailable or rate-limited.
    """
    if not keywords_in and not keywords_us:
        print("No keywords loaded — skipping pytrends")
        return []

    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("pytrends not installed — skipping keyword trends")
        return []

    results = []
    pytrends = TrendReq(hl='en-US', tz=330, timeout=(10, 25), retries=2, backoff_factor=1.0)

    keyword_sets = [
        ("IN", keywords_in),
        ("US", keywords_us),
    ]

    for geo, keywords in keyword_sets:
        if not keywords:
            continue

        # Group into batches of 5 (pytrends limit)
        kw_list = [k for k, _ in keywords]
        batches = [kw_list[i:i+5] for i in range(0, len(kw_list), 5)]

        for batch_idx, batch in enumerate(batches):
            try:
                pytrends.build_payload(batch, cat=0, timeframe='now 7-d', geo=geo)
                related = pytrends.related_queries()

                for kw in batch:
                    kw_type = "Category"
                    for k, t in keywords:
                        if k == kw:
                            kw_type = t
                            break

                    rising_queries = []
                    top_queries = []

                    if kw in related and related[kw]:
                        rising_df = related[kw].get("rising")
                        if rising_df is not None and not rising_df.empty:
                            for _, row in rising_df.head(5).iterrows():
                                q = str(row.get("query",""))
                                val = row.get("value", 0)
                                rising_queries.append({
                                    "query": q,
                                    "value": str(val),
                                    "aza_category": detect_category(q),
                                    "fashion_score": score_fashion(q),
                                })

                        top_df = related[kw].get("top")
                        if top_df is not None and not top_df.empty:
                            for _, row in top_df.head(5).iterrows():
                                q = str(row.get("query",""))
                                val = row.get("value", 0)
                                top_queries.append({
                                    "query": q,
                                    "value": int(val) if val else 0,
                                    "aza_category": detect_category(q),
                                    "fashion_score": score_fashion(q),
                                })

                    if rising_queries or top_queries:
                        results.append({
                            "keyword": kw,
                            "keyword_type": kw_type,
                            "geo": geo,
                            "rising": rising_queries,
                            "top": top_queries,
                            "angle": suggest_angle(kw),
                            "aza_category": detect_category(kw),
                        })

                # Rate limiting
                time.sleep(2)

            except Exception as e:
                print(f"pytrends batch {batch_idx} ({geo}) failed: {e}")
                time.sleep(5)
                continue

    in_count = sum(1 for r in results if r['geo'] == 'IN')
    us_count = sum(1 for r in results if r['geo'] == 'US')
    print(f"Keyword trends: {len(results)} keywords with signals ({in_count} IN, {us_count} US)")
    return results


# ── Main ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 0. Load keywords from Google Sheets
    keywords_in, keywords_us = fetch_keywords_from_sheets()

    # 1. Fetch all website sources
    all_items = []
    for src in SOURCES:
        all_items.extend(fetch_source(src))

    dedup = {}
    for item in all_items:
        if item["link"] not in dedup:
            dedup[item["link"]] = item
    articles = list(dedup.values())
    articles.sort(key=lambda x: (
        0 if x["tier"] == "owned" else 1 if x["tier"] == "competitor" else 2,
        x.get("published","")
    ), reverse=True)
    articles = articles[:800]

    competitor_count = sum(1 for x in articles if x["tier"] == "competitor")
    industry_count = sum(1 for x in articles if x["tier"] == "industry")
    owned_count = sum(1 for x in articles if x["tier"] == "owned")

    # 2. Fetch Google Trends RSS
    trends = fetch_trends_rss()

    # 3. Fetch pytrends keyword intelligence (uses live Sheet data)
    keyword_trends = fetch_keyword_trends(keywords_in, keywords_us)

    # 4. Write feed.json
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owned_count": owned_count,
            "competitor_count": competitor_count,
            "industry_count": industry_count,
            "keywords_loaded": {"IN": len(keywords_in), "US": len(keywords_us)},
            "articles": articles,
            "trends": trends,
            "keyword_trends": keyword_trends,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nfeed.json written: {len(articles)} articles | owned={owned_count} competitor={competitor_count} industry={industry_count}")
    print(f"Keywords loaded: {len(keywords_in)} IN, {len(keywords_us)} US (from Google Sheets)")
    print(f"Trends: {len(trends)} RSS signals | {len(keyword_trends)} keyword trend signals")
