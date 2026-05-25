# =========================================================
# AI TELEGRAM STOCK MARKET BOT
# FINAL PRODUCTION VERSION
# =========================================================

import os
import asyncio
import httpx
import feedparser
import yfinance as yf

from datetime import datetime
from pytz import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from transformers import pipeline
from rapidfuzz import fuzz
from dotenv import load_dotenv

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

BOT_TOKEN = os.getenv("8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc")
CHAT_ID = os.getenv("1212371388")

TELEGRAM_URL = f"https://api.telegram.org/bot{8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"}/sendMessage"

IST = timezone("Asia/Kolkata")

# =========================================================
# AI SENTIMENT MODEL
# =========================================================

print("Loading AI model...")

finbert = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert"
)

print("AI Loaded Successfully")

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
# TRUSTED NEWS SOURCES
# =========================================================

RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/business.xml",
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

            await client.post(
                TELEGRAM_URL,
                json=payload,
                timeout=20
            )

            print("Message Sent")

        except Exception as e:
            print("Telegram Error:", e)

# =========================================================
# DUPLICATE FILTER
# =========================================================

def is_duplicate(title):

    for old in SENT_NEWS:

        similarity = fuzz.ratio(
            title.lower(),
            old.lower()
        )

        if similarity > 85:
            return True

    SENT_NEWS.append(title)

    if len(SENT_NEWS) > 1000:
        SENT_NEWS.pop(0)

    return False

# =========================================================
# AI SENTIMENT
# =========================================================

def get_sentiment(title):

    try:

        result = finbert(title)[0]

        label = result["label"].lower()

        if label == "positive":
            return "🟢"

        elif label == "negative":
            return "🔴"

        return "⚪"

    except:
        return "⚪"

# =========================================================
# MARKET IMPACT ENGINE
# =========================================================

def market_impact(title):

    title = title.lower()

    rules = {
        "rbi": "Banking stocks may remain active today.",
        "inflation": "Markets may react cautiously.",
        "crude": "Oil-sensitive sectors may face pressure.",
        "war": "Global volatility may increase.",
        "railway": "Railway stocks may stay in focus.",
        "defence": "Defence sector sentiment may improve.",
        "order": "Positive sentiment possible in related stocks.",
        "fed": "Global market volatility may continue.",
        "gold": "Gold-related stocks may stay active.",
        "silver": "Silver ETFs may remain volatile.",
        "results": "Stock-specific volatility expected.",
    }

    for key, reason in rules.items():

        if key in title:
            return reason

    return "Monitoring market impact."

# =========================================================
# MARKET PREDICTION ENGINE
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

        if dow_change > 0.5 and nasdaq_change > 0.5:

            return (
                "🟢 Indian markets may open positive "
                "supported by strong global cues."
            )

        elif dow_change < -0.5:

            return (
                "🔴 Weak market opening possible "
                "due to weak global sentiment."
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

            for entry in feed.entries[:10]:

                title = entry.title

                if is_duplicate(title):
                    continue

                priority = is_watchlist_news(title)

                collected_news.append({
                    "title": title,
                    "source": feed.feed.get("title", "News"),
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

{impact}

— {source}
"""

# =========================================================
# LIVE MARKET ALERTS
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

    for news in news_list[:8]:

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

        await asyncio.sleep(3)

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

{outlook}

🔥 <b>STOCKS IN FOCUS</b>

🟢 RVNL
🟢 BEL
🟢 SUZLON
🟢 IREDA
🔴 ITC

⚠️ <b>KEY MARKET TRIGGERS</b>

▪ RBI commentary
▪ Crude oil movement
▪ Corporate results
▪ Global market cues

━━━━━━━━━━━━━━
"""

    await send_telegram(msg)

# =========================================================
# SCHEDULER
# =========================================================

scheduler = AsyncIOScheduler(timezone=IST)

# 7 AM BRIEFING
scheduler.add_job(
    morning_briefing,
    "cron",
    hour=7,
    minute=0
)

# LIVE NEWS EVERY 5 MINUTES
scheduler.add_job(
    send_live_news,
    "interval",
    minutes=5
)

scheduler.start()

# =========================================================
# START BOT
# =========================================================

print("✅ AI Stock Market Bot Started")

asyncio.get_event_loop().run_forever()
