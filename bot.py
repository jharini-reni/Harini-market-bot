import os
import asyncio
import httpx
from datetime import datetime
import pytz
import schedule
import time
import threading
import yfinance as yf

# Duplicate message prevention
SENT_NEWS_IDS = set()
STARTUP_SENT = False

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = pytz.timezone("Asia/Kolkata")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")  # Set in Railway env vars

STOCKS = {
    # NSE Listed
    "JUBLFOOD": "Jubilant FoodWorks",
    "IEX": "Indian Energy Exchange",
    "MRPL": "MRPL",
    "CANBK": "Canara Bank",
    "NIVABUPA": "Niva Bupa",
    "KALYANKJIL": "Kalyan Jewellers",
    "RVNL": "RVNL",
    "IDEA": "Vodafone Idea",
    "SUZLON": "Suzlon Energy",
    "INOXWIND": "Inox Wind",
    "COALINDIA": "Coal India",
    "VEDL": "Vedanta",
    "ITC": "ITC",
    "ITCHOTELS": "ITC Hotels",
    "DIACABS": "Diamond Cables",
    "BEL": "BEL",
    "REDINGTON": "Redington",
    "BANKBARODA": "Bank of Baroda",
    "PNB": "Punjab National Bank",
    "WIPRO": "Wipro",
    "HYUNDAI": "Hyundai India",
    "GEOJITFSL": "Geojit Financial",
    "IREDA": "IREDA",
    "TATATECH": "Tata Technologies",
    "YESBANK": "Yes Bank",
    "ETERNAL": "Eternal",
    "THANGAMAYIL": "Thangamayil Jewellery",
    "IDFCFIRSTB": "IDFC First Bank",
    "OLAELEC": "Ola Electric",
    "ATHENERGY": "Ather Energy",
    # ETFs
    "GOLDBEES": "GoldBees ETF",
    "SILVERBEES": "SilverBees ETF",
    "HDFCSILVER": "HDFC Silver ETF",
    "IDFCSILVER": "IDFC Silver ETF",
    # Unlisted / News only
    "GROWW": "Groww",
    "LENSKART": "Lenskart",
    "LGINDIA": "LG India",
    "SAMMANCAP": "Samman Capital",
}

NSE_SYMBOLS = {
    "JUBLFOOD": "JUBLFOOD.NS", "IEX": "IEX.NS", "MRPL": "MRPL.NS",
    "CANBK": "CANBK.NS", "KALYANKJIL": "KALYANKJIL.NS", "RVNL": "RVNL.NS",
    "IDEA": "IDEA.NS", "SUZLON": "SUZLON.NS", "INOXWIND": "INOXWIND.NS",
    "COALINDIA": "COALINDIA.NS", "VEDL": "VEDL.NS", "ITC": "ITC.NS",
    "ITCHOTELS": "ITCHOTELS.NS", "BEL": "BEL.NS", "REDINGTON": "REDINGTON.NS",
    "BANKBARODA": "BANKBARODA.NS", "PNB": "PNB.NS", "WIPRO": "WIPRO.NS",
    "HYUNDAI": "HYUNDAI.NS", "IREDA": "IREDA.NS", "TATATECH": "TATATECH.NS",
    "YESBANK": "YESBANK.NS", "IDFCFIRSTB": "IDFCFIRSTB.NS", "OLAELEC": "OLAELEC.NS",
    "GOLDBEES": "GOLDBEES.NS", "SILVERBEES": "SILVERBEES.NS",
    "HDFCSILVER": "HDFCSILVER.NS", "COALINDIA": "COALINDIA.NS",
    "NIVABUPA": "NIVABUPA.NS", "GEOJITFSL": "GEOJITFSL.NS",
    "DIACABS": "DIACABS.NS", "THANGAMAYIL": "THANGAMAYIL.NS",
    "ATHENERGY": "ATHENERGY.NS",
    # Indices
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "MIDCAP": "^NSEMDCP50",
    # Commodities
    "GOLD": "GC=F", "SILVER": "SI=F",
}


async def send_telegram(message: str):
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            await client.post(TELEGRAM_URL, json=payload, timeout=10)
        except Exception as e:
            print(f"Telegram error: {e}")


def get_price(symbol_key: str) -> str:
    yf_sym = NSE_SYMBOLS.get(symbol_key)
    if not yf_sym:
        return "N/A"
    try:
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period="1d", interval="1m")
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


async def fetch_news(query: str, count: int = 3) -> list[dict]:
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


def format_news_item(article: dict) -> str:
    title = article.get("title", "")
    source = article.get("source", {}).get("name", "Unknown")
    url = article.get("url", "")
    published = article.get("publishedAt", "")[:10]
    return f"▪{title}\n🔗 {source} | {published}\n{url}"


async def morning_briefing():
    now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p IST")
    msg = f"<b>🌅 MORNING MARKET BRIEFING</b>\n<b>{now}</b>\n{'─'*30}\n\n"

    # Indices
    msg += "<b>📊 KEY INDICES</b>\n"
    for name, key in [("Nifty 50", "NIFTY50"), ("Bank Nifty", "BANKNIFTY"), ("Midcap 50", "MIDCAP")]:
        price = get_price(key)
        msg += f"▪{name}: {price}\n"

    # Commodities
    msg += "\n<b>🪙 COMMODITIES</b>\n"
    msg += f"▪Gold: {get_price('GOLD')}\n"
    msg += f"▪Silver: {get_price('SILVER')}\n"

    # Top stock prices
    msg += "\n<b>📈 YOUR STOCKS SNAPSHOT</b>\n"
    listed = ["JUBLFOOD", "IEX", "CANBK", "RVNL", "SUZLON", "COALINDIA", "ITC", "WIPRO", "YESBANK", "BEL"]
    for s in listed:
        price = get_price(s)
        msg += f"▪{STOCKS[s]} ({s}): {price}\n"

    await send_telegram(msg)

    # Market news
    await asyncio.sleep(2)
    news_msg = "<b>📰 MORNING NEWS DIGEST</b>\n{'─'*30}\n\n"

    topics = [
        ("Indian stock market", "🇮🇳 INDIA MARKET"),
        ("RBI policy India", "🏦 RBI / ECONOMY"),
        ("Trump trade war market", "🌍 GLOBAL NEWS"),
        ("Gold Silver price today", "🥇 COMMODITIES NEWS"),
    ]

    for query, label in topics:
        articles = await fetch_news(query, 2)
        if articles:
            news_msg += f"<b>{label}</b>\n"
            for a in articles:
                news_msg += format_news_item(a) + "\n"
            news_msg += "\n"

    news_msg += "\n⚠️ <i>Unverified news shown in italics. Always check source.</i>"
    await send_telegram(news_msg)


async def market_update():
    now = datetime.now(IST).strftime("%I:%M %p")
    msg = f"<b>⚡ LIVE UPDATE | {now} IST</b>\n{'─'*30}\n\n"

    # Indices
    msg += "<b>📊 INDICES</b>\n"
    for name, key in [("Nifty 50", "NIFTY50"), ("Bank Nifty", "BANKNIFTY"), ("Midcap 50", "MIDCAP")]:
        msg += f"▪{name}: {get_price(key)}\n"

    # Commodities
    msg += "\n<b>🪙 GOLD & SILVER</b>\n"
    msg += f"▪Gold: {get_price('GOLD')}\n"
    msg += f"▪Silver: {get_price('SILVER')}\n"

    # Quick news
    articles = await fetch_news("India stock market NSE BSE", 2)
    if articles:
        msg += "\n<b>📰 LATEST NEWS</b>\n"
        for a in articles:
            msg += format_news_item(a) + "\n"

    await send_telegram(msg)


async def stock_news_update():
    """Send news for specific stocks every 30 mins"""
    now = datetime.now(IST).strftime("%I:%M %p")
    msg = f"<b>🔍 STOCK NEWS | {now} IST</b>\n{'─'*30}\n\n"

    watchlist = ["Jubilant FoodWorks", "Suzlon Energy", "Yes Bank", "Coal India", "Ather Energy", "Ola Electric", "LG India", "Thangamayil"]
    found = False
    for stock in watchlist:
        articles = await fetch_news(f"{stock} India news", 1)
        if articles:
            found = True
            msg += f"<b>▪{stock}</b>\n"
            msg += format_news_item(articles[0]) + "\n\n"

    if found:
        await send_telegram(msg)


def run_async(coro):
    asyncio.run(coro)


def setup_schedule():
    # Morning briefing at 7 AM IST
    schedule.every().day.at("07:00").do(lambda: run_async(morning_briefing()))

    # Market updates every 5 mins from 9:15 AM to 3:30 PM
    for h in range(9, 16):
        for m in range(0, 60, 5):
            if (h == 9 and m < 15) or (h == 15 and m > 30):
                continue
            t = f"{h:02d}:{m:02d}"
            schedule.every().day.at(t).do(lambda: run_async(market_update()))

    # Stock specific news every 30 mins
    schedule.every(30).minutes.do(lambda: run_async(stock_news_update()))


async def startup_message():
    global STARTUP_SENT
    if STARTUP_SENT:
        return
    STARTUP_SENT = True
    msg = (
        "✅ <b>India Market Bot STARTED!</b>\n\n"
        "▪Morning briefing: 7:00 AM daily\n"
        "▪Live updates: Every 5 mins (9:15 AM – 3:30 PM)\n"
        "▪Stock news: Every 30 mins\n"
        "▪Tracking: Nifty, Bank Nifty, Midcap + your stocks\n\n"
        "🚀 Bot is running 24/7!"
    )
    await send_telegram(msg)


if __name__ == "__main__":
    asyncio.run(startup_message())
    setup_schedule()
    print("Bot running...")
    while True:
        schedule.run_pending()
        time.sleep(30)