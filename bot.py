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

# =========================================================
# WATCHLIST
# =========================================================
WATCHLIST = [
    "rvnl", "suzlon", "vodafone idea", "yes bank", "ireda", "iex",
    "bel", "itc", "coal india", "vedanta", "canara bank",
    "bank of baroda", "pnb", "wipro", "tata tech", "tatatech",
    "ola electric", "inox wind", "mrpl", "jublfood", "jubilant food",
    "thangamayil", "ather energy", "kalyan jewellers", "kalyankjil",
    "niva bupa", "redington", "hyundai india", "diamond cable",
    "geojit", "goldbees", "silverbees", "lg india", "groww",
    "lenskart", "samman", "embassy reit", "lemon tree", "eternal",
    "hfcl", "irfc", "diacabs",
]

# =========================================================
# STRICT BLOCKED — Only block clear junk
# =========================================================
BLOCKED_STRICT = [
    # Questions
    "what's the last date", "what is the last date",
    "check details", "check here", "find out",
    "should you", "would you invest", "is it time",
    "buy or sell", "buy or avoid",
    # Analysis/opinion
    "why tcs", "why infosys", "why wipro", "why nifty",
    "here's why", "amid ai job", "job loss fears",
    "4-year high amid", "cautiously optimistic",
    # Recommendations
    "top stocks", "best stocks", "multibagger",
    "expert says", "analyst says buy",
    "technical analysis", "chart pattern",
    "sip returns", "mutual fund nav",
    "how to invest", "beginners guide",
    "city-wise", "check rates",
    "ipo gmp", "grey market",
    "intraday strategy", "weekly outlook",
    # Irrelevant
    "bitcoin", "crypto", "ethereum",
    "cricket", "bollywood", "weather forecast",
    "horoscope", "health tips", "recipe",
    "china breaks musk", "elon musk",
]

# =========================================================
# ONLY REAL CORPORATE/MARKET NEWS
# =========================================================
GOOD_KEYWORDS = [
    # Results with numbers
    "net profit", "revenue", "ebitda", "pat rises", "pat falls",
    "profit rises", "profit falls", "profit jumps", "profit drops",
    "q1 result", "q2 result", "q3 result", "q4 result",
    "quarterly result", "annual result",
    # Corporate actions with specifics
    "dividend of rs", "dividend declared", "dividend record date",
    "bonus shares", "stock split", "buyback",
    "order worth", "order of rs", "bags order", "wins order",
    "order from", "contract from", "mou with", "mou signed",
    "capacity expansion", "new plant", "commercial operations",
    "qip allotment", "block deal", "bulk deal",
    "promoter buys", "promoter sells", "stake acquired",
    "merger approved", "acquisition of", "takeover bid",
    "rating upgraded", "rating downgraded",
    # Market moving news
    "nifty", "sensex", "bank nifty", "gift nifty",
    "fii buys", "fii sells", "fii inflow", "fii outflow",
    "rbi cuts", "rbi hikes", "repo rate",
    "rupee falls", "rupee rises", "rupee hits",
    "crude oil", "brent crude", "opec cuts",
    "gold rises", "gold falls", "mcx gold",
    "us fed", "federal reserve", "rate cut", "rate hike",
    "dow jones", "nasdaq falls", "nasdaq rises",
    "iran", "war", "middle east", "west asia",
    "sebi bans", "sebi penalises", "sebi orders",
    "ipo listing", "listing gains", "listing loss",
    "india gdp", "cpi inflation", "iip data",
]

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.livemint.com/rss/markets",
    "https://www.thehindu.com/business/markets/feeder/default.rss",
]


# =========================================================
# PERSISTENCE
# =========================================================
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


# =========================================================
# FILTERS
# =========================================================
def clean_title(title):
    t = title.lower()
    for w in ["|", "watch:", "read:", "also read:"]:
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
    # Block junk
    if any(w in t for w in BLOCKED_STRICT):
        return False
    # Must have real news keyword
    return any(k in t for k in GOOD_KEYWORDS)


def is_my_stock(title):
    return any(s in title.lower() for s in WATCHLIST)


# =========================================================
# SENTIMENT
# =========================================================
def get_sentiment(title):
    t = title.lower()
    pos = [
        "profit rises", "profit jumps", "profit up", "net profit up",
        "revenue up", "revenue rises", "revenue grows",
        "bags order", "wins order", "order from", "mou signed",
        "dividend declared", "dividend of rs", "bonus shares",
        "buyback", "rating upgraded", "fii inflow", "fii buys",
        "rally", "surge", "gain", "rises", "jumps", "climbs",
        "listing gains", "rate cut", "rbi cuts", "approval",
        "commercial operations", "capacity expansion",
        "record high", "all time high", "strong demand",
    ]
    neg = [
        "profit falls", "profit drops", "profit declines", "net profit falls",
        "revenue falls", "revenue drops", "loss widens", "loss reported",
        "sebi bans", "sebi penalises", "sebi orders", "fraud",
        "promoter sells", "stake sale", "fii outflow", "fii sells",
        "falls", "drops", "declines", "crashes", "plunges", "slips",
        "listing loss", "rate hike", "rbi hikes", "default",
        "downgraded", "resignation", "warning", "concern",
    ]
    for w in pos:
        if w in t:
            return "🟢"
    for w in neg:
        if w in t:
            return "🔴"
    return "⚪"


# =========================================================
# BULLET POINTS — ACTUAL CONTENT
# =========================================================
def extract_numbers(text):
    """Extract key numbers/figures from text"""
    patterns = [
        r'₹[\d,.]+ ?(?:crore|lakh|billion|million)?',
        r'rs\.? ?[\d,.]+ ?(?:crore|lakh|billion|million)?',
        r'\d+\.?\d*%',
        r'\d+\.?\d*x',
    ]
    numbers = []
    for p in patterns:
        found = re.findall(p, text.lower())
        numbers.extend(found)
    return numbers[:3]


def get_bullets(title, summary=""):
    t = title.lower()
    s = summary.lower() if summary else ""
    bullets = []

    # First bullet = clean headline
    clean = title.strip()
    # Remove "check details", "what's the last date" etc from title
    for remove in ["— check details", ": check details", "what's the last date to buy?",
                   "- check details", ": details", "| details"]:
        clean = clean.replace(remove, "").replace(remove.title(), "").strip()
    bullets.append(clean)

    # Extract numbers from summary
    if summary:
        nums = extract_numbers(summary)

    # Second bullet — specific context
    if "net profit" in t and "rises" in t or "jumps" in t or "up" in t:
        # Try to find % from title
        pct = re.search(r'(\d+\.?\d*%)', title)
        if pct:
            bullets.append(f"Net profit grew {pct.group(1)} — strong earnings beat estimates.")
        else:
            bullets.append("Strong net profit growth — quarterly earnings beat market expectations.")

    elif "net profit" in t and ("falls" in t or "drops" in t or "declines" in t):
        pct = re.search(r'(\d+\.?\d*%)', title)
        if pct:
            bullets.append(f"Net profit declined {pct.group(1)} — below street estimates.")
        else:
            bullets.append("Net profit declined — weak quarterly performance below expectations.")

    elif "order" in t and ("bags" in t or "wins" in t or "worth" in t or "from" in t):
        val = re.search(r'(₹[\d,.]+\s*(?:crore|lakh)?|\d+\.?\d*\s*(?:crore|lakh|billion))', title, re.IGNORECASE)
        if val:
            bullets.append(f"Order value: {val.group(1)} — improves revenue visibility and order book.")
        else:
            bullets.append("Fresh order win — strengthens revenue pipeline and execution outlook.")
        bullets.append("Consistent order wins signal strong demand and business momentum.")

    elif "dividend" in t:
        div = re.search(r'(₹[\d,.]+|rs\.?\s*[\d,.]+)', title, re.IGNORECASE)
        if div:
            bullets.append(f"Dividend: {div.group(1)} per share — rewards shareholders.")
        else:
            bullets.append("Dividend declared — positive signal for income investors.")
        bullets.append("Investors may accumulate before record date to qualify for dividend.")

    elif "mou" in t or ("agreement" in t and "sign" in t):
        bullets.append("Strategic partnership secured — opens new revenue opportunities.")
        bullets.append("Execution of agreement will be key monitorable going forward.")

    elif "buyback" in t:
        val = re.search(r'(₹[\d,.]+\s*(?:crore)?)', title, re.IGNORECASE)
        if val:
            bullets.append(f"Buyback size: {val.group(1)} — management showing confidence in business.")
        else:
            bullets.append("Buyback signals management confidence in company fundamentals.")
        bullets.append("Shareholders tendering at buyback price may receive premium over CMP.")

    elif "sebi" in t and ("ban" in t or "penali" in t or "order" in t):
        bullets.append("SEBI regulatory action raises governance concerns — near-term pressure likely.")
        bullets.append("Company may file appeal — watch for legal developments.")

    elif "commercial operations" in t or "cod" in t:
        bullets.append("New capacity operational — directly adds to revenue from current quarter.")
        bullets.append("Positive for earnings growth and order execution track record.")

    elif "fii" in t and ("inflow" in t or "buys" in t or "buying" in t):
        val = re.search(r'(₹[\d,.]+\s*(?:crore)?)', title, re.IGNORECASE)
        if val:
            bullets.append(f"FII inflow: {val.group(1)} — strong foreign confidence in India.")
        else:
            bullets.append("FII inflows signal foreign confidence — positive for broader market.")
        bullets.append("Sustained FII buying may push Nifty to test higher resistance levels.")

    elif "fii" in t and ("outflow" in t or "sells" in t or "selling" in t):
        bullets.append("FII outflows create near-term selling pressure — watch for reversal signals.")
        bullets.append("DII buying may provide support — track net flows carefully.")

    elif "rbi" in t and ("cut" in t or "cuts" in t):
        bullets.append("RBI rate cut boosts liquidity — positive for banking and rate-sensitive sectors.")
        bullets.append("Housing, auto and NBFC sectors likely to benefit from lower borrowing costs.")

    elif "crude" in t or "brent" in t or "oil" in t:
        bullets.append("Crude oil movement directly impacts India's import bill and trade deficit.")
        bullets.append("OMCs, aviation and paint sectors may react to this price movement.")

    elif "gift nifty" in t or "sgx nifty" in t:
        bullets.append("Pre-market indicator — signals likely opening direction for Nifty 50 today.")
        bullets.append("Watch if gap sustains or fills in early trade session.")

    elif "dow" in t or "nasdaq" in t or "wall street" in t:
        bullets.append("US market performance sets tone for Asian markets and FII flows into India.")
        bullets.append("Nasdaq/Dow movement may influence IT and tech stocks at Indian market open.")

    elif "iran" in t or "middle east" in t or "war" in t:
        bullets.append("Geopolitical tension may spike crude oil — negative for India's trade deficit.")
        bullets.append("Risk-off global sentiment may trigger FII outflows from emerging markets.")

    elif "rupee" in t:
        bullets.append("Rupee weakness benefits IT exporters but pressures oil importers and inflation.")
        bullets.append("RBI may intervene through dollar sales if rupee movement turns disorderly.")

    elif "qip" in t:
        val = re.search(r'(₹[\d,.]+\s*(?:crore)?)', title, re.IGNORECASE)
        if val:
            bullets.append(f"QIP size: {val.group(1)} — institutional fundraise for expansion/debt reduction.")
        else:
            bullets.append("QIP fundraise — institutional capital infusion for growth and expansion.")
        bullets.append("Dilution impact on EPS to be monitored — watch utilisation of proceeds.")

    elif "merger" in t or "acquisition" in t:
        bullets.append("M&A deal may unlock significant value — target stock likely to see sharp movement.")
        bullets.append("Regulatory approvals and synergy benefits will be closely tracked by investors.")

    elif "rating" in t and "upgraded" in t:
        bullets.append("Credit rating upgrade reduces borrowing costs — positive for margins and expansion.")
        bullets.append("Higher rating improves access to cheaper capital for future growth plans.")

    elif "block deal" in t or "bulk deal" in t:
        val = re.search(r'(₹[\d,.]+\s*(?:crore)?)', title, re.IGNORECASE)
        if val:
            bullets.append(f"Deal size: {val.group(1)} — large institutional transaction in the stock.")
        else:
            bullets.append("Large institutional transaction — watch for follow-up buying or selling.")
        bullets.append("Identify buyer/seller to gauge direction — promoter sell signals caution.")

    else:
        bullets.append("Market participants tracking this for direct sector and stock impact.")

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
    if "hindu" in s:
        return "The Hindu"
    return source


# =========================================================
# TELEGRAM
# =========================================================
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


# =========================================================
# FETCH & SEND NEWS
# =========================================================
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
                summary = entry.get("summary", "") or ""
                summary = re.sub('<[^<]+?>', '', summary).strip()

                if not title or len(title) < 15:
                    continue
                if is_duplicate(title):
                    continue
                if not is_good_news(title):
                    continue

                # Prioritise watchlist stocks
                priority = 1 if is_my_stock(title) else 2
                collected.append({
                    "title": title,
                    "summary": summary,
                    "source": feed.feed.get("title", "News"),
                    "priority": priority
                })
        except Exception as e:
            print("RSS Error:", e)

    # Sort — watchlist stocks first
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


# =========================================================
# 7 AM MORNING BRIEFING
# =========================================================
def get_change(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="2d")
        prev = hist["Close"].iloc[-2]
        curr = hist["Close"].iloc[-1]
        chg = ((curr - prev) / prev) * 100
        emoji = "🟢" if chg > 0 else "🔴"
        return f"{emoji} {chg:+.2f}%"
    except:
        return "N/A"


async def morning_briefing():
    global LAST_BRIEFING_DATE
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if LAST_BRIEFING_DATE == today:
        return
    LAST_BRIEFING_DATE = today

    date_str = datetime.now(IST).strftime("%d %b %Y")
    msg = (
        f"🌅 *MORNING MARKET BRIEFING*\n"
        f"*{date_str} | 7:00 AM IST*\n\n"
        f"──────────────────────────────\n\n"
        f"📊 *GLOBAL MARKETS (Overnight)*\n\n"
        f"▪️ Dow Jones : {get_change('^DJI')}\n"
        f"▪️ Nasdaq : {get_change('^IXIC')}\n"
        f"▪️ S&P 500 : {get_change('^GSPC')}\n\n"
        f"──────────────────────────────\n\n"
        f"🇮🇳 *INDIAN MARKET SETUP*\n\n"
        f"▪️ Nifty 50 : {get_change('^NSEI')}\n"
        f"▪️ Bank Nifty : {get_change('^NSEBANK')}\n\n"
        f"📌 Investors tracking crude oil, FII activity and global cues closely.\n\n"
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


# =========================================================
# MAIN LOOP
# =========================================================
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
