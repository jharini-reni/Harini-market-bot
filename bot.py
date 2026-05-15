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
LAST_BRIEFING_DATE = None

RSS_FEEDS = [
    ("https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "Economic Times"),
    ("https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms", "Economic Times"),
    ("https://www.moneycontrol.com/rss/MCtopnews.xml", "Moneycontrol"),
    ("https://www.livemint.com/rss/markets", "LiveMint"),
    ("https://feeds.feedburner.com/ndtvprofit-latest", "NDTV Profit"),
    ("https://www.business-standard.com/rss/markets-106.rss", "Business Standard"),
    ("https://www.thehindu.com/business/markets/feeder/default.rss", "The Hindu Business"),
    ("https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms", "ET Economy"),
    ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "CNBC"),
]

MY_STOCKS = [
    "jubilant foodworks", "jublfood", "iex", "indian energy exchange",
    "mrpl", "canara bank", "canbk", "niva bupa", "kalyan jewellers",
    "kalyankjil", "rvnl", "rail vikas", "vodafone idea",
    "suzlon", "inox wind", "inoxwind", "coal india", "coalindia",
    "vedanta", "vedl", "itc ltd", "itc hotel", "itc shares",
    "bel ", "bharat electronics", "redington",
    "bank of baroda", "bankbaroda", "punjab national bank", "pnb ",
    "wipro", "hyundai india", "ireda", "tata technologies", "tatatech",
    "yes bank", "yesbank", "idfc first", "idfcfirstb",
    "ola electric", "olaelec", "ather energy", "thangamayil",
    "geojit", "goldbees", "silverbees", "hdfc silver",
    "lg india", "groww", "lenskart", "samman capital",
    "embassy reit", "lemon tree", "eternal ",
    "diamond cable", "diacabs", "inox wind", "kalyan jewellers"
]

INDIA_KEYWORDS = [
    "nifty", "sensex", "bank nifty", "gift nifty", "sgx nifty",
    "rbi", "sebi", "rupee", "bse", "nse", "india market",
    "indian stock", "fii", "dii", "repo rate", "inflation india",
    "modi", "budget india", "gdp india", "ipo india", "dalal street"
]

GLOBAL_KEYWORDS = [
    "dow jones", "nasdaq", "s&p 500", "wall street", "us fed",
    "federal reserve", "crude oil", "brent", "gold price", "silver price",
    "trump tariff", "trade war", "iran", "russia ukraine",
    "china economy", "global recession", "interest rate", "opec",
    "west asia", "middle east", "geopolitical"
]

SKIP_KEYWORDS = [
    "cricket", "ipl", "bollywood", "film", "movie", "actor",
    "recipe", "fashion", "lifestyle", "horoscope", "astrology",
    "football", "tennis", "hockey", "weather", "tourism",
    "health tips", "diet", "greystone", "microvast",
    "canada election", "australia election", "uk politics"
]

# Smart financial sentiment rules
STRONG_POSITIVE = [
    "wins order", "bags order", "new order worth", "order inflow",
    "profit jumps", "profit rises", "revenue surges", "strong growth",
    "upgraded to buy", "initiates buy", "target price raised",
    "mou signed", "receives approval", "rbi approval",
    "dividend declared", "bonus shares", "stock split",
    "capacity expansion", "new contract", "fresh order",
    "record high profit", "beat estimates", "better than expected",
    "stake acquisition", "promoter buying", "fii buying",
    "rate cut", "repo rate cut", "dovish", "market rally",
    "sensex rises", "nifty gains", "gift nifty positive",
    "dow gains", "nasdaq up", "us market rises"
]

STRONG_NEGATIVE = [
    "promoter selling", "promoter stake sale",
    "fraud detected", "sebi ban", "sebi penalty", "sebi action",
    "loss widens", "revenue falls", "profit declines", "misses estimates",
    "downgraded to sell", "target cut", "price target reduced",
    "penalty imposed", "default risk", "debt restructuring",
    "ceo resignation", "md quits", "regulatory action",
    "earnings miss", "margin pressure", "below expectations",
    "fii selling", "market crash", "sensex falls", "nifty drops",
    "rate hike", "hawkish", "recession fears",
    "war escalation", "oil price surge", "rupee falls record low"
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


def get_sentiment(title: str, summary: str = "") -> tuple:
    """Smart rule-based sentiment with reason"""
    t = (title + " " + summary).lower()

    for phrase in STRONG_POSITIVE:
        if phrase in t:
            reason = {
                "wins order": "New order win — revenue visibility improves",
                "bags order": "Order bagged — positive for earnings",
                "new order worth": "Fresh order — topline growth expected",
                "profit jumps": "Strong profit growth — bullish signal",
                "profit rises": "Profit rising — positive earnings trend",
                "revenue surges": "Revenue surge — strong business momentum",
                "upgraded to buy": "Analyst upgrade — institutional confidence",
                "initiates buy": "New buy recommendation — positive outlook",
                "target price raised": "Target raised — analysts see upside",
                "mou signed": "MoU signed — future business secured",
                "receives approval": "Regulatory approval — removes uncertainty",
                "rbi approval": "RBI approved — business expansion cleared",
                "dividend declared": "Dividend declared — rewards shareholders",
                "bonus shares": "Bonus shares — positive for retail investors",
                "rate cut": "Rate cut — boosts market liquidity & sentiment",
                "repo rate cut": "RBI rate cut — positive for banking & markets",
                "market rally": "Market rally — broad buying interest",
                "sensex rises": "Sensex up — positive market open expected",
                "nifty gains": "Nifty gaining — bullish momentum",
                "gift nifty positive": "GIFT Nifty positive — green opening expected",
                "dow gains": "Dow up — positive global cues for India",
                "nasdaq up": "Nasdaq rising — IT stocks may benefit",
                "promoter buying": "Promoter buying — insider confidence signal",
                "fii buying": "FII inflows — foreign confidence in India market",
            }.get(phrase, "Positive development for the stock")
            return "positive", reason

    for phrase in STRONG_NEGATIVE:
        if phrase in t:
            reason = {
                "promoter selling": "Promoter selling stake — insider exit signal ⚠️",
                "fraud detected": "Fraud detected — high risk, avoid ⚠️",
                "sebi ban": "SEBI ban — regulatory risk, negative ⚠️",
                "sebi penalty": "SEBI penalty — compliance concern ⚠️",
                "loss widens": "Loss widening — fundamentals weak ⚠️",
                "revenue falls": "Revenue declining — business slowdown ⚠️",
                "profit declines": "Profit falling — negative earnings trend ⚠️",
                "downgraded to sell": "Analyst downgrade — institutional exit signal ⚠️",
                "target cut": "Price target cut — analysts see downside ⚠️",
                "ceo resignation": "CEO resigned — leadership uncertainty ⚠️",
                "rate hike": "Rate hike — negative for markets & borrowing costs",
                "recession fears": "Recession fears — risk-off sentiment globally",
                "fii selling": "FII outflows — foreign selling pressure ⚠️",
                "market crash": "Market crash — broad sell-off ⚠️",
                "sensex falls": "Sensex falling — negative market sentiment",
                "nifty drops": "Nifty dropping — bearish pressure",
                "rupee falls record low": "Rupee at record low — imported inflation risk",
                "war escalation": "War escalating — geopolitical risk rises ⚠️",
                "oil price surge": "Oil surging — inflation risk for India",
            }.get(phrase, "Negative development — caution advised ⚠️")
            return "negative", reason

    return "neutral", ""


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
        hist = yf.Ticker(yf_sym).history(period="5d", interval="5m")
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
    return any(s in title.lower() for s in MY_STOCKS)


def is_india_news(title: str) -> bool:
    return any(kw in title.lower() for kw in INDIA_KEYWORDS)


def is_global_impact(title: str) -> bool:
    return any(kw in title.lower() for kw in GLOBAL_KEYWORDS)


def should_skip(title: str) -> bool:
    return any(skip in title.lower() for skip in SKIP_KEYWORDS)


async def fetch_and_send_news():
    global SENT_IDS
    india_news = []
    global_news = []
    positive_stocks = []
    negative_stocks = []
    neutral_stocks = []

    for feed_url, source in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = entry.get("title", "").strip()
                summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
                if not title or len(title) < 10 or should_skip(title):
                    continue
                nid = get_id(title)
                if nid in SENT_IDS:
                    continue
                SENT_IDS.add(nid)

                if is_my_stock(title):
                    sentiment, reason = get_sentiment(title, summary)
                    context = reason if reason else (summary[:120] + "..." if len(summary) > 120 else summary)
                    item = f"▪️<b>{title}</b>\n"
                    if context:
                        item += f"💡 {context}\n"
                    item += f"Source: {source}"
                    if sentiment == "positive":
                        positive_stocks.append(item)
                    elif sentiment == "negative":
                        negative_stocks.append(item)
                    else:
                        neutral_stocks.append(item)
                elif is_india_news(title):
                    context = summary[:120] + "..." if len(summary) > 120 else summary
                    item = f"▪️<b>{title}</b>"
                    if context and context[:50].lower() != title[:50].lower():
                        item += f"\n{context}"
                    item += f"\nSource: {source}"
                    india_news.append(item)
                elif is_global_impact(title):
                    context = summary[:120] + "..." if len(summary) > 120 else summary
                    item = f"▪️<b>{title}</b>"
                    if context and context[:50].lower() != title[:50].lower():
                        item += f"\n{context}"
                    item += f"\nSource: {source}"
                    global_news.append(item)

        except Exception as e:
            print(f"RSS error {source}: {e}")

    if not any([india_news, global_news, positive_stocks, negative_stocks, neutral_stocks]):
        print("No new news")
        return

    now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p IST")
    msg = f"📊 <b>MARKET UPDATE</b>\n<b>{now}</b>\n{'─'*30}\n\n"

    if india_news:
        msg += "<b>🇮🇳 INDIA MARKET CUES</b>\n\n"
        for item in india_news[:4]:
            msg += f"{item}\n\n"

    if global_news:
        msg += "<b>🌍 GLOBAL CUES</b>\n\n"
        for item in global_news[:3]:
            msg += f"{item}\n\n"

    if positive_stocks:
        msg += "<b>🟢 Positive Sentiment Stocks</b>\n\n"
        for item in positive_stocks[:4]:
            msg += f"{item}\n\n"

    if negative_stocks:
        msg += "<b>🔴 Negative Sentiment Stocks</b>\n\n"
        for item in negative_stocks[:3]:
            msg += f"{item}\n\n"

    if neutral_stocks:
        msg += "<b>⚪ Stocks To Watch</b>\n\n"
        for item in neutral_stocks[:3]:
            msg += f"{item}\n\n"

    await send_telegram(msg)

    if len(SENT_IDS) > 2000:
        SENT_IDS = set(list(SENT_IDS)[-1000:])


async def morning_briefing():
    global LAST_BRIEFING_DATE
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if LAST_BRIEFING_DATE == today:
        return
    LAST_BRIEFING_DATE = today

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


async def keep_alive():
    try:
        async with httpx.AsyncClient() as client:
            await client.get("https://api.telegram.org", timeout=5)
    except:
        pass


def run_async(coro):
    asyncio.run(coro)


if __name__ == "__main__":
    print("✅ Bot started — Smart Sentiment + India First!")
    schedule.every().day.at("07:00").do(lambda: run_async(morning_briefing()))
    schedule.every(15).minutes.do(lambda: run_async(fetch_and_send_news()))
    schedule.every(10).minutes.do(lambda: run_async(keep_alive()))
    asyncio.run(fetch_and_send_news())
    while True:
        schedule.run_pending()
        time.sleep(60)
