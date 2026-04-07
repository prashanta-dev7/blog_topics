#!/usr/bin/env python3
"""
AZA Fashions — Daily Feed Fetcher
Writes feed.json to repo root. Run by GitHub Actions.
"""
import json, feedparser, requests, datetime, hashlib, re, sys

# ── SOURCE TIERS ───────────────────────────────────────────────────────────
# Tier 1: Direct competitors — flagged prominently in the UI
COMPETITORS = [
    {"name": "Pernia's Pop-Up Shop",  "url": "https://www.perniaspopupshop.com/blog/feed"},
    {"name": "Utsav Fashion",         "url": "https://www.utsavfashion.com/blog/feed"},
    {"name": "House of Indya",        "url": "https://www.houseofindya.com/blogs/news.atom"},
    {"name": "Libas",                 "url": "https://www.libas.in/blogs/news.atom"},
    {"name": "BIBA",                  "url": "https://www.biba.in/blogs/fashion.atom"},
    {"name": "Manyavar",              "url": "https://www.manyavar.com/en-in/blog/feed"},
    {"name": "Torani",                "url": "https://www.torani.in/blogs/news.atom"},
    {"name": "Anita Dongre",          "url": "https://www.anitadongre.com/blogs/news.atom"},
    {"name": "FabIndia",              "url": "https://www.fabindia.com/blogs/news.atom"},
    {"name": "MissMalini Style",      "url": "https://www.missmalini.com/category/style/feed"},
    {"name": "South India Fashion",   "url": "https://www.southindiafashion.com/feed"},
    {"name": "Saree.com",             "url": "https://www.saree.com/blog/feed"},
    {"name": "Koskii",                "url": "https://www.koskii.com/blogs/news.atom"},
    {"name": "Panash India",          "url": "https://www.panashindia.com/blog/feed"},
    {"name": "Kalki Fashion",         "url": "https://blog.kalkifashion.com/feed"},
    {"name": "Lashkaraa",             "url": "https://www.lashkaraa.com/blogs/lashkaraa.atom"},
]

# Tier 2: Industry & inspiration sources
INDUSTRY = [
    {"name": "Vogue India",           "url": "https://www.vogue.in/feed"},
    {"name": "Vogue US",              "url": "https://www.vogue.com/feed/rss"},
    {"name": "Elle India",            "url": "https://www.elle.in/feed/"},
    {"name": "Grazia India",          "url": "https://www.grazia.co.in/feed"},
    {"name": "Harper's Bazaar",       "url": "https://www.harpersbazaar.com/rss/all.xml/"},
    {"name": "Business of Fashion",   "url": "https://www.businessoffashion.com/rss"},
    {"name": "Who What Wear",         "url": "https://www.whowhatwear.com/rss"},
    {"name": "Fashionista",           "url": "https://fashionista.com/.rss/excerpt/"},
    {"name": "WWD",                   "url": "https://wwd.com/feed/"},
    {"name": "India Today Fashion",   "url": "https://www.indiatoday.in/rss/1206578"},
    {"name": "AZA Magazine",          "url": "https://magazine.azafashions.com/feed"},
    {"name": "The Blonde Salad",      "url": "https://www.theblondesalad.com/feed"},
    {"name": "Fashion Gone Rogue",    "url": "https://www.fashiongonerogue.com/feed"},
    {"name": "Fashion Beans",         "url": "https://www.fashionbeans.com/feed"},
]

GOOGLE_TRENDS_URL = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=IN"

FASHION_KEYWORDS = [
    "fashion","style","outfit","wear","dress","saree","lehenga","kurta","bridal",
    "wedding","designer","collection","runway","couture","luxury","jewellery",
    "accessory","accessories","ethnic","silk","embroidery","handloom","craft",
    "bollywood","celebrity","look","trend","season","makeup","beauty","model",
    "label","brand","launch","show","week","gown","sari","anarkali","dupatta",
    "manish","sabyasachi","tarun","rohit","ritu","falguni","shane","masaba",
    "anamika","nachiket","gaurav","deepika","priyanka","alia","kareena","sonam",
    "kiara","katrina","ranveer","festive","diwali","navratri","eid","holi",
    "occasion","traditional","sustainable","khadi","zari","banarasi","kanjeevaram",
    "block print","mirror work","gota","phulkari","kantha","ikkat",
]

AZA_CATEGORIES = {
    "Bridal & Wedding":   ["bridal","wedding","bride","lehenga","trousseau","mehendi","engagement","shaadi"],
    "Celebrity Style":    ["bollywood","celebrity","wore","spotted","red carpet","airport","actor","actress","star"],
    "Designer Spotlight": ["designer","collection","label","launch","show","couture","debut","collaboration"],
    "Art & Craft":        ["craft","handloom","embroidery","weave","artisan","heritage","block print","zari",
                           "kalamkari","kantha","banarasi","kanjeevaram","sustainable","phulkari","ikkat"],
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

def fetch_sources(sources, is_competitor=False):
    articles, seen = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (AZA Blog Agent/1.0)"}
    for src in sources:
        try:
            resp = requests.get(src["url"], headers=headers, timeout=12)
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries[:10]:
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "")
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", ""))[:300]
                combined = title + " " + summary
                # Competitors: keep all posts regardless of fashion score
                # Industry: filter for fashion relevance
                if not is_competitor and score_fashion(combined) < 1:
                    continue
                if not title:
                    continue
                uid = hashlib.md5(link.encode()).hexdigest()[:8]
                if uid in seen:
                    continue
                seen.add(uid)
                articles.append({
                    "id":           uid,
                    "title":        title,
                    "link":         link,
                    "summary":      summary,
                    "source":       src["name"],
                    "is_competitor": is_competitor,
                    "aza_category": detect_category(combined),
                    "angle":        suggest_angle(title),
                    "score":        score_fashion(combined),
                    "published":    entry.get("published", ""),
                })
                count += 1
            print(f"  {src['name']}: {count} articles")
        except Exception as e:
            print(f"  ERROR {src['name']}: {e}")
    return articles

def fetch_trends():
    trends = []
    try:
        resp = requests.get(GOOGLE_TRENDS_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        feed = feedparser.parse(resp.content)
        for entry in feed.entries[:30]:
            title = entry.get("title", "").strip()
            if score_fashion(title) > 0:
                trends.append({
                    "term":         title,
                    "angle":        suggest_angle(title),
                    "aza_category": detect_category(title),
                })
    except Exception as e:
        print(f"  ERROR Trends: {e}")
    return trends[:10]

if __name__ == "__main__":
    competitor_only = "--competitors-only" in sys.argv

    print("── Fetching competitor blogs…")
    competitor_articles = fetch_sources(COMPETITORS, is_competitor=True)

    if competitor_only:
        # Load existing feed.json, replace competitor articles only
        try:
            with open("feed.json") as f:
                existing = json.load(f)
            industry_articles = [a for a in existing.get("articles", []) if not a.get("is_competitor")]
            trends = existing.get("trends", [])
            print(f"  Keeping {len(industry_articles)} existing industry articles")
        except:
            industry_articles = []
            trends = []
    else:
        print("── Fetching industry sources…")
        industry_articles = fetch_sources(INDUSTRY, is_competitor=False)
        print("── Fetching Google Trends India…")
        trends = fetch_trends()

    # Merge: competitors first, then industry, deduplicated
    seen_ids = set()
    all_articles = []
    for a in competitor_articles + industry_articles:
        if a["id"] not in seen_ids:
            seen_ids.add(a["id"])
            all_articles.append(a)

    # Sort: competitors first, then by score
    all_articles.sort(key=lambda x: (-int(x.get("is_competitor", False)), -x.get("score", 0)))

    with open("feed.json", "w") as f:
        json.dump({
            "generated_at":      datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "competitor_count":  len(competitor_articles),
            "industry_count":    len(industry_articles),
            "articles":          all_articles,
            "trends":            trends,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n✓ feed.json written — {len(competitor_articles)} competitor + {len(industry_articles)} industry articles, {len(trends)} trends")
