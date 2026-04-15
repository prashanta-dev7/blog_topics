#!/usr/bin/env python3
"""
AZA Blog Agent — Content Intelligence Feed Generator (v5.0)
Fetches from 36 editorial/competitor sources, Google Trends RSS,
and pytrends keyword intelligence for IN + US markets.
Output: feed.json consumed by the Content Intelligence Desk (index.html)
"""

import json
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
    "User-Agent": "Mozilla/5.0 (AZA Blog Agent/5.0; +https://www.azafashions.com)"
}
MAX_AGE_DAYS = 60
CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
GOOGLE_TRENDS_URL = "https://trends.google.com/trending/rss?geo=IN"

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

# ── Keyword Trends Config ──────────────────────────────────────────────
# Top tracked keywords from AZA Keyword Tracker (by search volume)
# These are used for pytrends related-queries lookups to surface
# emerging search signals the content team can act on.

KEYWORDS_IN = [
    ("saree for women","Category"),("sarees","Category"),("lehenga","Category"),
    ("saree","Category"),("lehengas","Category"),("Lashkaraa","Designer"),
    ("indian clothes","Category"),("indian clothing","Category"),
    ("sarees for women","Category"),("Sabyasachi","Designer"),
    ("indian dresses","Category"),("indian dress","Category"),
    ("salwar kameez","Category"),("sherwani","Category"),
    ("indian outfits for women","Category"),("indian dresses for women","Category"),
    ("kurta for men","Category"),("sharara","Category"),
    ("indian sarees","Category"),("indian saree","Category"),
    ("sherwani for men","Category"),("lehenga choli","Category"),
    ("mens indian clothing","Category"),("indo western for women","Category"),
    ("Mahima Mahajan","Designer"),("lehenga dress","Category"),
    ("bridal lehenga","Category"),("Masaba","Designer"),
    ("indian outfits","Category"),("anarkali dress","Category"),
    ("lehenga for wedding","Category"),("wedding sarees","Category"),
    ("ready to wear saree","Category"),("sharara suit","Category"),
    ("sharara suits","Category"),("mens kurta","Category"),
    ("lehenga for women","Category"),("lehengas for women","Category"),
    ("kurta for women","Category"),("saree blouse","Category"),
    ("indian ethnic wear","Category"),("indo western dress","Category"),
    ("indian lehenga","Category"),("black kurta","Category"),
    ("pre stitched saree","Category"),("pre draped saree","Category"),
    ("wedding lehenga","Category"),("sangeet lehenga","Category"),
    ("Paulmi And Harsh","Designer"),("Basanti Kapde Aur Koffee","Designer"),
]

KEYWORDS_US = [
    ("anthrilo","Designer"),("gowns","Category"),("sarees","Category"),
    ("designer shirts","Category"),("palazzo pants","Category"),
    ("lehenga","Category"),("lehengas","Category"),("kaftans","Category"),
    ("lashkaraa","Designer"),("kurtas","Category"),
    ("aza","Category"),("indian dresses for wedding","Category"),
    ("designer dresses","Category"),("gowns for women","Category"),
    ("aza fashions","Category"),("anarkali","Category"),
    ("saree dress","Category"),("sarees for women","Category"),
    ("jhumkas","Category"),("kaftans for women","Category"),
    ("blouse designs","Category"),("indian dresses online","Category"),
    ("indian dresses for women","Category"),("anarkali dress","Category"),
    ("ready to wear saree","Category"),("designer dresses for women","Category"),
    ("silk sarees","Category"),("saree blouses","Category"),
    ("tarun tahiliani","Designer"),("masaba","Designer"),
    ("sherwani mens wear","Category"),("lehenga for women","Category"),
    ("mens kurta","Category"),("sharara suit","Category"),
    ("bridal lehengas","Category"),("sherwani men","Category"),
    ("kurta for women","Category"),("jhumka earrings","Category"),
    ("pre draped saree","Category"),("black saree","Category"),
    ("mahima mahajan","Designer"),("saree blouse designs","Category"),
    ("indian lehenga","Category"),("anarkali suit","Category"),
    ("house of chikankari","Designer"),("pre stitched saree","Category"),
    ("indian kurta for men","Category"),("black kurta","Category"),
    ("designer jackets for women","Category"),("red saree","Category"),
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


# ── Feed + HTML Fetchers (unchanged from v4) ───────────────────────────
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


# ── Google Trends RSS (unchanged) ──────────────────────────────────────
def fetch_trends_rss():
    """Pull trending-now items from Google Trends RSS for India."""
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


# ── NEW: pytrends Keyword Intelligence ─────────────────────────────────
def fetch_keyword_trends():
    """
    Use pytrends to get related queries (rising + top) for AZA's
    tracked keywords in IN and US markets.
    Returns a list of keyword trend objects for the frontend.
    Falls back gracefully if pytrends is unavailable or rate-limited.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        print("pytrends not installed — skipping keyword trends")
        return []

    results = []
    pytrends = TrendReq(hl='en-US', tz=330, timeout=(10, 25), retries=2, backoff_factor=1.0)

    keyword_sets = [
        ("IN", KEYWORDS_IN),
        ("US", KEYWORDS_US),
    ]

    for geo, keywords in keyword_sets:
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

                # Rate limiting — be gentle with Google
                time.sleep(2)

            except Exception as e:
                print(f"pytrends batch {batch_idx} ({geo}) failed: {e}")
                time.sleep(5)
                continue

    print(f"Keyword trends: {len(results)} keywords with signals ({sum(1 for r in results if r['geo']=='IN')} IN, {sum(1 for r in results if r['geo']=='US')} US)")
    return results


# ── Main ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
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

    # 2. Fetch Google Trends RSS (quick)
    trends = fetch_trends_rss()

    # 3. Fetch pytrends keyword intelligence (slow, rate-limited)
    keyword_trends = fetch_keyword_trends()

    # 4. Write feed.json
    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "owned_count": owned_count,
            "competitor_count": competitor_count,
            "industry_count": industry_count,
            "articles": articles,
            "trends": trends,
            "keyword_trends": keyword_trends,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nfeed.json written: {len(articles)} articles | owned={owned_count} competitor={competitor_count} industry={industry_count}")
    print(f"Trends: {len(trends)} RSS signals | {len(keyword_trends)} keyword trend signals")
