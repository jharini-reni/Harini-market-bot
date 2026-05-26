# =========================================================
# AI TELEGRAM STOCK MARKET BOT
# FINAL PREMIUM VERSION
# INDIA MARKET PRIORITY
# NO DUPLICATES
# IMPORTANT NEWS ONLY
# PROFESSIONAL MARKET SUMMARIES
# LIVE NEWS EVERY 1 MINUTE
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
# WATCHLIST
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
# IMPORTANT KEYWORDS
# =========================================================

IMPORTANT_KEYWORDS = [

    "fii",
    "fpi",
    "dii",
    "war",
    "iran",
    "russia",
    "ukraine",
    "middle east",
    "rbi",
    "fed",
    "nifty",
    "sensex",
    "bank nifty",
    "crude",
    "oil",
    "inflation",
    "market",
    "stocks",
    "results",
    "profit",
    "loss",
    "dividend",
    "order",
    "railway",
    "defence",
    "ipo",
    "india",
    "tariff",

]

# =========================================================
# BLOCKED ARTICLES
# =========================================================

BLOCKED_WORDS = [

    "buy or sell",
    "what's fueling",
    "what is fueling",
    "target price",
    "should you buy",
    "top stocks",
    "best stocks",
    "multibagger",
    "how to",
    "step-by-step",
    "ipo allotment",
    "gmp",
    "mutual fund",
    "long term",
    "brokerage",
    "recommendation",
    "technical view",
    "stock to buy",
    "expert suggests",
    "share price target",
    "check status",
    "5 stocks",
    "small-cap stock",
    "blue-chip stocks",
    "stocks to watch",
    "trading idea",
    "investment strategy",

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

            print("Telegram:", response.status_code)

        except Exception as e:

            print("Telegram Error:", e)

# =========================================================
# CLEAN TITLE
# =========================================================

def clean_title(title):

    title = title.lower()

    remove_words = [

        "live",
        "latest",
        "today",
        "updates",
        "update",
        "q1",
        "q2",
        "q3",
        "q4",
        ":",
        "-",
        "|",
        "?",
        ",",
        "share price",
        "stock price",

    ]

    for word in remove_words:

        title = title.replace(word, "")

    return " ".join(title.split())

# =========================================================
# ULTRA DUPLICATE FILTER
# =========================================================

def is_duplicate(title):

    cleaned = clean_title(title)

    for old in SENT_NEWS:

        similarity = fuzz.token_set_ratio(
            cleaned,
            old
        )

        if similarity > 65:
            return True

    SENT_NEWS.append(cleaned)

    if len(SENT_NEWS) > 5000:
        SENT_NEWS.pop(0)

    return False

# =========================================================
# SENTIMENT ENGINE
# =========================================================

def get_sentiment(title):

    title = title.lower()

    positive_words = [

        "surge",
        "gain",
        "rise",
        "profit",
        "approval",
        "growth",
        "strong",
        "high",
        "record",
        "buy",
        "up",
        "order",
        "dividend",

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
# MARKET IMPACT
# =========================================================

def market_impact(title):

    title = title.lower()

    if "profit" in title or "results" in title:

        return (
            "Quarterly earnings announced with investors "
            "closely tracking revenue growth, margins and "
            "management commentary for future outlook."
        )

    if "loss" in title:

        return (
            "Weak earnings performance may impact investor "
            "sentiment and create pressure on the stock."
        )

    if "dividend" in title:

        return (
            "Dividend announcement may attract interest from "
            "income-focused and long-term investors."
        )

    if "order" in title:

        return (
            "New order inflow improves business visibility "
            "and may support future revenue growth."
        )

    if "fii" in title or "fpi" in title:

        return (
            "Foreign investor activity may influence broader "
            "market direction and sector sentiment."
        )

    if "rbi" in title:

        return (
            "Banking and financial stocks may remain active "
            "based on RBI commentary and policy outlook."
        )

    if "war" in title or "iran" in title:

        return (
            "Rising geopolitical tensions may increase global "
            "market volatility and risk-off sentiment."
        )

    if "crude" in title or "oil" in title:

        return (
            "Higher crude oil prices may pressure Indian "
            "markets and oil-sensitive sectors."
        )

    if "gold" in title:

        return (
            "Gold-related stocks and ETFs may stay active "
            "amid safe-haven buying interest."
        )

    if "silver" in title:

        return (
            "Silver ETFs and metal-related counters may "
            "remain volatile due to price fluctuations."
        )

    if "railway" in title:

        return (
            "Railway sector stocks may stay in focus amid "
            "continued infrastructure spending."
        )

    return (
        "Market participants are closely monitoring "
        "developments for potential sector impact."
    )

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
                "🟢 Indian markets may open positive supported "
                "by strong global cues and improved risk sentiment."
            )

        elif dow_change < -0.5 or sp_change < -0.5:

            return (
                "🔴 Weak opening possible due to negative global "
                "sentiment and cautious investor positioning."
            )

        return (
            "⚪ Flat to volatile opening expected with traders "
            "tracking global and domestic triggers."
        )

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
# WATCHLIST NEWS
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

                skip_news = any(
                    word in title_lower
                    for word in BLOCKED_WORDS
                )

                if skip_news:
                    continue

                important_news = any(
                    keyword in title_lower
                    for keyword in IMPORTANT_KEYWORDS
                )

                watchlist_news = is_watchlist_news(title)

                if not important_news and not watchlist_news:
                    continue

                collected_news.append({

                    "title": title,

                    "source": feed.feed.get(
                        "title",
                        "News"
                    ),

                    "priority": (
                        watchlist_news or important_news
                    )

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
# LIVE NEWS
# =========================================================

async def send_live_news():

    now = datetime.now(IST)

    if not (8 <= now.hour <= 16):
        return

    print("Checking Market News...")

    news_list = await fetch_news()

    news_list = sorted(
        news_list,
        key=lambda x: x["priority"],
        reverse=True
    )

    for news in news_list[:5]:

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
# MORNING BRIEFING
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

scheduler.add_job(
    morning_briefing,
    "cron",
    hour=7,
    minute=0
)

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