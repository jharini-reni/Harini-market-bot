# =========================================================
# PREMIUM INDIA MARKET TELEGRAM BOT
# FINAL PROFESSIONAL VERSION
# CLEAN FORMAT
# NO DUPLICATES
# INDIA MARKET NEWS ONLY
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

    "rvnl",
    "suzlon",
    "idea",
    "yes bank",
    "ireda",
    "iex",
    "bel",
    "itc",
    "coal india",
    "vedanta",
    "canara bank",
    "bank of baroda",
    "pnb",
    "wipro",
    "tatatech",
    "ola electric",
    "hfcl",
    "texrail",
    "inox wind",
    "mrpl",
    "jublfood"

]

# =========================================================
# IMPORTANT KEYWORDS
# =========================================================

IMPORTANT_KEYWORDS = [

    "results",
    "profit",
    "loss",
    "dividend",
    "order",
    "stake sale",
    "block deal",
    "fii",
    "fpi",
    "dii",
    "rbi",
    "nifty",
    "sensex",
    "bank nifty",
    "crude",
    "oil",
    "gold",
    "silver",
    "war",
    "iran",
    "middle east",
    "inflation",
    "fed"

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
    "brokerage",
    "technical view",
    "recommendation",
    "stock to buy",
    "expert suggests",
    "share price target",
    "investment strategy",
    "what's fueling",
    "what is fueling",
    "gmp",
    "ipo allotment",
    "mutual fund",

]

# =========================================================
# REMOVE RANDOM NEWS
# =========================================================

BLOCKED_NEWS = [

    "football",
    "cricket",
    "hollywood",
    "celebrity",
    "movie",
    "music",
    "entertainment",
    "bts",
    "gene therapy",

]

# =========================================================
# RSS FEEDS
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
            "parse_mode": "Markdown",
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

        "latest",
        "live",
        "today",
        "update",
        "updates",
        "q1",
        "q2",
        "q3",
        "q4",
        ":",
        "-",
        "|"

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
        "high",
        "order",
        "dividend"

    ]

    negative_words = [

        "loss",
        "fall",
        "drop",
        "war",
        "weak",
        "crash",
        "decline",
        "sell"

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
            "Company reported quarterly earnings with "
            "investors tracking margins, revenue growth "
            "and future business outlook closely."
        )

    if "loss" in title:

        return (
            "Weak earnings performance may impact "
            "investor sentiment and stock movement."
        )

    if "dividend" in title:

        return (
            "Dividend announcement may attract "
            "long-term and income-focused investors."
        )

    if "order" in title:

        return (
            "Fresh order inflow improves revenue "
            "visibility and future growth expectations."
        )

    if "fii" in title or "fpi" in title:

        return (
            "Foreign investor activity may influence "
            "overall market direction and volatility."
        )

    if "rbi" in title:

        return (
            "Banking and financial stocks may remain "
            "active after RBI commentary."
        )

    if "war" in title or "iran" in title:

        return (
            "Global tensions may increase market "
            "volatility and cautious sentiment."
        )

    if "crude" in title or "oil" in title:

        return (
            "Higher crude oil prices may pressure "
            "Indian markets and oil-sensitive sectors."
        )

    return (
        "Market participants are closely monitoring "
        "developments for sector impact."
    )

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

                title_lower = title.lower()

                if is_duplicate(title):
                    continue

                skip_article = any(
                    word in title_lower
                    for word in BLOCKED_WORDS
                )

                if skip_article:
                    continue

                skip_random = any(
                    word in title_lower
                    for word in BLOCKED_NEWS
                )

                if skip_random:
                    continue

                important = any(
                    keyword in title_lower
                    for keyword in IMPORTANT_KEYWORDS
                )

                watchlist = is_watchlist_news(title)

                if not important and not watchlist:
                    continue

                collected_news.append({

                    "title": title,

                    "source": feed.feed.get(
                        "title",
                        "News"
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
{sentiment} *{title}*

📌 {impact}

📰 Source: {source}

──────────────────────────────
"""

# =========================================================
# LIVE MARKET NEWS
# =========================================================

async def send_live_news():

    now = datetime.now(IST)

    if not (7 <= now.hour <= 23):
        return

    print("Checking News...")

    news_list = await fetch_news()

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

async def morning_briefing():

    today = datetime.now(IST).strftime("%d %b %Y")

    dow = get_change("^DJI")

    nasdaq = get_change("^IXIC")

    sp500 = get_change("^GSPC")

    nifty = get_change("^NSEI")

    banknifty = get_change("^NSEBANK")

    msg = f"""
🌅 *MORNING MARKET BRIEFING*
*{today} | 7:00 AM IST*

──────────────────────────────

📊 *GLOBAL MARKETS*

▪ Dow Jones : {dow}
▪ Nasdaq : {nasdaq}
▪ S&P 500 : {sp500}

──────────────────────────────

🇮🇳 *INDIAN MARKET SETUP*

▪ Nifty 50 : {nifty}
▪ Bank Nifty : {banknifty}

📌 Global cues indicate cautious to volatile market opening with investors tracking crude oil prices, FII activity and RBI commentary closely.

──────────────────────────────

🔥 *WATCHLIST STOCKS IN FOCUS*

🟢 RVNL – Railway stocks remain active

🟢 SUZLON – Renewable energy theme strong

🟢 BEL – Defence sector momentum continues

🟢 IREDA – Green energy stocks in focus

🟢 YES BANK – Banking sector active

🔴 ITC – FMCG sector may remain volatile

──────────────────────────────

⚠️ *KEY MARKET TRIGGERS*

▪ FII / DII Activity

▪ Corporate Results

▪ Crude Oil Movement

▪ RBI & Global Cues

▪ War / Geopolitical Updates

──────────────────────────────
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

print("✅ Premium India Market Bot Started")

asyncio.get_event_loop().run_forever()