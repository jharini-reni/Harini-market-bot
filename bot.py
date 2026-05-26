# =========================================================
# PREMIUM INDIA STOCK MARKET TELEGRAM BOT
# NO DUPLICATES
# INDIA NEWS ONLY
# WATCHLIST PRIORITY
# MORNING MARKET SETUP
# LIVE IMPORTANT NEWS
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
# IMPORTANT MARKET KEYWORDS
# =========================================================

IMPORTANT_KEYWORDS = [

    "nifty",
    "sensex",
    "bank nifty",
    "gift nifty",

    "fii",
    "fpi",
    "dii",

    "rbi",
    "inflation",
    "repo rate",
    "fed",

    "crude",
    "oil",
    "gold",
    "silver",

    "iran",
    "war",
    "ukraine",
    "middle east",

    "results",
    "profit",
    "loss",
    "dividend",
    "order",
    "stake",
    "deal",
    "approval",
    "merger",
    "acquisition",

]

# =========================================================
# REMOVE RECOMMENDATION ARTICLES
# =========================================================

BLOCKED_WORDS = [

    "buy or sell",
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
    "brokerage",
    "technical view",
    "stock to buy",
    "expert suggests",
    "share price target",
    "investment strategy",
    "what's fueling",
    "what is fueling",

]

# =========================================================
# REMOVE RANDOM NEWS
# =========================================================

BLOCKED_NEWS = [

    "bts",
    "celebrity",
    "football",
    "cricket",
    "hollywood",
    "movie",
    "music awards",
    "gene therapy",
    "eli lilly",
    "meta",
    "ai datacentre",
    "entertainment",

]

# =========================================================
# TRUSTED INDIA MARKET SOURCES
# =========================================================

RSS_FEEDS = [

    "https://www.moneycontrol.com/rss/business.xml",

    "https://www.moneycontrol.com/rss/MCtopnews.xml",

    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",

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
# CLEAN TITLE
# =========================================================

def clean_title(title):

    title = title.lower()

    remove_words = [

        "live",
        "latest",
        "today",
        "update",
        "updates",
        "q1",
        "q2",
        "q3",
        "q4",
        ":",
        "-",
        "|",
        "?",
        ",",

    ]

    for word in remove_words:

        title = title.replace(word, "")

    return " ".join(title.split())

# =========================================================
# DUPLICATE FILTER
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
# WATCHLIST CHECK
# =========================================================

def is_watchlist_news(title):

    title = title.lower()

    for stock in WATCHLIST:

        if stock in title:
            return True

    return False

# =========================================================
# SENTIMENT
# =========================================================

def get_sentiment(title):

    title = title.lower()

    positive_words = [

        "profit",
        "surge",
        "rise",
        "gain",
        "approval",
        "growth",
        "strong",
        "high",
        "order",
        "dividend",

    ]

    negative_words = [

        "loss",
        "fall",
        "drop",
        "war",
        "weak",
        "crash",
        "decline",
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
# SMART MARKET IMPACT
# =========================================================

def market_impact(title):

    title = title.lower()

    if "results" in title or "profit" in title:

        return (
            "Company announced quarterly earnings with "
            "investors closely tracking profit growth, "
            "revenue performance and future outlook."
        )

    if "loss" in title:

        return (
            "Weak financial performance may impact "
            "investor sentiment and stock movement."
        )

    if "dividend" in title:

        return (
            "Dividend announcement may attract "
            "long-term and income-focused investors."
        )

    if "order" in title:

        return (
            "Fresh order inflow improves business "
            "visibility and future revenue expectations."
        )

    if "fii" in title or "fpi" in title:

        return (
            "Foreign investor activity may influence "
            "overall market direction and volatility."
        )

    if "rbi" in title:

        return (
            "Banking and financial stocks may remain "
            "active based on RBI commentary."
        )

    if "war" in title or "iran" in title:

        return (
            "Geopolitical tensions may increase global "
            "market volatility and cautious sentiment."
        )

    if "crude" in title or "oil" in title:

        return (
            "Higher crude oil prices may pressure "
            "Indian markets and oil-sensitive sectors."
        )

    if "gold" in title:

        return (
            "Gold-related stocks and ETFs may stay "
            "active amid safe-haven buying."
        )

    if "silver" in title:

        return (
            "Silver ETFs may remain volatile due "
            "to metal price fluctuations."
        )

    return (
        "Market participants are closely monitoring "
        "developments for sector impact."
    )

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
# MARKET OUTLOOK
# =========================================================

def market_prediction():

    try:

        dow = yf.Ticker("^DJI").history(period="2d")

        nasdaq = yf.Ticker("^IXIC").history(period="2d")

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
                "🟢 Positive global cues may support "
                "a stronger Indian market opening."
            )

        elif dow_change < -0.5:

            return (
                "🔴 Weak global sentiment may keep "
                "Indian markets under pressure."
            )

        return (
            "⚪ Flat to volatile opening expected "
            "with focus on global cues."
        )

    except:

        return "⚪ Market outlook unavailable."

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

                skip_article = any(
                    word in title_lower
                    for word in BLOCKED_WORDS
                )

                if skip_article:
                    continue

                skip_random_news = any(
                    word in title_lower
                    for word in BLOCKED_NEWS
                )

                if skip_random_news:
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

━━━━━━━━━━━━━━━
"""

# =========================================================
# LIVE MARKET NEWS
# =========================================================

async def send_live_news():

    now = datetime.now(IST)

    # MARKET HOURS ONLY

    if not (7 <= now.hour <= 23):
        return

    print("Checking News...")

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

━━━━━━━━━━━━━━━

📊 <b>GLOBAL MARKETS</b>

▪ Dow Jones : {dow}

▪ Nasdaq : {nasdaq}

▪ S&P 500 : {sp500}

━━━━━━━━━━━━━━━

🇮🇳 <b>NIFTY OUTLOOK</b>

▪ Nifty : {nifty}

📌 {outlook}

━━━━━━━━━━━━━━━

🔥 <b>WATCHLIST IN FOCUS</b>

🟢 RVNL
🟢 SUZLON
🟢 BEL
🟢 IREDA
🟢 YES BANK
🟢 IEX
🔴 ITC

━━━━━━━━━━━━━━━

⚠️ <b>KEY MARKET TRIGGERS</b>

▪ FII / DII Activity

▪ RBI Commentary

▪ Crude Oil Prices

▪ Corporate Results

▪ Global Market Cues

━━━━━━━━━━━━━━━
"""

    await send_telegram(msg)

# =========================================================
# SCHEDULER
# =========================================================

scheduler = AsyncIOScheduler(timezone=IST)

# MORNING 7 AM MESSAGE

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

print("✅ Premium India Market Bot Started")

asyncio.get_event_loop().run_forever()