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
    ("https://www.thehindu.com/business/markets/feeder/default.rss", "The Hindu"),
    ("https://feeds.reuters.com/reuters/businessNews", "Reuters"),
    ("https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362", "CNBC"),
]

MY_STOCKS = [
    "jubilant", "jublfood", "iex", "mrpl", "canara bank", "canbk",
    "niva bupa", "kalyan jewellers", "kalyankjil", "rvnl", "vodafone idea",
    "suzlon", "inox wind", "inoxwind", "coal india", "coalindia",
    "vedanta", "vedl", "itc", "bel ", "bharat electronics", "redington",
    "bank of baroda", "bankbaroda", "punjab national", "pnb ",
    "wipro", "hyundai india", "ireda", "tata tech", "tatatech",
    "yes bank", "yesbank", "idfc first", "ola electric", "olaelec",
    "ather energy", "thangamayil", "geojit", "goldbees", "silverbees",
    "lg india", "groww", "lenskart", "samman", "embassy reit",
    "lemon tree", "eternal", "diamond cable", "diacabs",
]

INDIA_KEYWORDS = [
    "nifty", "sensex", "bank nifty", "gift nifty", "sgx nifty",
    "rbi", "sebi", "rupee", "bse", "nse", "india market",
    "indian stock", "fii", "dii", "repo rate", "dalal street",
    "modi", "budget india", "gdp india", "ipo"
]

GLOBAL_KEYWORDS = [
    "dow jones", "nasdaq", "s&p 500", "wall street", "us fed",
    "federal reserve", "crude oil", "brent", "gold price", "silver price",
    "trump", "iran", "russia ukraine", "china economy",
    "global recession", "interest rate", "opec", "west asia", "middle east",
]

SKIP_KEYWORDS = [
    "cricket", "ipl", "bollywood", "film", "movie", "actor", "recipe",
    "fashion", "lifestyle", "horoscope", "football", "tennis", "hockey",
    "weather", "tourism", "health tips", "diet", "greystone", "microvast",
]

NSE_SYMBOLS = {
    "NIFTY50": "^NSEI", "BANKNIFTY": "^NSEBANK", "MIDCAP": "^NSEMDCP50",
    "GOLD": "GC=F", "SILVER": "SI=F", "USDINR": "INR=X",
    "SUZLON": "SUZLON.NS", "YESBANK": "YESBANK.NS", "IDEA": "IDEA.NS",
    "RVNL": "RVNL.NS", "COALINDIA": "COALINDIA.NS", "ITC": "ITC.NS",
    "CANBK": "CANBK.NS", "IREDA": "IREDA.NS", "WIPRO": "WIPRO.NS",
    "BEL": "BEL.NS", "VEDL": "VEDL.NS", "JUBLFOOD": "JUBLFOOD.NS",
    "PNB": "PNB.NS", "BANKBARODA": "BANKBARODA.NS",
    "INOXWIND": "INOXWIND.NS", "KALYANKJIL": "KALYANKJIL.NS",
    "TATATECH": "TATATECH.NS",
}

POSITIVE_SIGNALS = [
    ("wins order", "New order win — revenue visibility improves ↑"),
    ("bags order", "Order bagged — earnings growth expected ↑"),
    ("new order", "Fresh order received — positive for topline ↑"),
    ("order inflow", "Strong order inflows — business momentum ↑"),
    ("profit rises", "Profit rising — strong earnings trend ↑"),
    ("profit jumps", "Profit jumped — bullish signal ↑"),
    ("revenue up", "Revenue growing — positive momentum ↑"),
    ("upgraded to buy", "Analyst upgrade to Buy — institutional confidence ↑"),
    ("initiates buy", "New Buy recommendation — upside potential ↑"),
    ("target raised", "Price target raised — analysts see more upside ↑"),
    ("mou signed", "MoU signed — future business secured ↑"),
    ("rbi approval", "RBI approved — regulatory clearance positive ↑"),
    ("dividend declared", "Dividend declared — rewards shareholders ↑"),
    ("bonus shares", "Bonus issue — positive for retail investors ↑"),
    ("rate cut", "Rate cut — boosts liquidity & market sentiment ↑"),
    ("repo rate cut", "RBI rate cut — positive for banking sector ↑"),
    ("promoter buying", "Promoter buying — insider confidence signal ↑"),
    ("fii buying", "FII inflows — foreign confidence in India ↑"),
    ("market rally", "Market rallying — broad buying interest ↑"),
    ("sensex rises", "Sensex up — positive market momentum ↑"),
    ("nifty gains", "Nifty gaining — bullish trend continues ↑"),
    ("gift nifty positive", "GIFT Nifty positive — green opening expected ↑"),
    ("dow gains", "Dow up — positive global cues for India ↑"),
    ("nasdaq up", "Nasdaq rising — IT stocks may benefit ↑"),
    ("capacity expansion", "Capacity expansion — long term growth positive ↑"),
    ("new contract", "New contract secured — revenue visibility ↑"),
    ("beat estimates", "Beat estimates — strong quarterly performance ↑"),
]

NEGATIVE_SIGNALS = [
    ("promoter selling", "Promoter selling stake — insider exit signal ⚠️"),
    ("promoter stake sale", "Promoter reducing stake — caution advised ⚠️"),
    ("fraud detected", "Fraud detected — high risk, avoid ⚠️"),
    ("sebi ban", "SEBI ban — regulatory action negative ⚠️"),
    ("sebi penalty", "SEBI penalty — compliance concern ⚠️"),
    ("loss widens", "Loss widening — fundamentals weak ⚠️"),
    ("revenue falls", "Revenue declining — business slowdown ⚠️"),
    ("profit declines", "Profit falling — negative earnings trend ⚠️"),
    ("misses estimates", "Missed estimates — below expectations ⚠️"),
    ("downgraded to sell", "Analyst downgrade to Sell — exit signal ⚠️"),
    ("target cut", "Price target cut — analysts see downside ⚠️"),
    ("penalty imposed", "Penalty imposed — regulatory risk ⚠️"),
    ("ceo resignation", "CEO resigned — leadership uncertainty ⚠️"),
    ("fii selling", "FII outflows — foreign selling pressure ⚠️"),
    ("rate hike", "Rate hike — negative for borrowing & markets ⚠️"),
    ("market crash", "Market crash — broad sell-off ⚠️"),
    ("sensex falls", "Sensex falling — negative market sentiment ⚠️"),
    ("nifty drops", "Nifty dropping — bearish pressure ⚠️"),
    ("rupee record low", "Rupee at record low — imported inflation risk ⚠️"),
    ("oil price surge", "Oil surging — inflation risk for India ⚠️"),
    ("war escalation", "War escalating — geopolitical risk rises ⚠️"),
    ("debt concern", "Debt concerns raised — financial risk ⚠️"),
    ("earnings miss", "Earnings miss — below street expectations ⚠️"),
]


def get_sentiment(title: str, summary: str = "") -> tuple:
    t = (title + " " + summary).lower()
    for phrase, reason in POSITIVE_SIGNALS:
        if phrase in t:
            return "positive", reason
    for phrase, reason in NEGATIVE_SIGNALS:
        if phrase in t:
            return "negative", reason
    return "neutral", ""


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


def get_index_price(symbol_key: str) -> str:
    yf_sym = NSE_SYMBOLS.get(symbol_key)
    if not yf_sym:
        return "N/A"
    try:
        hist = yf.Ticker(yf_sym).history(period="5d", interval="5m")
        if hist.empty:
            return "N/A"
        price = hist["Close"].iloc[-1]
        open_p = hist["Open"].iloc[0]
        change = price - open_p
        pct = (change / open_p) * 100
        arrow = "🟢" if pct >= 0 else "🔴"
        return f"{arrow} {price:,.0f} ({change:+,.0f} | {pct:+.2f}%)"
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
                summary = clean_text(entry.get("summary", "") or "")
                if not title or len(title) < 10 or should_skip(title):
                    continue
                nid = get_id(title)
                if nid in SENT_IDS:
                    continue
                SENT_IDS.add(nid)

                if is_my_stock(title):
                    sentiment, reason = get_sentiment(title, summary)
                    if sentiment == "positive":
                        positive_stocks.append((title, reason, source))
                    elif sentiment == "negative":
                        negative_stocks.append((title, reason, source))
                    else:
                        neutral_stocks.append((title, summary[:100] if summary else "", source))
                elif is_india_news(title):
                    india_news.append((title, summary[:100] if summary else "", source))
                elif is_global_impact(title):
                    global_news.append((title, summary[:100] if summary else "", source))
        except Exception as e:
            print(f"RSS error: {e}")

    if not any([india_news, global_news, positive_stocks, negative_stocks, neutral_stocks]):
        print("No new news")
        return

    now = datetime.now(IST).strftime("%d %b %Y | %I:%M %p IST")
    msg = f"📊 <b>MARKET UPDATE | {now}</b>\n{'─'*30}\n\n"

    if india_news:
        msg += "<b>MARKET CUES</b>\n\n"
        for title, context, source in india_news[:5]:
            msg += f"▪️{title.upper()}\n"
            if context and context[:40].lower() != title[:40].lower():
                msg += f"{context}\n"
            msg += f"Source: {source}\n\n"

    if global_news:
        msg += "<b>🌍 GLOBAL CUES</b>\n\n"
        for title, context, source in global_news[:3]:
            msg += f"▪️{title.upper()}\n"
            if context and context[:40].lower() != title[:40].lower():
                msg += f"{context}\n"
            msg += f"Source: {source}\n\n"

    if positive_stocks:
        msg += "<b>🟢 Positive Sentiment Stocks</b>\n\n"
        for title, reason, source in positive_stocks[:4]:
            msg += f"• {title}\n"
            if reason:
                msg += f"  {reason}\n"
            msg += f"  Source: {source}\n\n"

    if negative_stocks:
        msg += "<b>🔴 Negative Sentiment Stocks</b>\n\n"
        for title, reason, source in negative_stocks[:3]:
            msg += f"• {title}\n"
            if reason:
                msg += f"  {reason}\n"
            msg += f"  Source: {source}\n\n"

    if neutral_stocks:
        msg += "<b>Stocks To Watch</b>\n\n"
        for title, context, source in neutral_stocks[:3]:
            msg += f"• {title}\n"
            msg += f"  Source: {source}\n\n"

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
    msg = f"🌅 <b>GOOD MORNING</b>\n<b>{now} | 7:00 AM IST</b>\n{'─'*30}\n\n"

    msg += "<b>MARKET CUES</b>\n\n"
    msg += f"▪️GIFT NIFTY: {get_index_price('NIFTY50')}\n"
    msg += f"▪️NIFTY 50: {get_index_price('NIFTY50')}\n"
    msg += f"▪️BANK NIFTY: {get_index_price('BANKNIFTY')}\n"
    msg += f"▪️MIDCAP 50: {get_index_price('MIDCAP')}\n\n"

    msg += f"▪️GOLD: {get_price('GOLD')}\n"
    msg += f"▪️SILVER: {get_price('SILVER')}\n\n"

    msg += "<b>📈 Stocks To Watch Today</b>\n\n"
    watchlist = [
        ("SUZLON", "SUZLON"), ("YESBANK", "YESBANK"), ("IDEA", "IDEA"),
        ("RVNL", "RVNL"), ("COALINDIA", "COALINDIA"), ("ITC", "ITC"),
        ("CANBK", "CANBK"), ("IREDA", "IREDA"), ("WIPRO", "WIPRO"),
        ("BEL", "BEL"), ("VEDL", "VEDL"), ("JUBLFOOD", "JUBLFOOD"),
        ("PNB", "PNB"), ("BANKBARODA", "BANKBARODA"),
    ]
    for name, key in watchlist:
        msg += f"• {name} – {get_price(key)}\n"

    await send_telegram(msg)
    await asyncio.sleep(3)
    await fetch_and_send_news()


def run_async(coro):
    asyncio.run(coro)


if __name__ == "__main__":
    print("✅ Bot started!")
    schedule.every().day.at("07:00").do(lambda: run_async(morning_briefing()))
    schedule.every(15).minutes.do(lambda: run_async(fetch_and_send_news()))
    asyncio.run(fetch_and_send_news())
    while True:
        schedule.run_pending()
        time.sleep(60)
