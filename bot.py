import asyncio
import httpx
import feedparser
import yfinance as yf
from datetime import datetime
from pytz import timezone
from rapidfuzz import fuzz
import threading
import re
from flask import Flask

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = timezone("Asia/Kolkata")

SENT_NEWS = []
LAST_BRIEFING_DATE = None
SENT_NEWS_FILE = "sent_news.txt"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ India Market Bot Running!", 200

@app.route('/health')
def health():
    return "OK", 200

WATCHLIST = [
    "rvnl", "suzlon", "vodafone idea", "yes bank", "ireda", "iex",
    "bel", "itc", "coal india", "vedanta", "canara bank",
    "bank of baroda", "pnb", "wipro", "tata tech", "tatatech",
    "ola electric", "inox wind", "mrpl", "jublfood", "jubilant food",
    "thangamayil", "ather energy", "kalyan jewellers", "kalyankjil",
    "niva bupa", "redington", "hyundai india", "diamond cable",
    "geojit", "goldbees", "silverbees", "lg india", "groww",
    "lenskart", "samman", "embassy reit", "lemon tree", "eternal",
    "hfcl", "irfc", "diacabs", "inoxwind",
]

# ONLY accept these types of news
GOOD_KEYWORDS = [
    # GIFT Nifty & market opening
    "gift nifty", "sgx nifty", "gift nifty falls", "gift nifty rises",
    "gift nifty signals", "nifty to open", "market to open",
    "signals weak start", "signals strong start", "gap up", "gap down",
    # Results with actual numbers
    "net profit", "pat rises", "pat falls", "pat up", "pat down",
    "revenue rises", "revenue falls", "revenue up", "revenue down",
    "ebitda rises", "ebitda falls", "quarterly result", "q1 result",
    "q2 result", "q3 result", "q4 result", "annual result",
    # Corporate actions with values
    "dividend of rs", "dividend declared", "record date",
    "bonus shares", "stock split", "buyback of rs", "buyback worth",
    "order worth rs", "order of rs", "bags rs", "wins rs",
    "order from", "bags order", "wins order", "contract awarded",
    "mou signed", "mou with", "agreement signed",
    "capacity of", "commercial operations", "cod declared",
    "qip of rs", "block deal worth", "bulk deal worth",
    "promoter buys", "promoter sells", "stake acquired",
    "merger approved", "acquisition of", "takeover bid",
    "rating upgraded to", "rating downgraded to",
    # Market moving news — factual only
    "nifty falls", "nifty rises", "nifty gains", "nifty drops",
    "sensex falls", "sensex rises", "sensex gains", "sensex drops",
    "bank nifty", "midcap falls", "midcap rises",
    "fii buys", "fii sells", "fii inflow", "fii outflow",
    "dii buys", "dii inflow",
    "rbi cuts repo", "rbi hikes repo", "rbi keeps repo",
    "rbi policy", "rbi governor",
    "rupee falls", "rupee rises", "rupee hits", "rupee at",
    "crude oil rises", "crude oil falls", "crude oil at",
    "brent crude", "opec cuts", "opec raises",
    "gold rises", "gold falls", "gold at", "mcx gold",
    "silver rises", "silver falls", "silver at",
    "us fed", "fed cuts", "fed hikes", "federal reserve",
    "dow falls", "dow rises", "dow jones",
    "nasdaq falls", "nasdaq rises",
    "iran strikes", "iran war", "iran peace",
    "us iran", "russia ukraine", "west asia",
    "trump imposes", "trump tariff", "trump announces",
    "sebi bans", "sebi penalises", "sebi fines", "sebi orders",
    "india gdp", "cpi inflation", "wpi inflation",
    "ipo listing", "listing gains", "listing loss",
    "white house says", "white house announces",
    "govt announces", "government approves", "ministry approves",
    "npcil", "nuclear energy", "defence order", "army order",
    "us court orders", "court orders", "supreme court",
]

# STRICT block — all recommendation/opinion/analysis
BLOCKED_STRICT = [
    # Recommendations
    "should you", "would you invest", "is it time",
    "buy or sell", "buy or avoid", "time to buy", "time to sell",
    "should i buy", "should i sell",
    # Analysis/opinion
    "here's why", "why nifty", "why sensex", "why markets",
    "why this stock", "why tcs", "why infosys",
    "will the surge", "will the rally", "is the rally",
    "can nifty", "can sensex", "what next for",
    "outlook for", "preview:", "review:",
    "amid ai", "job loss fears", "4-year high amid",
    # Interviews
    "opens up on", "in conversation", "exclusive interview",
    "says he is", "says she is", "succession plan",
    "10x profit goal", "39-year partnership",
    "interview:", ": interview",
    # Recommendations
    "top stocks", "best stocks", "stocks to buy",
    "multibagger", "expert says buy", "analyst says buy",
    "brokerage initiates", "brokerage maintains",
    "technical view", "chart pattern", "moving average",
    "support at", "resistance at", "target of rs",
    "stop loss at",
    # Generic junk
    "sip returns", "mutual fund nav", "how to invest",
    "beginners guide", "city-wise rates", "check rates",
    "ipo gmp", "grey market premium",
    "intraday strategy", "weekly outlook", "monthly outlook",
    "5 stocks", "10 stocks", "top 5", "top 10",
    "check details", "find out more", "what's the last date",
    "cautiously optimistic", "earnings revival",
    "q1 surprise sends", "will the surge last",
    "what's buzzing", "what is buzzing",
    "pile up in inventory",  # interview
    "seeing pile up",  # interview
]

BLOCKED_NEWS = [
    "bitcoin", "ethereum", "crypto", "cryptocurrency",
    "nft", "defi", "binance",
    "cricket match", "ipl match",
    "bollywood movie", "hollywood",
    "weather forecast", "recipe",
    "horoscope", "health tips",
]

# Best RSS feeds for breaking news
RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.livemint.com/rss/markets",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
]


def load_sent_news():
    global SENT_NEWS
    try:
        with open(SENT_NEWS_FILE, "r") as f:
            SENT_NEWS = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(SENT_NEWS)} sent news")
    except:
        SENT_NEWS = []


def save_sent_news():
    try:
        with open(SENT_NEWS_FILE, "w") as f:
            for item in SENT_NEWS[-2000:]:
                f.write(item + "\n")
    except:
        pass


async def send_telegram(message):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(TELEGRAM_URL, json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=20)
            print("✅ Sent!")
        except Exception as e:
            print("❌ Error:", e)


def clean_title(title):
    t = title.lower()
    for w in ["|", "watch:", "read:", "also read:", "exclusive |", "breaking:"]:
        t = t.replace(w, "")
    return " ".join(t.split())


def is_duplicate(title):
    cleaned = clean_title(title)
    for old in SENT_NEWS:
        if fuzz.token_set_ratio(cleaned, old) > 75:
            return True
    SENT_NEWS.append(cleaned)
    if len(SENT_NEWS) > 3000:
        SENT_NEWS.pop(0)
    save_sent_news()
    return False


def is_good_news(title):
    t = title.lower()
    if any(w in t for w in BLOCKED_STRICT):
        return False
    if any(w in t for w in BLOCKED_NEWS):
        return False
    is_stock = any(s in t for s in WATCHLIST)
    has_keyword = any(k in t for k in GOOD_KEYWORDS)
    return is_stock or has_keyword


def get_sentiment(title):
    t = title.lower()
    pos = [
        "profit rises", "profit jumps", "profit up", "revenue up",
        "revenue rises", "order bags", "order wins", "mou signed",
        "dividend declared", "bonus", "buyback", "rating upgraded",
        "fii inflow", "fii buys", "rally", "surge", "gain", "rises",
        "jumps", "listing gains", "rate cut", "approval", "record high",
        "commercial operations", "court orders lifting",
        "govt announces", "government approves", "support scheme",
    ]
    neg = [
        "profit falls", "profit drops", "loss widens", "revenue falls",
        "sebi bans", "sebi penalises", "fraud", "default",
        "promoter sells", "fii outflow", "fii sells",
        "falls", "drops", "declines", "crashes", "plunges",
        "listing loss", "rate hike", "tariff", "imposes duty",
        "downgraded", "resignation", "strikes", "war escalation",
    ]
    for w in pos:
        if w in t:
            return "🟢"
    for w in neg:
        if w in t:
            return "🔴"
    return "⚪"


def get_bullets(title, summary=""):
    t = title.lower()
    bullets = []

    # Clean title
    clean = title.strip()
    for remove in ["— check details", ": check details", "what's the last date to buy?",
                   "- check details", "| details", "exclusive |", "breaking:"]:
        clean = re.sub(re.escape(remove), "", clean, flags=re.IGNORECASE).strip()
    bullets.append(clean)

    # Specific context bullets
    if "gift nifty" in t or "sgx nifty" in t:
        if "falls" in t or "weak" in t or "negative" in t:
            bullets.append("Indian markets expected to open lower — watch for gap-down opening.")
            bullets.append("Crude oil and US market cues adding to negative sentiment.")
        elif "rises" in t or "positive" in t or "strong" in t:
            bullets.append("Indian markets expected to open higher — positive global cues.")
            bullets.append("Watch if gap-up sustains in early trade or gets sold into.")

    elif "net profit" in t or "pat" in t:
        pct = re.search(r'(\d+\.?\d*%)', title)
        if "rises" in t or "jumps" in t or "up" in t:
            p = f" by {pct.group(1)}" if pct else ""
            bullets.append(f"Net profit grew{p} — strong earnings beat market expectations.")
        elif "falls" in t or "drops" in t or "down" in t:
            p = f" by {pct.group(1)}" if pct else ""
            bullets.append(f"Net profit declined{p} — below street estimates, selling likely.")

    elif "order" in t and ("bags" in t or "wins" in t or "worth" in t or "from" in t):
        val = re.search(r'(₹[\d,.]+\s*(?:crore|lakh)?|rs\.?\s*[\d,.]+\s*(?:crore|lakh)?|\d+\.?\d*\s*(?:crore|lakh|billion))', title, re.IGNORECASE)
        if val:
            bullets.append(f"Order value: {val.group(1)} — strengthens revenue pipeline.")
        else:
            bullets.append("Fresh order win — improves revenue visibility and order book.")
        bullets.append("Consistent order wins signal strong demand in the sector.")

    elif "dividend" in t:
        div = re.search(r'(₹[\d,.]+|rs\.?\s*[\d,.]+)', title, re.IGNORECASE)
        if div:
            bullets.append(f"Dividend: {div.group(1)} per share — rewards shareholders.")
        else:
            bullets.append("Dividend declared — positive for income-focused investors.")
        bullets.append("Accumulate before record date to qualify for dividend.")

    elif "mou" in t or ("agreement" in t and "sign" in t):
        bullets.append("Strategic tie-up opens new revenue opportunities.")
        bullets.append("Watch for deal size and execution timeline as key monitorables.")

    elif "buyback" in t:
        val = re.search(r'(₹[\d,.]+\s*(?:crore)?)', title, re.IGNORECASE)
        if val:
            bullets.append(f"Buyback size: {val.group(1)} — management confident in fundamentals.")
        else:
            bullets.append("Buyback signals management confidence in company outlook.")

    elif "sebi" in t and ("ban" in t or "penali" in t or "fine" in t):
        bullets.append("SEBI regulatory action — governance concern, near-term stock pressure.")
        bullets.append("Company may appeal — watch for legal developments.")

    elif "trump" in t and ("tariff" in t or "imposes" in t or "duty" in t):
        bullets.append("US tariff action may impact Indian exports and global supply chains.")
        bullets.append("Affected sectors: solar, steel, pharma — watch for FII reaction.")

    elif "white house" in t or "us court" in t:
        bullets.append("US policy development — watch for impact on Indian markets and sectors.")

    elif "fii" in t and ("inflow" in t or "buys" in t):
        bullets.append("FII inflows signal foreign confidence — positive for broader market.")
        bullets.append("Sustained FII buying may support Nifty at higher levels.")

    elif "fii" in t and ("outflow" in t or "sells" in t):
        bullets.append("FII outflows create near-term selling pressure on Indian markets.")
        bullets.append("DII buying may provide support — track net flows carefully.")

    elif "rbi" in t and "cut" in t:
        bullets.append("RBI rate cut boosts liquidity — positive for banking and rate-sensitive sectors.")
        bullets.append("Housing, auto and NBFC sectors to benefit from lower borrowing costs.")

    elif "crude" in t or "brent" in t:
        bullets.append("Crude movement impacts India's import bill, trade deficit and rupee.")
        bullets.append("OMCs, aviation and paint sectors react directly to oil prices.")

    elif "rupee" in t:
        bullets.append("Rupee weakness helps IT exporters but hurts oil importers and inflation.")
        bullets.append("RBI may intervene through dollar sales if movement turns disorderly.")

    elif "iran" in t or "west asia" in t or "middle east" in t:
        bullets.append("Geopolitical escalation may spike crude — negative for India markets.")
        bullets.append("Risk-off sentiment may trigger FII outflows from emerging markets.")

    elif "commercial operations" in t or "cod" in t:
        bullets.append("New capacity now operational — adds to revenue from current quarter.")

    elif "npcil" in t or "nuclear" in t:
        bullets.append("Nuclear energy approval — unlocks long-term growth pipeline for company.")

    elif "govt announces" in t or "government approves" in t or "ministry" in t:
        bullets.append("Government policy support — positive for the sector and related stocks.")

    else:
        bullets.append("Development closely tracked for direct sector and stock impact.")

    return bullets[:3]


def get_source_short(source):
    s = source.lower()
    if "economic times" in s or "et markets" in s:
        return "ET"
    if "moneycontrol" in s:
        return "Moneycontrol"
    if "ndtv" in s:
        return "NDTV Profit"
    if "business standard" in s:
        return "Business Standard"
    if "mint" in s:
        return "LiveMint"
    if "reuters" in s:
        return "Reuters"
    if "cnbc" in s:
        return "CNBC"
    if "hindu" in s:
        return "The Hindu"
    return source


async def fetch_and_send():
    now = datetime.now(IST)
    if not (6 <= now.hour <= 23):
        return

    print("📰 Fetching news...")
    collected = []

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:25]:
                title = entry.title.strip()
                summary = re.sub('<[^<]+?>', '', entry.get("summary", "") or "").strip()

                if not title or len(title) < 15:
                    continue
                if is_duplicate(title):
                    continue
                if not is_good_news(title):
                    continue

                priority = 1 if any(s in title.lower() for s in WATCHLIST) else 2
                collected.append({
                    "title": title,
                    "summary": summary,
                    "source": feed.feed.get("title", "News"),
                    "priority": priority
                })
        except Exception as e:
            print("RSS Error:", e)

    collected.sort(key=lambda x: x["priority"])

    if not collected:
        print("No new news")
        return

    for item in collected[:6]:
        title = item["title"]
        summary = item["summary"]
        source = get_source_short(item["source"])
        sentiment = get_sentiment(title)
        bullets = get_bullets(title, summary)
        bullet_text = "\n".join(f"▪️ {b}" for b in bullets)
        msg = f"{sentiment}\n\n{bullet_text}\n\n📰 Source: {source}"
        await send_telegram(msg)
        await asyncio.sleep(3)


def get_change(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="2d")
        prev = hist["Close"].iloc[-2]
        curr = hist["Close"].iloc[-1]
        chg = ((curr - prev) / prev) * 100
        emoji = "🟢" if chg > 0 else "🔴"
        return f"{emoji} {curr:,.2f} ({chg:+.2f}%)"
    except:
        return "N/A"


def get_price(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="2d")
        curr = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        chg = ((curr - prev) / prev) * 100
        emoji = "🟢" if chg > 0 else "🔴"
        return f"{emoji} {curr:,.2f} ({chg:+.2f}%)"
    except:
        return "N/A"


async def morning_briefing():
    global LAST_BRIEFING_DATE
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if LAST_BRIEFING_DATE == today:
        return
    LAST_BRIEFING_DATE = today

    date_str = datetime.now(IST).strftime("%d %b %Y")

    dow = get_change("^DJI")
    nasdaq = get_change("^IXIC")
    sp500 = get_change("^GSPC")
    nifty = get_change("^NSEI")
    banknifty = get_change("^NSEBANK")
    crude = get_price("CL=F")
    gold = get_price("GC=F")

    # GIFT Nifty signal based on US markets
    if "🟢" in dow and "🟢" in nasdaq:
        gift_signal = "🟢 Positive — Gap Up Opening Expected"
    elif "🔴" in dow and "🔴" in nasdaq:
        gift_signal = "🔴 Negative — Gap Down Opening Expected"
    else:
        gift_signal = "⚪ Mixed — Flat to Volatile Opening Expected"

    msg = (
        f"🌅 *MORNING MARKET BRIEFING*\n"
        f"*{date_str} | 7:00 AM IST*\n\n"
        f"──────────────────────────────\n\n"
        f"🎯 *GIFT NIFTY SIGNAL*\n\n"
        f"▪️ {gift_signal}\n\n"
        f"──────────────────────────────\n\n"
        f"📊 *GLOBAL MARKETS (Overnight)*\n\n"
        f"▪️ Dow Jones : {dow}\n"
        f"▪️ Nasdaq : {nasdaq}\n"
        f"▪️ S&P 500 : {sp500}\n"
        f"▪️ Crude Oil : {crude}\n"
        f"▪️ Gold : {gold}\n\n"
        f"──────────────────────────────\n\n"
        f"🇮🇳 *INDIAN MARKET (Prev Close)*\n\n"
        f"▪️ Nifty 50 : {nifty}\n"
        f"▪️ Bank Nifty : {banknifty}\n\n"
        f"──────────────────────────────\n\n"
        f"🔥 *STOCKS IN FOCUS TODAY*\n\n"
        f"🟢 RVNL – Railway capex theme strong\n"
        f"🟢 SUZLON – Renewable energy momentum\n"
        f"🟢 BEL – Defence sector strong\n"
        f"🟢 IREDA – Green energy financing active\n"
        f"🟢 IEX – Power exchange in focus\n"
        f"🟢 YES BANK – Banking sector active\n"
        f"⚪ COAL INDIA – Commodity prices key\n"
        f"🔴 OLA ELECTRIC – Promoter activity watch\n\n"
        f"──────────────────────────────\n\n"
        f"⚠️ *KEY TRIGGERS TODAY*\n\n"
        f"▪️ FII / DII Activity\n"
        f"▪️ Corporate Results Season\n"
        f"▪️ Crude Oil Movement\n"
        f"▪️ RBI & Global Cues\n"
        f"▪️ Geopolitical Updates\n\n"
        f"──────────────────────────────"
    )
    await send_telegram(msg)


async def bot_loop():
    print("✅ Bot Started!")
    load_sent_news()
    await fetch_and_send()
    while True:
        now = datetime.now(IST)
        if now.hour == 7 and now.minute == 0:
            await morning_briefing()
        if now.minute % 10 == 0:
            await fetch_and_send()
        await asyncio.sleep(60)


def run_bot():
    asyncio.run(bot_loop())


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
