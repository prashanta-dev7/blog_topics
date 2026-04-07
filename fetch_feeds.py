#!/usr/bin/env python3
import json
import feedparser
import requests
import datetime
import hashlib
import re
import sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (AZA Blog Agent/2.0; +https://www.azafashions.com)"
}

SOURCES = [
    {"name":"AZA Blog","page_url":"https://www.azafashions.com/blog/","feed_url":"https://www.azafashions.com/blog/feed","tier":"owned"},
    {"name":"AZA Magazine","page_url":"https://magazine.azafashions.com/","feed_url":"https://magazine.azafashions.com/feed","tier":"owned"},

    {"name":"Kalki Fashion Blog","page_url":"https://blog.kalkifashion.com/","feed_url":"https://blog.kalkifashion.com/feed/","tier":"competitor"},
    {"name":"Pernia's Pop-Up Shop","page_url":"https://www.perniaspopupshop.com/blog/","feed_url":"https://www.perniaspopupshop.com/blog/feed","tier":"competitor"},
    {"name":"Utsav Fashion","page_url":"https://www.utsavfashion.com/blog/","feed_url":"https://www.utsavfashion.com/blog/feed","tier":"competitor"},
    {"name":"Kalki Fashion Main","page_url":"https://www.kalkifashion.com/in/blog/","feed_url":"https://www.kalkifashion.com/in/blog/rss.xml","tier":"competitor"},
    {"name":"FabIndia","page_url":"https://www.fabindia.com/blogs/news","feed_url":"https://www.fabindia.com/blogs/news.atom","tier":"competitor"},
    {"name":"House of Indya","page_url":"https://www.houseofindya.com/blog","feed_url":"https://www.houseofindya.com/blogs/news.atom","tier":"competitor"},
    {"name":"Manyavar","page_url":"https://www.manyavar.com/en-in/blog","feed_url":"https://www.manyavar.com/en-in/blog/feed","tier":"competitor"},
    {"name":"BIBA","page_url":"https://www.biba.in/blogs/fashion","feed_url":"https://www.biba.in/blogs/fashion.atom","tier":"competitor"},
    {"name":"Anita Dongre","page_url":"https://www.anitadongre.com/blogs/news","feed_url":"https://www.anitadongre.com/blogs/news.atom","tier":"competitor"},
    {"name":"Sabyasachi","page_url":"https://www.sabyasachi.com/blog","feed_url":"https://www.sabyasachi.com/blog/rss.xml","tier":"competitor"},
    {"name":"Torani","page_url":"https://www.torani.in/blogs/news","feed_url":"https://www.torani.in/blogs/news.atom","tier":"competitor"},
    {"name":"Lashkaraa","page_url":"https://www.lashkaraa.com/blogs/lashkaraa/","feed_url":"https://www.lashkaraa.com/blogs/lashkaraa.atom","tier":"competitor"},
    {"name":"Libas","page_url":"https://www.libas.in/blogs/news","feed_url":"https://www.libas.in/blogs/news.atom","tier":"competitor"},
    {"name":"MissMalini Style","page_url":"https://www.missmalini.com/category/style","feed_url":"https://www.missmalini.com/category/style/feed","tier":"competitor"},
    {"name":"South India Fashion","page_url":"https://www.southindiafashion.com","feed_url":"https://www.southindiafashion.com/feed","tier":"competitor"},
    {"name":"Saree.com","page_url":"https://www.saree.com/blog","feed_url":"https://www.saree.com/blog/feed","tier":"competitor"},
    {"name":"Koskii","page_url":"https://www.koskii.com/blog","feed_url":"https://www.koskii.com/blogs/news.atom","tier":"competitor"},
    {"name":"Panash India","page_url":"https://www.panashindia.com/blog","feed_url":"https://www.panashindia.com/blog/feed","tier":"competitor"},
    {"name":"Indian Cloth Store","page_url":"https://www.indianclothstore.com/blog","feed_url":"https://www.indianclothstore.com/blog/feed","tier":"competitor"},

    {"name":"India Today Fashion","page_url":"https://www.indiatoday.in/lifestyle/fashion","feed_url":"https://www.indiatoday.in/rss/1206578","tier":"industry"},
    {"name":"Vogue India Fashion","page_url":"https://www.vogue.in/fashion","feed_url":"https://www.vogue.in/feed","tier":"industry"},
    {"name":"Elle India Fashion","page_url":"https://www.elle.in/fashion","feed_url":"https://www.elle.in/feed/","tier":"industry"},
    {"name":"Grazia India Fashion","page_url":"https://www.grazia.co.in/fashion","feed_url":"https://www.grazia.co.in/feed","tier":"industry"},
    {"name":"Vogue US","page_url":"https://www.vogue.com","feed_url":"https://www.vogue.com/feed/rss","tier":"industry"},
    {"name":"Business of Fashion","page_url":"https://www.businessoffashion.com","feed_url":"https://www.businessoffashion.com/rss","tier":"industry"},
    {"name":"Who What Wear","page_url":"https://www.whowhatwear.com","feed_url":"https://www.whowhatwear.com/rss","tier":"industry"},
    {"name":"Fashionista","page_url":"https://fashionista.com","feed_url":"https://fashionista.com/.rss/excerpt/","tier":"industry"},
    {"name":"Harper's Bazaar","page_url":"https://www.harpersbazaar.com","feed_url":"https://www.harpersbazaar.com/rss/all.xml/","tier":"industry"},
    {"name":"Elle India","page_url":"https://www.elle.in","feed_url":"https://www.elle.in/feed/","tier":"industry"},
    {"name":"Grazia India","page_url":"https://www.grazia.co.in","feed_url":"https://www.grazia.co.in/feed","tier":"industry"},
    {"name":"Lyst","page_url":"https://www.lyst.com","feed_url":"https://www.lyst.com/magazine/feed/","tier":"industry"},
    {"name":"Tag-Walk","page_url":"https://www.tag-walk.com","feed_url":"https://www.tag-walk.com/en/feed","tier":"industry"},
    {"name":"The Blonde Salad","page_url":"https://www.theblondesalad.com","feed_url":"https://www.theblondesalad.com/feed","tier":"industry"},
    {"name":"The Sartorialist","page_url":"https://www.thesartorialist.com","feed_url":"https://www.thesartorialist.com/feed","tier":"industry"},
    {"name":"FashionBeans","page_url":"https://www.fashionbeans.com","feed_url":"https://www.fashionbeans.com/feed","tier":"industry"},
    {"name":"Fashion Gone Rogue","page_url":"https://www.fashiongonerogue.com","feed_url":"https://www.fashiongonerogue.com/feed","tier":"industry"},
]

GOOGLE_TRENDS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=IN"

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
    path = parsed.path.lower()
    if source_host not in host:
        return False
    bad = ["/tag/", "/category/", "/author/", "/page/", "/search", "/feed", ".jpg", ".png", ".webp", ".svg", ".pdf"]
    if any(x in path for x in bad):
        return False
    return path.count("/") >= 2

def parse_date(entry):
    for key in ["published", "updated", "created"]:
        val = entry.get(key)
        if val:
            return val
    return ""

def item_from_entry(entry, src, tier):
    title = clean_text(entry.get("title", ""))
    link = entry.get("link", "")
    summary = clean_text(entry.get("summary", "") or entry.get("description", ""))[:320]
    if not title or not link:
        return None
    combined = f"{title} {summary}"
    return {
        "id": hashlib.md5(link.encode()).hexdigest()[:12],
        "title": title,
        "link": link,
        "summary": summary,
        "source": src["name"],
        "tier": tier,
        "is_competitor": tier == "competitor",
        "aza_category": detect_category(combined),
        "angle": suggest_angle(title),
        "score": score_fashion(combined),
        "published": parse_date(entry),
        "discovered_via": "feed"
    }

def fetch_feed_items(src):
    items = []
    try:
        resp = requests.get(src["feed_url"], headers=HEADERS, timeout=18)
        if resp.status_code >= 400:
            return items
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:15]:
            item = item_from_entry(entry, src, src["tier"])
            if item:
                items.append(item)
    except Exception:
        pass
    return items

def extract_candidates_from_html(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    for a in soup.find_all("a", href=True):
        href = normalize_url(base_url, a.get("href"))
        text = clean_text(a.get_text(" ", strip=True))
        if not href or not text:
            continue
        if len(text) < 20:
            continue
        candidates.append((text, href))

    for article in soup.find_all(["article", "div", "li"], limit=300):
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
        if not href or not title or len(title) < 20:
            continue
        candidates.append((title, href))

    dedup = []
    seen = set()
    for title, href in candidates:
        key = (title.lower(), href)
        if key in seen:
            continue
        seen.add(key)
        dedup.append((title, href))
    return dedup

def fetch_html_items(src):
    items = []
    try:
        resp = requests.get(src["page_url"], headers=HEADERS, timeout=18)
        if resp.status_code >= 400:
            return items
        host = urlparse(src["page_url"]).netloc.lower()
        candidates = extract_candidates_from_html(resp.text, src["page_url"])
        for title, link in candidates[:80]:
            if not looks_like_post_url(link, host):
                continue
            combined = title
            if src["tier"] == "industry" and score_fashion(combined) < 1:
                continue
            items.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:12],
                "title": title,
                "link": link,
                "summary": "",
                "source": src["name"],
                "tier": src["tier"],
                "is_competitor": src["tier"] == "competitor",
                "aza_category": detect_category(combined),
                "angle": suggest_angle(title),
                "score": score_fashion(combined),
                "published": "",
                "discovered_via": "html"
            })
    except Exception:
        pass
    return items[:12]

def merge_items(feed_items, html_items):
    merged = {}
    for item in feed_items + html_items:
        key = item["link"]
        if key not in merged:
            merged[key] = item
        else:
            existing = merged[key]
            if existing.get("summary","") == "" and item.get("summary",""):
                existing["summary"] = item["summary"]
            if existing.get("published","") == "" and item.get("published",""):
                existing["published"] = item["published"]
            if existing.get("discovered_via") == "html" and item.get("discovered_via") == "feed":
                existing["discovered_via"] = "feed"
    return list(merged.values())

def fetch_source(src):
    feed_items = fetch_feed_items(src)
    html_items = fetch_html_items(src)
    items = merge_items(feed_items, html_items)

    if src["tier"] == "industry":
        items = [x for x in items if x["score"] > 0 or x["source"] in ["Vogue US","Business of Fashion","Vogue India Fashion","Elle India Fashion","Grazia India Fashion"]]

    items = items[:12]
    print(f"{src['name']}: {len(items)} items ({len(feed_items)} feed, {len(html_items)} html)")
    return items

def fetch_trends():
    trends = []
    try:
        resp = requests.get(GOOGLE_TRENDS_URL, headers=HEADERS, timeout=15)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:30]:
            title = clean_text(entry.get("title", ""))
            if score_fashion(title) > 0:
                trends.append({
                    "term": title,
                    "angle": suggest_angle(title),
                    "aza_category": detect_category(title),
                })
    except Exception:
        pass
    return trends[:10]

if __name__ == "__main__":
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
        -x.get("score", 0),
        x["source"].lower()
    ))

    competitor_count = sum(1 for x in articles if x["tier"] == "competitor")
    industry_count = sum(1 for x in articles if x["tier"] == "industry")
    owned_count = sum(1 for x in articles if x["tier"] == "owned")

    trends = fetch_trends()

    with open("feed.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "owned_count": owned_count,
            "competitor_count": competitor_count,
            "industry_count": industry_count,
            "articles": articles,
            "trends": trends
        }, f, indent=2, ensure_ascii=False)

    print(f"feed.json written: {len(articles)} total | owned={owned_count} competitor={competitor_count} industry={industry_count}")
