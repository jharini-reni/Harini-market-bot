import asyncio
import httpx
import feedparser
import yfinance as yf
from datetime import datetime
from pytz import timezone
from rapidfuzz import fuzz
import threading
from flask import Flask

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = timezone("Asia/Kolkata")

SENT_NEWS = []
LAST_BRIEFING_DATE = None

# Flask app to satisfy Render port requirement
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ India Market Bot is Running!", 200

@app.route('/health')
def health():
    return "OK", 200

WATCHLIST = [
    "rvnl", "suzlon", "vodafone idea", "yes bank", "ireda", "iex", "bel",
    "itc", "coal india", "vedanta", "canara bank", "bank of baroda", "pnb",
    "wipro", "tata tech", "tatatech", "ola electric", "inox wind", "mrpl",
    "jublfood", "jubilant", "thangamayil", "ather energy",
    "kalyan jewellers", "kalyankjil", "niva bupa", "redington",
    "hyundai india", "diamond cable", "geojit", "goldbees", "silverbees",
    "lg india", "groww", "lenskart", "samman", "embassy reit",
    "lemon tree", "eternal", "hfcl", "inoxwind", "canbk", "yesbank",
    "olaelec", "bankbaroda", "punjab national", "suzlon energy",
]

IMPORTANT_KEYWORDS = [
    "results", "profit", "loss", "revenue", "ebitda", "earnings", "q4", "q3", "q2", "q1",
    "quarterly", "annual results", "fy26", "fy25",
    "dividend", "bonus", "split", "buyback", "rights issue", "qip", "ofs",
    "block deal", "bulk deal", "stake", "promoter",
    "order", "contract", "mou", "agreement", "wins", "bags", "awarded",
    "capacity", "expansion", "plant", "launch",
    "merger", "acquisition", "takeover", "demerger", "joint venture",
    "nifty", "sensex", "bank nifty", "gift nifty", "sgx nifty",
    "fii", "fpi", "dii", "institutional",
    "rbi", "sebi", "repo rate", "monetary", "inflation", "gdp", "cpi",
    "rupee", "dollar", "forex", "credit rating",
    "crude oil", "brent", "opec", "gold", "silver", "mcx",
    "fed", "federal reserve", "dow jones", "nasdaq", "wall street",
    "iran", "russia", "ukraine", "west asia", "middle east", "trump",
    "trade war", "tariff", "china",
    "ipo", "listing",
    "rally", "crash", "surge", "plunge", "jump", "fall", "drop",
    "record high", "record low", "52 week", "all time high",
    "shares rise", "shares fall", "shares jump", "shares drop",
    "stock rises", "stock falls",
]

BLOCKED_WORDS = [
    "where are prices headed", "should you buy", "should you invest",
    "buy or sell", "buy or avoid", "top stocks to buy",
    "best stocks to buy", "stocks to buy today",
    "multibagger opportunity", "expert suggests buy",
    "sip returns", "mutual fund nav",
    "5 stocks to", "10 stocks to", "top 5 stocks", "top 10 stocks",
    "how to invest", "beginners guide",
    "city-wise rates", "price in your city", "check rates",
    "ipo gmp today", "grey market premium today",
    "intraday strategy", "weekly market outlook",
]

BLOCKED_NEWS = [
    "bitcoin", "ethereum", "crypto", "cryptocurrency", "blockchain",
    "nft", "defi", "binance", "coinbase", "dogecoin",
    "cricket match", "ipl match", "football match",
    "bollywood", "hollywood", "celebrity news",
    "weather forecast", "recipe", "fashion week",
    "horoscope", "astrology",
]

RSS_FEEDS = [
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://www.livemint.com/rss/markets",
    "https://www.thehindu.com/business/markets/feeder/default.rss",
]


async def send_telegram(message):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(TELEGRAM_URL, json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=20)
            print("Sent!")
        except Exception as e:
            print("Error:", e)


def clean_title(title):
    t = title.lower()
    for w in ["latest", "live", "today", "update", "updates", "|"]:
        t = t.replace(w, "")
    return " ".join(t.split())


def is_duplicate(title):
    cleaned = clean_title(title)
    for old in SENT_NEWS:
        if fuzz.token_set_ratio(cleaned, old) > 75:
            return True
    SENT_NEWS.append(cleaned)
    if len(SENT_NEWS) > 3000:
        SENT_NEWS.pop(0)
    return False


def is_watchlist_news(title):
    return any(s in title.lower() for s in WATCHLIST)


def is_real_news(title):
    t = title.lower()
    if any(w in t for w in BLOCKED_WORDS):
        return False
    if any(w in t for w in BLOCKED_NEWS):
        return False
    return any(k in t for k in IMPORTANT_KEYWORDS) or is_watchlist_news(title)


def get_sentiment(title):
    t = title.lower()
    pos = ["profit", "surge", "rise", "gain", "wins", "bags", "jump",
           "dividend", "bonus", "buyback", "upgrade", "rally", "approval",
           "mou", "record high", "all time high", "strong", "beat",
           "swings into profit", "turns profitable", "inflow", "buying"]
    neg = ["loss", "fall", "drop", "decline", "crash", "penalty",
           "sebi ban", "fraud", "default", "selling", "outflow",
           "downgrade", "miss", "weak", "concern", "plunge",
           "misleading", "resignation", "warning", "sebi penalty"]
    for w in pos:
        if w in t:
            return "🟢"
    for w in neg:
        if w in t:
            return "🔴"
    return "⚪"


def get_stock_name(title):
    t = title.lower()
    stock_map = {
        "rvnl": "RVNL", "suzlon": "SUZLON", "vodafone idea": "IDEA",
        "yes bank": "YES BANK", "ireda": "IREDA", "iex": "IEX",
        " bel ": "BEL", "bel india": "BEL", "itc ltd": "ITC", " itc ": "ITC",
        "coal india": "COAL INDIA", "vedanta": "VEDANTA",
        "canara bank": "CANARA BANK", "bank of baroda": "BANK OF BARODA",
        "bankbaroda": "BANK OF BARODA", " pnb ": "PNB",
        "punjab national": "PNB", "wipro": "WIPRO",
        "tata tech": "TATA TECH", "tatatech": "TATA TECH",
        "ola electric": "OLA ELECTRIC", "inox wind": "INOX WIND",
        "inoxwind": "INOX WIND", "mrpl": "MRPL",
        "jublfood": "JUBLFOOD", "jubilant food": "JUBLFOOD",
        "thangamayil": "THANGAMAYIL", "ather energy": "ATHER",
        "kalyan jewellers": "KALYAN", "niva bupa": "NIVA BUPA",
        "redington": "REDINGTON", "hyundai india": "HYUNDAI",
        "geojit": "GEOJIT", "goldbees": "GOLDBEES",
        "silverbees": "SILVERBEES", "lg india": "LG INDIA",
        "groww": "GROWW", "lenskart": "LENSKART",
        "embassy reit": "EMBASSY REIT", "lemon tree": "LEMON TREE",
        "eternal": "ETERNAL", "hfcl": "HFCL",
    }
    for key, val in stock_map.items():
        if key in t:
            return val
    return ""


def get_bullet_points(title):
    t = title.lower()
    points = [title.strip()]

    if ("results" in t or "profit" in t) and ("jump" in t or "surge" in t or "rise" in t or "record" in t or "beat" in t):
        points.append("Strong quarterly performance with earnings beat — positive for stock sentiment.")
        if "dividend" in t:
            points.append("Dividend declared alongside results — rewards shareholders and signals strong cash flows.")
    elif ("results" in t or "profit" in t) and ("loss" in t or "fall" in t or "decline" in t or "miss" in t):
        points.append("Weak quarterly performance — earnings miss may trigger selling pressure near-term.")
    elif "results" in t or "profit" in t or "revenue" in t:
        points.append("Quarterly earnings in focus — investors tracking revenue growth, margins and guidance.")
        if "dividend" in t:
            points.append("Dividend declared — positive signal for income-focused investors.")
    elif "order" in t and ("win" in t or "bag" in t or "award" in t or "inflow" in t or "wins" in t or "bags" in t):
        points.append("Order win strengthens revenue visibility and order book — positive for earnings outlook.")
        points.append("Consistent order wins signal strong execution capability and sector demand.")
    elif "dividend" in t:
        points.append("Dividend announcement rewards shareholders and signals strong cash flow position.")
        points.append("Investors may accumulate before record date to qualify for dividend.")
    elif "buyback" in t:
        points.append("Buyback signals management confidence in fundamentals — positive for shareholders.")
        points.append("Watch buyback price vs current market price for premium benefit.")
    elif "mou" in t or ("agreement" in t and "sign" in t):
        points.append("Strategic tie-up opens new revenue opportunities and strengthens growth outlook.")
        points.append("Execution timeline of the agreement will be a key monitorable.")
    elif "sebi" in t and ("penalty" in t or "ban" in t or "action" in t):
        points.append("Regulatory action by SEBI raises governance concerns — near-term stock pressure likely.")
        points.append("Company may appeal the order — outcome closely tracked by investors.")
    elif "promoter" in t and ("sell" in t or "stake" in t):
        points.append("Promoter stake reduction signals potential insider exit — monitor closely.")
        points.append("FII and retail activity in the stock will be closely watched.")
    elif "fii" in t or "fpi" in t:
        if "buy" in t or "inflow" in t:
            points.append("FII inflows signal foreign confidence in India — positive for broader market.")
        else:
            points.append("FII outflows may create near-term selling pressure — watch for reversal.")
    elif "rbi" in t or "repo rate" in t:
        points.append("RBI commentary may impact banking and rate-sensitive sectors sharply.")
        points.append("Market will closely watch any change in monetary policy stance.")
    elif "crude oil" in t or "brent" in t or "opec" in t:
        points.append("Crude oil movement impacts India's import bill, current account and rupee.")
        points.append("OMCs, aviation and paint sectors may react to oil price movement.")
    elif "gold" in t and "price" in t:
        points.append("Gold price movement impacts GoldBees ETF and jewellery stocks.")
        points.append("Rising gold signals global risk-off — watch FII flows into India.")
    elif "rupee" in t:
        points.append("Rupee weakness benefits IT exporters but pressures oil and import sectors.")
        points.append("RBI may intervene in forex markets if rupee movement becomes disorderly.")
    elif "gift nifty" in t or "sgx nifty" in t:
        points.append("Pre-market indicator signals likely opening direction for Nifty 50 today.")
        points.append("Watch if opening gap sustains or reverses in early trade.")
    elif "dow" in t or "nasdaq" in t or "wall street" in t:
        points.append("US market performance sets tone for Asian markets and FII flows into India.")
        points.append("Nasdaq movement may influence Indian IT sector stocks at open.")
    elif "iran" in t or "middle east" in t or "west asia" in t or "war" in t:
        points.append("Geopolitical tension may spike crude oil — negative for India's trade deficit.")
        points.append("Risk-off sentiment may trigger FII outflows from emerging markets.")
    elif "merger" in t or "acquisition" in t or "takeover" in t:
        points.append("M&A deal may unlock significant value — target stock likely to see sharp movement.")
        points.append("Synergy benefits and deal premium will be evaluated by institutional investors.")
    elif "inflation" in t or "cpi" in t:
        points.append("Inflation data shapes RBI rate decisions — impacts rate-sensitive banking sector.")
        points.append("Above-estimate inflation may delay rate cuts — negative for equity markets.")
    else:
        points.append("Market participants closely tracking this for potential sector and stock impact.")

    return points[:3]


def get_source_short(source):
    s = source.lower()
    if "economic times" in s or "et markets" in s:
        return "ET"
    if "moneycontrol" in s:
        return "Moneycontrol"
    if "ndtv" in s:
        return "NDTV Profit"
    if "business standard" in s:
        return "Business Standard"
    if "mint" in s:
        return "LiveMint"
    if "hindu" in s:
        return "The Hindu"
    return source


async def fetch_news():
    collected = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:25]:
                title = entry.title.strip()
                if not title or len(title) < 15:
                    continue
                if is_duplicate(title):
                    continue
                if not is_real_news(title):
                    continue
                collected.append({
                    "title": title,
                    "source": feed.feed.get("title", "News")
                })
        except Exception as e:
            print("RSS Error:", e)
    return collected


async def send_live_news():
    now = datetime.now(IST)
    if not (6 <= now.hour <= 23):
        return
    print("Checking news...")
    news_list = await fetch_news()
    if not news_list:
        print("No new news")
        return
    for news in news_list[:6]:
        title = news["title"]
        source = get_source_short(news["source"])
        sentiment = get_sentiment(title)
        stock_name = get_stock_name(title)
        bullets = get_bullet_points(title)

        header = f"{sentiment} *{stock_name}:*" if stock_name else f"{sentiment}"
        bullet_text = "".join(f"\n▪️ {p}" for p in bullets)
        msg = f"{header}\n{bullet_text}\n\n📰 Source: {source}"
        await send_telegram(msg)
        await asyncio.sleep(3)


def get_change(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="2d")
        prev = hist["Close"].iloc[-2]
        curr = hist["Close"].iloc[-1]
        chg = ((curr - prev) / prev) * 100
        emoji = "🟢" if chg > 0 else "🔴"
        return f"{emoji} {chg:+.2f}%"
    except:
        return "N/A"


async def morning_briefing():
    global LAST_BRIEFING_DATE
    today = datetime.now(IST).strftime("%Y-%m-%d")
    if LAST_BRIEFING_DATE == today:
        return
    LAST_BRIEFING_DATE = today
    date_str = datetime.now(IST).strftime("%d %b %Y")
    msg = (
        f"🌅 *MORNING MARKET BRIEFING*\n*{date_str} | 7:00 AM IST*\n\n"
        f"──────────────────────────────\n\n"
        f"📊 *GLOBAL MARKETS (Overnight)*\n\n"
        f"▪️ Dow Jones : {get_change('^DJI')}\n"
        f"▪️ Nasdaq : {get_change('^IXIC')}\n"
        f"▪️ S&P 500 : {get_change('^GSPC')}\n\n"
        f"──────────────────────────────\n\n"
        f"🇮🇳 *INDIAN MARKET SETUP*\n\n"
        f"▪️ Nifty 50 : {get_change('^NSEI')}\n"
        f"▪️ Bank Nifty : {get_change('^NSEBANK')}\n\n"
        f"📌 Investors tracking crude oil, FII activity and global cues closely.\n\n"
        f"──────────────────────────────\n\n"
        f"🔥 *STOCKS IN FOCUS TODAY*\n\n"
        f"🟢 RVNL – Railway capex theme strong\n"
        f"🟢 SUZLON – Renewable energy momentum\n"
        f"🟢 BEL – Defence sector strong\n"
        f"🟢 IREDA – Green energy financing active\n"
        f"🟢 IEX – Power exchange in focus\n"
        f"🟢 YES BANK – Banking sector active\n"
        f"⚪ COAL INDIA – Commodity prices key\n"
        f"🔴 OLA ELECTRIC – Promoter activity watch\n\n"
        f"──────────────────────────────\n\n"
        f"⚠️ *KEY TRIGGERS TODAY*\n\n"
        f"▪️ FII / DII Activity\n"
        f"▪️ Corporate Results Season\n"
        f"▪️ Crude Oil Movement\n"
        f"▪️ RBI & Global Cues\n"
        f"▪️ Geopolitical Updates\n\n"
        f"──────────────────────────────"
    )
    await send_telegram(msg)


async def bot_loop():
    print("✅ Bot Started!")
    await send_live_news()
    while True:
        now = datetime.now(IST)
        if now.hour == 7 and now.minute == 0:
            await morning_briefing()
        if now.minute % 10 == 0:
            await send_live_news()
        await asyncio.sleep(60)


def run_bot():
    asyncio.run(bot_loop())


if __name__ == "__main__":
    # Run bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    # Run Flask web server (satisfies Render port requirement)
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
