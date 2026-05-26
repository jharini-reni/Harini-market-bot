# =========================================================
# AI TELEGRAM STOCK MARKET BOT
# FINAL ADVANCED VERSION
# INDIA MARKET PRIORITY
# NO DUPLICATES
# IMPORTANT NEWS ONLY
# LIVE NEWS EVERY 1 MINUTE
# RENDER FREE PLAN READY
# =========================================================

import asyncio
import httpx
import feedparser
import yfinance as yf

from datetime import datetime
from pytz import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from rapidfuzz import fuzz

# =========================================================
# TELEGRAM CONFIG
# =========================================================

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

IST = timezone("Asia/Kolkata")

# =========================================================
# YOUR WATCHLIST
# =========================================================

WATCHLIST = [

    "groww",
    "sammancap",
    "iex",
    "mrpl",
    "lenskart",
    "jublfood",
    "embassy",
    "lemontree",
    "canbk",
    "nivabupa",
    "kalyankjil",
    "rvnl",
    "idea",
    "suzlon",
    "inoxwind",
    "coalindia",
    "vedl",
    "itc",
    "itchotels",
    "bel",
    "redington",
    "bankbaroda",
    "pnb",
    "wipro",
    "hyundai",
    "geojitfsl",
    "ireda",
    "tatatech",
    "yesbank",
    "eternal",
    "thangamayil",
    "idfcfirstbk",
    "hfcl",
    "texrail",
    "olaelec",
    "ather",
    "goldbees",
    "silverbees",
    "gold",
    "silver",
    "suntv"

]

# =========================================================
# IMPORTANT MARKET KEYWORDS
# =========================================================

IMPORTANT_KEYWORDS = [

    "fii",
    "fpi",
    "dii",
    "war",
    "rbi",
    "fed",
    "nifty",
    "sensex",
    "bank nifty",
    "crude",
    "inflation",
    "market",
    "stocks",
    "results",
    "dividend",
    "order",
    "india",
    "railway",
    "defence",
    "profit",
    "loss",
    "ipo",
    "tariff",
    "china",
    "russia",
    "ukraine",
    "middle east",
    "us market",
]

# =========================================================
# TRUSTED NEWS SOURCES
# =========================================================

RSS_FEEDS = [

    "https://www.moneycontrol.com/rss/business.xml",

    "https://www.moneycontrol.com/rss/MCtopnews.xml",

    "https://www.livemint.com/rss/markets",

    "https://feeds.feedburner.com/ndtvprofit-latest",

    "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/business.xml",

]

# =========================================================
# STORAGE
# =========================================================

SENT_NEWS = []

# =========================================================
# TELEGRAM SEND
# =========================================================

async def send_telegram(message):

    async with httpx.AsyncClient() as client:

        payload = {

            "chat_id": CHAT_ID,

            "text": message,

            "parse_mode": "HTML",

            "disable_web_page_preview": True

        }

        try:

            response = await client.post(
                TELEGRAM_URL,
                json=payload,
                timeout=20
            )

            print("Telegram Status:", response.status_code)

        except Exception as e:

            print("Telegram Error:", e)

# =========================================================
# STRONG DUPLICATE FILTER
# =========================================================

def is_duplicate(title):

    title = title.lower().strip()

    for old in SENT_NEWS:

        similarity = fuzz.token_sort_ratio(
            title,
            old
        )

        if similarity > 75:
            return True

    SENT_NEWS.append(title)

    if len(SENT_NEWS) > 2000:
        SENT_NEWS.pop(0)

    return False

# =========================================================
# SIMPLE SENTIMENT ENGINE
# =========================================================

def get_sentiment(title):

    title = title.lower()

    positive_words = [

        "surge",
        "gain",
        "rise",
        "profit",
        "approval",
        "bullish",
        "growth",
        "strong",
        "high",
        "record",
        "buy",
        "up",

    ]

    negative_words = [

        "fall",
        "decline",
        "loss",
        "war",
        "weak",
        "drop",
        "bearish",
        "crash",
        "cuts",
        "down",
        "sell",

    ]

    for word in positive_words:

        if word in title:
            return "🟢"

    for word in negative_words:

        if word in title:
            return "🔴"

    return "⚪"

# =========================================================
# MARKET IMPACT ENGINE
# =========================================================

def market_impact(title):

    title = title.lower()

    impacts = {

        "fii":
        "FII activity may impact overall market sentiment.",

        "fpi":
        "Foreign investor activity may influence markets.",

        "dii":
        "Domestic institutions remain active in markets.",

        "war":
        "Global uncertainty may increase market volatility.",

        "rbi":
        "Banking and financial stocks may stay active.",

        "fed":
        "US Fed commentary may affect global markets.",

        "crude":
        "Oil price movement may impact Indian markets.",

        "inflation":
        "Inflation concerns may pressure equities.",

        "railway":
        "Railway stocks may remain in focus.",

        "defence":
        "Defence stocks may see buying interest.",

        "order":
        "Positive order inflow may support stock sentiment.",

        "results":
        "Quarterly results may drive stock volatility.",

        "profit":
        "Strong earnings sentiment possible.",

        "loss":
        "Weak earnings sentiment possible.",

        "dividend":
        "Dividend-related buying interest possible.",

        "nifty":
        "Index movement may influence broader markets.",

        "sensex":
        "Benchmark indices remain volatile.",

        "gold":
        "Gold-related stocks and ETFs may stay active.",

        "silver":
        "Silver ETFs may remain volatile.",

    }

    for key, value in impacts.items():

        if key in title:
            return value

    return "Market participants monitoring developments."

# =========================================================
# MARKET OUTLOOK
# =========================================================

def market_prediction():

    try:

        dow = yf.Ticker("^DJI").history(period="2d")
        nasdaq = yf.Ticker("^IXIC").history(period="2d")
        sp500 = yf.Ticker("^GSPC").history(period="2d")

        dow_change = (
            (dow["Close"].iloc[-1] - dow["Close"].iloc[-2])
            / dow["Close"].iloc[-2]
        ) * 100

        nasdaq_change = (
            (nasdaq["Close"].iloc[-1] - nasdaq["Close"].iloc[-2])
            / nasdaq["Close"].iloc[-2]
        ) * 100

        sp_change = (
            (sp500["Close"].iloc[-1] - sp500["Close"].iloc[-2])
            / sp500["Close"].iloc[-2]
        ) * 100

        if dow_change > 0.5 and nasdaq_change > 0.5:

            return (
                "🟢 Positive opening expected due to strong global cues."
            )

        elif dow_change < -0.5 or sp_change < -0.5:

            return (
                "🔴 Weak opening possible due to negative global sentiment."
            )

        return "⚪ Flat to volatile opening expected."

    except:

        return "⚪ Market outlook unavailable."

# =========================================================
# INDEX CHANGE
# =========================================================

def get_change(symbol):

    try:

        ticker = yf.Ticker(symbol)

        hist = ticker.history(period="2d")

        prev_close = hist["Close"].iloc[-2]
        current = hist["Close"].iloc[-1]

        change = (
            (current - prev_close)
            / prev_close
        ) * 100

        emoji = "🟢" if change > 0 else "🔴"

        return f"{emoji} {change:+.2f}%"

    except:

        return "N/A"

# =========================================================
# WATCHLIST PRIORITY
# =========================================================

def is_watchlist_news(title):

    title = title.lower()

    for stock in WATCHLIST:

        if stock in title:
            return True

    return False

# =========================================================
# FETCH NEWS
# =========================================================

async def fetch_news():

    collected_news = []

    for url in RSS_FEEDS:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries[:20]:

                title = entry.title.strip()

                if is_duplicate(title):
                    continue

                title_lower = title.lower()

                important = any(
                    word in title_lower
                    for word in IMPORTANT_KEYWORDS
                )

                priority = (
                    is_watchlist_news(title)
                    or important
                )

                if not priority:
                    continue

                collected_news.append({

                    "title": title,

                    "source": feed.feed.get(
                        "title",
                        "News"
                    ),

                    "priority": priority

                })

        except Exception as e:

            print("RSS Error:", e)

    return collected_news

# =========================================================
# FORMAT NEWS
# =========================================================

def format_news(title, sentiment, impact, source):

    return f"""
{sentiment} <b>{title}</b>

📌 {impact}

📰 {source}
"""

# =========================================================
# LIVE MARKET NEWS
# =========================================================

async def send_live_news():

    now = datetime.now(IST)

    # MARKET HOURS
    if not (8 <= now.hour <= 16):
        return

    print("Checking Market News...")

    news_list = await fetch_news()

    news_list = sorted(
        news_list,
        key=lambda x: x["priority"],
        reverse=True
    )

    for news in news_list[:6]:

        title = news["title"]

        sentiment = get_sentiment(title)

        impact = market_impact(title)

        source = news["source"]

        message = format_news(
            title,
            sentiment,
            impact,
            source
        )

        await send_telegram(message)

        await asyncio.sleep(2)

# =========================================================
# MORNING MARKET BRIEFING
# =========================================================

async def morning_briefing():

    today = datetime.now(IST).strftime("%d %b %Y")

    dow = get_change("^DJI")
    nasdaq = get_change("^IXIC")
    sp500 = get_change("^GSPC")
    nifty = get_change("^NSEI")

    outlook = market_prediction()

    msg = f"""
🌅 <b>MORNING MARKET SETUP</b>
📅 {today}

━━━━━━━━━━━━━━

📊 <b>GLOBAL MARKETS</b>

▪ Dow Jones: {dow}
▪ Nasdaq: {nasdaq}
▪ S&P 500: {sp500}

🇮🇳 <b>NIFTY OUTLOOK</b>

▪ Nifty: {nifty}

📌 {outlook}

🔥 <b>WATCHLIST STOCKS</b>

🟢 RVNL
🟢 SUZLON
🟢 BEL
🟢 IREDA
🟢 YES BANK
🟢 IEX
🔴 ITC

⚠️ <b>KEY MARKET TRIGGERS</b>

▪ FII / DII Activity
▪ RBI Commentary
▪ Crude Oil Prices
▪ Corporate Results
▪ Global Market Cues

━━━━━━━━━━━━━━
"""

    await send_telegram(msg)

# =========================================================
# SCHEDULER
# =========================================================

scheduler = AsyncIOScheduler(timezone=IST)

# 7 AM MORNING BRIEFING
scheduler.add_job(
    morning_briefing,
    "cron",
    hour=7,
    minute=0
)

# LIVE NEWS EVERY 1 MINUTE
scheduler.add_job(
    send_live_news,
    "interval",
    minutes=1
)

scheduler.start()

# =========================================================
# START BOT
# =========================================================

print("✅ AI Stock Market Bot Running...")

asyncio.get_event_loop().run_forever()