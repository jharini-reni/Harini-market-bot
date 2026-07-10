import asyncio
import httpx
import feedparser
import yfinance as yf
from datetime import datetime, timedelta
from pytz import timezone
from rapidfuzz import fuzz
import threading
import json
import re
from flask import Flask

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = timezone("Asia/Kolkata")

SENT_NEWS = []
SENT_BSE = set()
LAST_BRIEFING_DATE = None
SENT_NEWS_FILE = "sent_news.txt"
SENT_BSE_FILE = "sent_bse.txt"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ India Market Bot Running!", 200

@app.route('/health')
def health():
    return "OK", 200

# =========================================================
# YOUR WATCHLIST WITH NSE SYMBOLS
# =========================================================
WATCHLIST_SYMBOLS = {
    "RVNL": "Rail Vikas Nigam",
    "SUZLON": "Suzlon Energy",
    "IDEA": "Vodafone Idea",
    "YESBANK": "Yes Bank",
    "IREDA": "IREDA",
    "IEX": "Indian Energy Exchange",
    "BEL": "Bharat Electronics",
    "ITC": "ITC",
    "COALINDIA": "Coal India",
    "VEDL": "Vedanta",
    "CANBK": "Canara Bank",
    "BANKBARODA": "Bank of Baroda",
    "PNB": "Punjab National Bank",
    "WIPRO": "Wipro",
    "TATATECH": "Tata Technologies",
    "OLAELEC": "Ola Electric",
    "INOXWIND": "Inox Wind",
    "MRPL": "MRPL",
    "JUBLFOOD": "Jubilant FoodWorks",
    "THANGAMAYL": "Thangamayil Jewellery",
    "ATHENERGY": "Ather Energy",
    "KALYANKJIL": "Kalyan Jewellers",
    "NIVABUPA": "Niva Bupa",
    "REDINGTON": "Redington",
    "HYUNDAI": "Hyundai India",
    "GEOJITFSL": "Geojit Financial",
    "GOLDBEES": "GoldBees ETF",
    "SILVERBEES": "SilverBees ETF",
    "LMNTREE": "Lemon Tree Hotels",
    "ETERNAL": "Eternal",
    "HFCL": "HFCL",
    "IRFC": "IRFC",
    "DIACABS": "Diamond Cables",
}

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/",
}

# BSE scrip codes for watchlist stocks
BSE_CODES = {
    "RVNL": "543213",
    "SUZLON": "532667",
    "IDEA": "532822",
    "YESBANK": "532648",
    "IREDA": "544097",
    "IEX": "540750",
    "BEL": "500049",
    "ITC": "500875",
    "COALINDIA": "533278",
    "VEDL": "500295",
    "CANBK": "532483",
    "BANKBARODA": "532134",
    "PNB": "532461",
    "WIPRO": "507685",
    "TATATECH": "544028",
    "INOXWIND": "539083",
    "MRPL": "500109",
    "JUBLFOOD": "533155",
    "KALYANKJIL": "543278",
    "NIVABUPA": "543963",
    "REDINGTON": "532805",
    "HFCL": "500183",
    "IRFC": "543257",
}

BLOCKED_WORDS = [
    "should you", "would you", "can you",
    "is it time", "time to buy", "time to sell",
    "buy or sell", "buy or avoid", "should you subscribe",
    "what's buzzing", "what is buzzing", "what's fueling",
    "where are prices", "where is market",
    "top stocks", "best stocks", "stocks to buy",
    "multibagger", "expert suggests", "analyst recommends",
    "technical analysis", "chart pattern", "moving average",
    "share price live", "price live update",
    "sip returns", "mutual fund nav", "how to invest",
    "beginners guide", "city-wise rates", "check rates",
    "ipo gmp", "grey market premium", "intraday strategy",
    "weekly outlook", "monthly outlook",
    "5 stocks", "10 stocks", "top 5", "top 10",
    "privacy", "google assistant", "pixel launch",
    "cautiously optimistic", "earnings revival",
    "why tcs", "why infosys", "why wipro",
    "4-year high", "amid ai", "job loss fears",
]

BLOCKED_NEWS = [
    "bitcoin", "ethereum", "crypto", "cryptocurrency",
    "nft", "defi", "binance", "cricket match",
    "bollywood", "hollywood", "celebrity",
    "weather forecast", "recipe", "fashion",
    "horoscope", "astrology", "health tips",
]

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.livemint.com/rss/markets",
]

IMPORTANT_KEYWORDS = [
    "results", "profit", "loss", "revenue", "ebitda", "q4", "q3", "q2", "q1",
    "dividend", "bonus", "split", "buyback", "qip", "ofs",
    "block deal", "bulk deal", "stake", "promoter",
    "order", "contract", "mou", "agreement", "wins", "bags", "awarded",
    "merger", "acquisition", "takeover", "demerger",
    "nifty", "sensex", "bank nifty", "gift nifty",
    "fii", "fpi", "dii", "rbi", "sebi", "repo rate",
    "rupee", "crude oil", "gold price", "silver price",
    "fed", "dow jones", "nasdaq", "iran", "trump", "war",
    "ipo", "listing", "rating upgrade", "rating downgrade",
]


# =========================================================
# PERSISTENCE
# =========================================================
def load_sent_news():
    global SENT_NEWS
    try:
        with open(SENT_NEWS_FILE, "r") as f:
            SENT_NEWS = [line.strip() for line in f if line.strip()]
    except:
        SENT_NEWS = []

def save_sent_news():
    try:
        with open(SENT_NEWS_FILE, "w") as f:
            for item in SENT_NEWS[-2000:]:
                f.write(item + "\n")
    except:
        pass

def load_sent_bse():
    global SENT_BSE
    try:
        with open(SENT_BSE_FILE, "r") as f:
            SENT_BSE = set(line.strip() for line in f if line.strip())
    except:
        SENT_BSE = set()

def save_sent_bse():
    try:
        with open(SENT_BSE_FILE, "w") as f:
            for item in list(SENT_BSE)[-3000:]:
                f.write(item + "\n")
    except:
        pass


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
            print("❌ Telegram Error:", e)


# =========================================================
# NSE CORPORATE ANNOUNCEMENTS
# =========================================================
async def fetch_nse_announcements():
    results = []
    try:
        async with httpx.AsyncClient(headers=NSE_HEADERS, follow_redirects=True) as client:
            # Get NSE cookies first
            await client.get("https://www.nseindia.com", timeout=10)
            await asyncio.sleep(1)

            r = await client.get(
                "https://www.nseindia.com/api/corporate-announcements?index=equities",
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                for item in data[:50]:
                    symbol = item.get("symbol", "")
                    subject = item.get("subject", "").strip()
                    desc = item.get("desc", "").strip()
                    an_id = item.get("an_id", str(item.get("exchdisstime", "")))

                    if symbol in WATCHLIST_SYMBOLS and an_id not in SENT_BSE:
                        SENT_BSE.add(an_id)
                        results.append({
                            "symbol": symbol,
                            "name": WATCHLIST_SYMBOLS.get(symbol, symbol),
                            "subject": subject,
                            "desc": desc,
                            "source": "NSE"
                        })
    except Exception as e:
        print("NSE API Error:", e)
    return results


# =========================================================
# BSE CORPORATE ANNOUNCEMENTS
# =========================================================
async def fetch_bse_announcements():
    results = []
    try:
        async with httpx.AsyncClient(headers=BSE_HEADERS, follow_redirects=True) as client:
            r = await client.get(
                "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&category=-1&subcategory=-1&strSearch=&FromDate=&ToDate=&scrip_cd=",
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                announcements = data.get("Table", [])
                for item in announcements[:50]:
                    scrip = str(item.get("SCRIP_CD", ""))
                    headline = item.get("HEADLINE", "").strip()
                    news_id = str(item.get("NEWSSUB", item.get("NewsID", "")))
                    symbol = next((k for k, v in BSE_CODES.items() if v == scrip), None)

                    if symbol and news_id not in SENT_BSE:
                        SENT_BSE.add(news_id)
                        results.append({
                            "symbol": symbol,
                            "name": WATCHLIST_SYMBOLS.get(symbol, symbol),
                            "subject": headline,
                            "desc": "",
                            "source": "BSE"
                        })
    except Exception as e:
        print("BSE API Error:", e)
    return results


# =========================================================
# FORMAT ANNOUNCEMENT — KALYAN STYLE
# =========================================================
def get_emoji(subject):
    s = subject.lower()
    pos = ["profit", "surge", "rise", "gain", "order", "wins", "bags",
           "dividend", "bonus", "buyback", "approval", "mou", "record",
           "strong", "beat", "awarded", "contract", "expand", "launch",
           "acquisition", "commercial operation", "revenue up"]
    neg = ["loss", "fall", "drop", "penalty", "sebi", "fraud", "default",
           "selling", "downgrade", "miss", "weak", "concern", "resignation",
           "misleading", "warning", "decline", "crash"]
    for w in pos:
        if w in s:
            return "🟢"
    for w in neg:
        if w in s:
            return "🔴"
    return "⚪"


def get_sentiment_label(subject):
    emoji = get_emoji(subject)
    if emoji == "🟢":
        return "Positive"
    elif emoji == "🔴":
        return "Negative"
    return "Neutral"


def format_announcement(item):
    symbol = item["symbol"]
    name = item["name"]
    subject = item["subject"]
    desc = item.get("desc", "")
    source = item["source"]
    emoji = get_emoji(subject)
    sentiment = get_sentiment_label(subject)

    msg = f"*{name} – {subject}*\n\n"

    # Add description bullets if available
    if desc and len(desc) > 20:
        # Clean HTML
        desc_clean = re.sub('<[^<]+?>', '', desc).strip()
        # Split into sentences
        sentences = [s.strip() for s in re.split(r'[.\n]', desc_clean) if len(s.strip()) > 20]
        for s in sentences[:3]:
            msg += f"▪️ {s}\n"
        msg += "\n"

    msg += f"{emoji} ({sentiment})\n"
    msg += f"📰 Source: {source} Filing"
    return msg


# =========================================================
# RSS NEWS FEED
# =========================================================
def clean_title(title):
    t = title.lower()
    for w in ["latest", "live", "today", "update", "updates", "|"]:
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


def is_real_news(title):
    t = title.lower()
    if any(w in t for w in BLOCKED_WORDS):
        return False
    if any(w in t for w in BLOCKED_NEWS):
        return False
    return any(k in t for k in IMPORTANT_KEYWORDS)


def get_rss_sentiment(title):
    t = title.lower()
    pos = ["profit", "surge", "rise", "gain", "wins", "bags", "jump",
           "dividend", "bonus", "buyback", "rally", "approval", "mou",
           "record high", "strong", "beat", "inflow", "buying"]
    neg = ["loss", "fall", "drop", "decline", "crash", "penalty",
           "sebi ban", "fraud", "default", "selling", "outflow",
           "downgrade", "miss", "weak", "concern", "plunge", "misleading"]
    for w in pos:
        if w in t:
            return "🟢"
    for w in neg:
        if w in t:
            return "🔴"
    return "⚪"


def get_impact(title):
    t = title.lower()
    if ("results" in t or "profit" in t) and ("jump" in t or "surge" in t or "rise" in t):
        return "Strong quarterly earnings — positive for stock sentiment and near-term outlook."
    if ("results" in t or "profit" in t) and ("loss" in t or "fall" in t or "miss" in t):
        return "Weak quarterly earnings — selling pressure likely near-term."
    if "order" in t and ("win" in t or "bag" in t or "award" in t):
        return "Order win improves revenue visibility and strengthens order book."
    if "dividend" in t:
        return "Dividend declared — investors may accumulate before record date."
    if "buyback" in t:
        return "Buyback signals management confidence — positive for shareholders."
    if "sebi" in t and ("penalty" in t or "ban" in t):
        return "SEBI regulatory action — governance concern, near-term pressure likely."
    if "fii" in t or "fpi" in t:
        return "FII activity — foreign flows are key driver for market direction."
    if "rbi" in t or "repo rate" in t:
        return "RBI policy update — banking and rate-sensitive stocks may react sharply."
    if "crude oil" in t or "brent" in t:
        return "Crude oil movement impacts India's import bill, rupee and inflation."
    if "rupee" in t:
        return "Rupee movement affects IT exporters and import-heavy sectors."
    if "gift nifty" in t or "dow" in t or "nasdaq" in t:
        return "Global cues setting direction for Indian market open today."
    if "iran" in t or "war" in t or "middle east" in t:
        return "Geopolitical tension may spike crude — negative for India's trade deficit."
    return "Development closely tracked for potential sector and stock impact."


def get_source_short(source):
    s = source.lower()
    if "economic times" in s:
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


async def fetch_rss_news():
    collected = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                title = entry.title.strip()
                if not title or len(title) < 15:
                    continue
                if is_duplicate(title):
                    continue
                if not is_real_news(title):
                    continue
                collected.append({
                    "title": title,
                    "source": feed.feed.get("title", "News")
                })
        except Exception as e:
            print("RSS Error:", e)
    return collected


# =========================================================
# SEND ALL NEWS
# =========================================================
async def send_all_news():
    now = datetime.now(IST)
    if not (6 <= now.hour <= 23):
        return

    print("🔍 Checking NSE/BSE announcements...")

    # 1. NSE Corporate Announcements
    nse_items = await fetch_nse_announcements()
    for item in nse_items[:5]:
        msg = format_announcement(item)
        await send_telegram(msg)
        await asyncio.sleep(2)

    # 2. BSE Corporate Announcements
    bse_items = await fetch_bse_announcements()
    for item in bse_items[:5]:
        msg = format_announcement(item)
        await send_telegram(msg)
        await asyncio.sleep(2)

    save_sent_bse()

    # 3. RSS News (market/global)
    print("📰 Checking RSS news...")
    rss_items = await fetch_rss_news()
    for item in rss_items[:4]:
        title = item["title"]
        source = get_source_short(item["source"])
        sentiment = get_rss_sentiment(title)
        impact = get_impact(title)

        msg = (
            f"{sentiment} *{title}*\n\n"
            f"▪️ {impact}\n\n"
            f"📰 Source: {source}"
        )
        await send_telegram(msg)
        await asyncio.sleep(2)


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
# MAIN BOT LOOP
# =========================================================
async def bot_loop():
    print("✅ Bot Started with NSE + BSE APIs!")
    load_sent_news()
    load_sent_bse()
    await send_all_news()
    while True:
        now = datetime.now(IST)
        if now.hour == 7 and now.minute == 0:
            await morning_briefing()
        if now.minute % 10 == 0:
            await send_all_news()
        await asyncio.sleep(60)


def run_bot():
    asyncio.run(bot_loop())


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
