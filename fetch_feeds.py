#!/usr/bin/env python3
import json, feedparser, requests, datetime, hashlib, re

SOURCES = [
    {"name": "Vogue India",         "url": "https://www.vogue.in/feed"},
    {"name": "Vogue US",            "url": "https://www.vogue.com/feed/rss"},
    {"name": "Harper's Bazaar",     "url": "https://www.harpersbazaar.com/rss/all.xml/"},
    {"name": "Business of Fashion", "url": "https://www.businessoffashion.com/rss"},
    {"name": "Net-a-Porter",        "url": "https://www.net-a-porter.com/en-in/porter/rss"},
    {"name": "Elle India",          "url": "https://www.elle.in/feed/"},
    {"name": "Femina",              "url": "https://www.femina.in/feed"},
    {"name": "WWD",                 "url": "https://wwd.com/feed/"},
    {"name": "Grazia India",        "url": "https://www.graziaindia.com/feed"},
    {"name": "Pinkvilla",           "url": "https://www.pinkvilla.com/rss.xml"},
]

GOOGLE_TRENDS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=IN"

FASHION_KEYWORDS = [
    "fashion","style","outfit","wear","dress","saree","lehenga","kurta","bridal",
    "wedding","designer","collection","runway","couture","luxury","jewellery",
    "accessory","ethnic","silk","embroidery","handloom","craft","bollywood",
    "celebrity","look","trend","season","beauty","model","label","brand","launch",
    "show","gown","sari","anarkali","dupatta","manish","sabyasachi","tarun","rohit",
    "ritu","falguni","masaba","anamika","nachiket","gaurav","deepika","priyanka",
    "alia","kareena","sonam","kiara","katrina","festive","diwali","navratri","eid",
    "holi","occasion","traditional","sustainable","khadi","zari","banarasi","kanjeevaram",
]

AZA_CATEGORIES = {
    "Bridal & Wedding":   ["bridal","wedding","bride","lehenga","trousseau","mehendi","engagement","shaadi"],
    "Celebrity Style":    ["bollywood","celebrity","wore","spotted","red carpet","airport","actor","actress","star"],
    "Designer Spotlight": ["designer","collection","label","launch","show","couture","debut","collaboration"],
    "Art & Craft":        ["craft","handloom","embroidery","weave","artisan","heritage","block print","zari","kalamkari","banarasi","kanjeevaram","sustainable"],
    "Trend Alert":        ["trend","season","forecast","style guide","what to wear","how to","guide","edit","resort"],
    "Occasion Dressing":  ["party","festive","diwali","navratri","eid","holi","occasion","gala","awards","reception"],
}

def score_fashion(text):
    t = text.lower()
    return sum(1 for kw in FASHION_KEYWORDS if kw in t)

def detect_category(text):
    t = text.lower()
    best, best_score = "Fashion & Style", 0
    for cat, keywords in AZA_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in t)
        if score > best_score:
            best, best_score = cat, score
    return best

def suggest_angle(title):
    t = title.lower()
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
    if any(w in t for w in ["sustainable","handmade","ethical","khadi"]):
        return "Conscious Fashion: Why This Matters for Your Wardrobe"
    return f"Fashion Intelligence: {title[:70]}..."

def fetch_articles():
    articles, seen = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (AZA Blog Agent/1.0)"}
    for src in SOURCES:
        try:
            resp = requests.get(src["url"], headers=headers, timeout=10)
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:8]:
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "")
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", ""))[:300]
                combined = title + " " + summary
                if score_fashion(combined) < 1 or not title:
                    continue
                uid = hashlib.md5(link.encode()).hexdigest()[:8]
                if uid in seen: continue
                seen.add(uid)
                articles.append({
                    "id": uid, "title": title, "link": link,
                    "summary": summary, "source": src["name"],
                    "aza_category": detect_category(combined),
                    "angle": suggest_angle(title),
                    "score": score_fashion(combined),
                    "published": entry.get("published", ""),
                })
        except Exception as e:
            print(f"Error {src['name']}: {e}")
    return sorted(articles, key=lambda x: -x["score"])

def fetch_trends():
    trends = []
    try:
        resp = requests.get(GOOGLE_TRENDS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:30]:
            title = entry.get("title", "").strip()
            if score_fashion(title) > 0:
                trends.append({
                    "term": title,
                    "angle": suggest_angle(title),
                    "aza_category": detect_category(title),
                })
    except Exception as e:
        print(f"Trends error: {e}")
    return trends[:10]

if __name__ == "__main__":
    articles = fetch_articles()
    trends = fetch_trends()
    print(f"{len(articles)} articles, {len(trends)} trends")
    with open("feed.json", "w") as f:
        json.dump({
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "articles": articles,
            "trends": trends,
        }, f, indent=2, ensure_ascii=False)
    print("feed.json written")
