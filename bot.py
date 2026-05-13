import os
import asyncio
import httpx
from datetime import datetime
import pytz
import schedule
import time
import yfinance as yf
import hashlib

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = pytz.timezone("Asia/Kolkata")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Duplicate prevention - store sent news IDs
SENT_IDS = set()

STOCKS = [
    "Jubilant FoodWorks", "Indian Energy Exchange", "MRPL", "Canara Bank",
    "Niva Bupa", "Kalyan Jewellers", "RVNL", "Vodafone Idea", "Suzlon Energy",
    "Inox Wind", "Coal India", "Vedanta", "ITC", "ITC Hotels", "Diamond Cables",
    "BEL", "Redington", "Bank of Baroda", "Punjab National Bank", "Wipro",
    "Hyundai India", "IREDA", "Tata Technologies", "Yes Bank", "IDFC First Bank",
    "Ola Electric", "Ather Energy", "Thangamayil Jewellery", "Geojit Financial",
    "GoldBees", "SilverBees", "Gold ETF", "Silver ETF",
    "LG India", "Groww", "Lenskart", "Samman Capital"
]

NSE_SYMBOLS = {
    "JUBLFOOD": "JUBLFOOD.NS", "IEX": "IEX.NS", "MRPL": "MRPL.NS",
    "CANBK": "CANBK.NS", "KALYANKJIL": "KALYANKJIL.NS", "RVNL": "RVNL.NS",
    "IDEA": "IDEA.NS", "SUZLON": "SUZLON.NS", "INOXWIND": "INOXWIND.NS",
    "COALINDIA": "COALINDIA.NS", "VEDL": "VEDL.NS", "ITC": "ITC.NS",
    "BEL": "BEL.NS", "BANKBARODA": "BANKBARODA.NS", "PNB": "PNB.NS",
    "WIPRO": "WIPRO.NS", "IREDA": "IREDA.NS", "TATATECH": "TATATECH.NS",
    "YESBANK": "YESBANK.NS", "IDFCFIRSTB": "IDFCFIRSTB.NS",
    "OLAELEC": "OLAELEC.NS", "GOLDBEES": "GOLDBEES.NS",
    "SILVERBEES": "SILVERBEES.NS", "THANGAMAYIL": "THANGAMAYIL.NS",
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "MIDCAP": "^NSEMDCP50",
    "GOLD": "GC=F", "SILVER": "SI=F",
}

NEWS_TOPICS = [
    ("Indian stock market NSE BSE", "🇮🇳 INDIA MARKET"),
    ("RBI policy economy India", "🏦 RBI / ECONOMY"),
    ("Trump trade war global market", "🌍 GLOBAL NEWS"),
    ("Gold Silver price India", "🥇 GOLD & SILVER"),
    ("Nifty Bank Nifty sensex today", "📊 INDICES"),
    ("Suzlon Ola Electric Ather Energy news", "⚡ YOUR STOCKS"),
    ("Yes Bank IDFC Canara Bank news", "🏦 BANKING STOCKS"),
    ("Coal India Vedanta ITC news", "🏭 PSU & FMCG"),
    ("Modi economy policy India", "🇮🇳 INDIA POLICY"),
    ("war Ukraine Russia China market impact", "⚔️ GEOPOLITICAL"),
]


async def send_telegram(message: str):
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            await client.post(TELEGRAM_URL, json=payload, timeout=10)
            await asyncio.sleep(0.5)  # Avoid telegram rate limit
        except Exception as e:
            print(f"Telegram error: {e}")


def get_news_id(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()


async def fetch_news(query: str, count: int = 3) -> list:
    if not NEWS_API_KEY:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": count,
        "apiKey": NEWS_API_KEY,
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, timeout=10)
            data = r.json()
            return data.get("articles", [])
    except:
        return []


def get_price(symbol_key: str) -> str:
    yf_sym = NSE_SYMBOLS.get(symbol_key)
    if not yf_sym:
        return "N/A"
    try:
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1d", interval="5m")
        if hist.empty:
            return "N/A"
        price = hist["Close"].iloc[-1]
        open_price = hist["Open"].iloc[0]
        change = price - open_price
        pct = (change / open_price) * 100
        arrow = "🟢" if change >= 0 else "🔴"
        return f"{arrow} ₹{price:.2f} ({pct:+.2f}%)"
    except:
        return "N/A"


async def send_live_news():
    """Runs every 10 mins — sends only NEW news, no duplicates"""
    global SENT_IDS
    found_any = False

    for query, label in NEWS_TOPICS:
        articles = await fetch_news(query, 3)
        new_articles = []

        for a in articles:
            news_id = get_news_id(a.get("title", ""))
            if news_id not in SENT_IDS:
                SENT_IDS.add(news_id)
                new_articles.append(a)

        if new_articles:
            found_any = True
            now = datetime.now(IST).strftime("%I:%M %p")
            msg = f"<b>{label} | {now} IST</b>\n{'─'*25}\n\n"
            for a in new_articles:
                title = a.get("title", "")
                source = a.get("source", {}).get("name", "Unknown")
                url = a.get("url", "")
                published = a.get("publishedAt", "")[:10]
                msg += f"▪{title}\n🔗 {source} | {published}\n{url}\n\n"
            await send_telegram(msg)

    # Keep SENT_IDS from growing too large
    if len(SENT_IDS) > 1000:
        SENT_IDS = set(list(SENT_IDS)[-500:])


async def morning_briefing():
    """7 AM full briefing"""
    now = datetime.now(IST).strftime("%d %b %Y")
    msg = f"🌅 <b>MORNING MARKET BRIEFING</b>\n<b>{now} | 7:00 AM IST</b>\n{'─'*25}\n\n"

    # Indices
    msg += "<b>📊 KEY INDICES</b>\n"
    for name, key in [("Nifty 50", "NIFTY50"), ("Bank Nifty", "BANKNIFTY"), ("Midcap 50", "MIDCAP")]:
        msg += f"▪{name}: {get_price(key)}\n"

    # Commodities
    msg += "\n<b>🪙 GOLD & SILVER</b>\n"
    msg += f"▪Gold: {get_price('GOLD')}\n"
    msg += f"▪Silver: {get_price('SILVER')}\n"

    # Focus stocks today
    msg += "\n<b>🔍 FOCUS STOCKS TODAY</b>\n"
    focus = ["SUZLON", "YESBANK", "IDEA", "RVNL", "OLAELEC", "COALINDIA", "ITC", "CANBK"]
    for s in focus:
        msg += f"▪{s}: {get_price(s)}\n"

    await send_telegram(msg)

    # Morning news digest
    await asyncio.sleep(2)
    news_msg = f"📰 <b>MORNING NEWS DIGEST | {now}</b>\n{'─'*25}\n\n"

    for query, label in NEWS_TOPICS[:6]:
        articles = await fetch_news(query, 2)
        if articles:
            news_msg += f"<b>{label}</b>\n"
            for a in articles:
                title = a.get("title", "")
                source = a.get("source", {}).get("name", "")
                url = a.get("url", "")
                news_id = get_news_id(title)
                SENT_IDS.add(news_id)
                news_msg += f"▪{title}\n🔗 {source}\n{url}\n\n"

    await send_telegram(news_msg)


def run_async(coro):
    asyncio.run(coro)


def setup_schedule():
    # 7 AM morning briefing
    schedule.every().day.at("07:00").do(lambda: run_async(morning_briefing()))

    # Live news every 10 mins — 24/7
    schedule.every(10).minutes.do(lambda: run_async(send_live_news()))


if __name__ == "__main__":
    print("Bot started!")
    setup_schedule()
    # Run news immediately on start
    asyncio.run(send_live_news())
    while True:
        schedule.run_pending()
        time.sleep(60)
