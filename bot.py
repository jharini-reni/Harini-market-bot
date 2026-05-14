import os
import asyncio
import httpx
from datetime import datetime
import pytz
import schedule
import time
import yfinance as yf
import hashlib
import feedparser
import re

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = pytz.timezone("Asia/Kolkata")

SENT_IDS = set()

# FREE UNLIMITED RSS FEEDS - No API limit
RSS_FEEDS = [
    ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "Economic Times"),
    ("https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms", "Economic Times"),
    ("https://www.moneycontrol.com/rss/MCtopnews.xml", "Moneycontrol"),
    ("https://www.livemint.com/rss/markets", "LiveMint"),
    ("https://feeds.feedburner.com/ndtvprofit-latest", "NDTV Profit"),
    ("https://www.business-standard.com/rss/markets-106.rss", "Business Standard"),
    ("https://www.thehindu.com/business/markets/feeder/default.rss", "The Hindu Business"),
    ("https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "ET Economy"),
    ("https://www.business-standard.com/rss/economy-policy-101.rss", "BS Economy"),
    ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "CNBC"),
    ("https://www.investing.com/rss/news.rss", "Investing.com"),
]

MY_STOCKS = [
    "jubilant foodworks", "jublfood", "iex", "indian energy exchange",
    "mrpl", "canara bank", "canbk", "niva bupa", "kalyan jewellers",
    "kalyankjil", "rvnl", "rail vikas", "vodafone idea",
    "suzlon", "inox wind", "inoxwind", "coal india", "coalindia",
    "vedanta", "vedl", "itc ltd", "itc hotel",
    "bel ", "bharat electronics", "redington",
    "bank of baroda", "bankbaroda", "punjab national bank", "pnb ",
    "wipro", "hyundai india", "ireda", "tata technologies", "tatatech",
    "yes bank", "yesbank", "idfc first", "idfcfirstb",
    "ola electric", "olaelec", "ather energy", "thangamayil",
    "geojit", "goldbees", "silverbees", "hdfc silver",
    "lg india", "groww", "lenskart", "samman capital",
    "embassy reit", "lemon tree", "eternal ",
    "diamond cable", "diacabs", "niva bupa",
    "inox wind", "kalyan jewellers"
]

IMPORTANT_KEYWORDS = [
    "gift nifty", "sgx nifty", "dow jones", "nasdaq", "s&p 500",
    "wall street", "us market", "federal reserve", "us fed",
    "rbi ", "repo rate", "inflation", "crude oil", "brent crude",
    "trump", "modi ", "sebi ", "nifty 50", "sensex", "bank nifty",
    "fii", "dii", "foreign investor", "rupee", "dollar index",
    "rate cut", "rate hike", "gdp", "forex reserve",
    "war ", "iran", "russia", "ukraine", "china economy",
    "gold price", "silver price", "oil price", "opec",
    "west asia", "middle east", "global market", "asian market",
    "ipo ", "quarterly result", "q4 result", "q1 result",
    "rbi policy", "monetary policy", "interest rate",
    "market rally", "market crash", "bull run", "bear market",
    "trade war", "tariff", "sanctions", "geopolitical"
]

SKIP_KEYWORDS = [
    "cricket", "ipl", "bollywood", "film", "movie", "actor",
    "recipe", "fashion", "lifestyle", "horoscope", "astrology",
    "football", "tennis", "hockey", "weather", "tourism", "travel",
    "health tips", "diet", "greystone", "microvast", "canada election",
    "australia election", "uk election"
]

NSE_SYMBOLS = {
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "MIDCAP": "^NSEMDCP50",
    "GOLD": "GC=F", "SILVER": "SI=F",
    "SUZLON": "SUZLON.NS", "YESBANK": "YESBANK.NS", "IDEA": "IDEA.NS",
    "RVNL": "RVNL.NS", "OLAELEC": "OLAELEC.NS", "COALINDIA": "COALINDIA.NS",
    "ITC": "ITC.NS", "CANBK": "CANBK.NS", "IREDA": "IREDA.NS",
    "WIPRO": "WIPRO.NS", "BEL": "BEL.NS", "VEDL": "VEDL.NS",
    "JUBLFOOD": "JUBLFOOD.NS", "PNB": "PNB.NS", "BANKBARODA": "BANKBARODA.NS",
    "INOXWIND": "INOXWIND.NS", "KALYANKJIL": "KALYANKJIL.NS",
    "TATATECH": "TATATECH.NS", "THANGAMAYIL": "THANGAMAYIL.NS",
}


async def send_telegram(message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(TELEGRAM_URL, json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=10)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Telegram error: {e}")


def get_id(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()


def clean_text(text: str) -> str:
    text = re.sub('<[^<]+?>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_price(symbol_key: str) -> str:
    yf_sym = NSE_SYMBOLS.get(symbol_key)
    if not yf_sym:
        return "N/A"
    try:
        hist = yf.Ticker(yf_sym).history(period="1d", interval="5m")
        if hist.empty:
            return "N/A"
        price = hist["Close"].iloc[-1]
        open_p = hist["Open"].iloc[0]
        pct = ((price - open_p) / open_p) * 100
        arrow = "🟢" if pct >= 0 else "🔴"
        return f"{arrow} ₹{price:.2f} ({pct:+.2f}%)"
    except:
        return "N/A"


def is_my_stock(title: str) -> bool:
    t = title.lower()
    return any(s in t for s in MY_STOCKS)


def is_important(title: str) -> bool:
    t = title.lower()
    if any(skip in t for skip in SKIP_KEYWORDS):
        return False
    return any(kw in t for kw in IMPORTANT_KEYWORDS)


def classify_sentiment(title: str, summary: str = "") -> str:
    t = (title + " " + summary).lower()
    strong_pos = [
        "wins order", "bags order", "new order", "profit rises",
        "revenue up", "strong growth", "buy rating", "upgrade to buy",
        "mou signed", "receives approval", "record high profit",
        "dividend declared", "bonus shares", "capacity expansion",
        "new contract", "order inflow", "stake acquisition"
    ]
    strong_neg = [
        "promoter selling", "fraud detected", "sebi action",
        "loss widens", "revenue falls", "profit declines",
        "downgrade to sell", "penalty imposed", "default",
        "debt concern", "margin pressure", "earnings miss",
        "ceo resignation", "regulatory action", "ban imposed"
    ]
    if any(p in t for p in strong_pos):
        return "positive"
    if any(n in t for n in strong_neg):
        return "negative"
    return "neutral"


def build_news_item(title: str, summary: str, source: str) -> str:
    title = clean_text(title).strip()
    summary = clean_text(summary).strip()
    context = ""
    if summary and len(summary) > 30:
        context = summary[:160]
        if len(summary) > 160:
            context += "..."
        if context.lower()[:60] == title.lower()[:60]:
            context = ""
    item = f"▪️<b>{title}</b>"
    if context:
        item += f"\n{context}"
    item += f"\n<i>Source: {source}</i>"
    return item


async def fetch_and_send_news():
    global SENT_IDS
    market_cues = []
    positive_stocks = []
    negative_stocks = []
    neutral_stocks = []

    for feed_url, source in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "") or entry.get("description", "")
                if not title or len(title) < 10:
                    continue
                nid = get_id(title)
                if nid in SENT_IDS:
                    continue
                SENT_IDS.add(nid)
                sentiment = classify_sentiment(title, summary)
                item = build_news_item(title, summary, source)
                if is_my_stock(title):
                    if sentiment == "positive":
                        positive_stocks.append(item)
                    elif sentiment == "negative":
                        negative_stocks.append(item)
                    else:
                        neutral_stocks.append(item)
                elif is_important(title):
                    market_cues.append(item)
        except Exception as e:
            print(f"RSS error {source}: {e}")

    if not market_cues and not positive_stocks and not negative_stocks and not neutral_stocks:
        print("No new news")
        return

    now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p IST")
    msg = f"📊 <b>MARKET UPDATE</b>\n<b>{now}</b>\n{'─'*30}\n\n"

    if market_cues:
        msg += "<b>🌍 MARKET CUES</b>\n\n"
        for item in market_cues[:5]:
            msg += f"{item}\n\n"

    if positive_stocks:
        msg += "<b>🟢 Positive Sentiment Stocks</b>\n\n"
        for item in positive_stocks[:5]:
            msg += f"{item}\n\n"

    if negative_stocks:
        msg += "<b>🔴 Negative Sentiment Stocks</b>\n\n"
        for item in negative_stocks[:4]:
            msg += f"{item}\n\n"

    if neutral_stocks:
        msg += "<b>⚪ Stocks To Watch</b>\n\n"
        for item in neutral_stocks[:4]:
            msg += f"{item}\n\n"

    await send_telegram(msg)

    if len(SENT_IDS) > 2000:
        SENT_IDS = set(list(SENT_IDS)[-1000:])


async def morning_briefing():
    now = datetime.now(IST).strftime("%d %b %Y")
    msg = f"🌅 <b>GOOD MORNING — MARKET BRIEFING</b>\n<b>{now} | 7:00 AM IST</b>\n{'─'*30}\n\n"
    msg += "<b>📊 KEY INDICES</b>\n"
    for name, key in [("Nifty 50","NIFTY50"),("Bank Nifty","BANKNIFTY"),("Midcap 50","MIDCAP")]:
        msg += f"▪️{name}: {get_price(key)}\n"
    msg += "\n<b>🪙 COMMODITIES</b>\n"
    msg += f"▪️Gold: {get_price('GOLD')}\n"
    msg += f"▪️Silver: {get_price('SILVER')}\n"
    msg += "\n<b>📈 YOUR STOCKS SNAPSHOT</b>\n"
    for s in ["SUZLON","YESBANK","IDEA","RVNL","COALINDIA","ITC",
              "CANBK","IREDA","WIPRO","BEL","VEDL","JUBLFOOD",
              "PNB","BANKBARODA","INOXWIND","KALYANKJIL","TATATECH"]:
        msg += f"▪️{s}: {get_price(s)}\n"
    await send_telegram(msg)
    await asyncio.sleep(3)
    await fetch_and_send_news()


def run_async(coro):
    asyncio.run(coro)


if __name__ == "__main__":
    print("✅ Bot started — Professional Market Alerts 24/7!")
    schedule.every().day.at("07:00").do(lambda: run_async(morning_briefing()))
    schedule.every(15).minutes.do(lambda: run_async(fetch_and_send_news()))
    asyncio.run(fetch_and_send_news())
    while True:
        schedule.run_pending()
        time.sleep(60)
