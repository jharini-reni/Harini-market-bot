# =========================================================
# PREMIUM INDIA MARKET TELEGRAM BOT
# =========================================================

import asyncio
import httpx
import feedparser
import yfinance as yf
from datetime import datetime
from pytz import timezone
from rapidfuzz import fuzz

BOT_TOKEN = "8920822727:AAEoeYvwnNrIU58ODEJVGCCLiHy1wSa-VAc"
CHAT_ID = "1212371388"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
IST = timezone("Asia/Kolkata")

WATCHLIST = [
    "rvnl", "suzlon", "vodafone idea", "yes bank", "ireda", "iex", "bel",
    "itc", "coal india", "vedanta", "canara bank", "bank of baroda", "pnb",
    "wipro", "tata tech", "tatatech", "ola electric", "inox wind", "mrpl",
    "jublfood", "jubilant food", "thangamayil", "ather energy",
    "kalyan jewellers", "kalyankjil", "niva bupa", "redington",
    "hyundai india", "diamond cable", "geojit", "goldbees", "silverbees",
    "lg india", "groww", "lenskart", "samman capital", "embassy reit",
    "lemon tree", "eternal", "hfcl", "inoxwind", "canbk", "yesbank",
    "olaelec", "bankbaroda", "jubilant"
]

IMPORTANT_KEYWORDS = [
    "quarterly results", "q4 results", "q1 results", "q2 results", "q3 results",
    "net profit", "revenue growth", "ebitda", "earnings",
    "dividend declared", "dividend record date", "bonus shares", "stock split",
    "buyback", "rights issue", "qip", "ofs", "block deal", "bulk deal",
    "promoter stake", "stake sale",
    "order win", "order bag", "new order", "order inflow", "bags order",
    "wins order", "contract awarded", "mou signed", "agreement signed",
    "capacity expansion", "merger", "acquisition", "takeover", "demerger",
    "nifty", "sensex", "bank nifty", "gift nifty", "sgx nifty",
    "fii", "fpi", "dii", "foreign investor",
    "rbi policy", "repo rate", "rbi governor", "monetary policy",
    "sebi order", "sebi ban", "sebi penalty",
    "credit rating", "rating upgrade", "rating downgrade",
    "rupee", "dollar index", "forex reserve",
    "crude oil", "brent crude", "opec", "oil price",
    "gold price", "silver price", "mcx gold", "mcx silver",
    "us fed", "federal reserve", "rate cut", "rate hike",
    "dow jones", "nasdaq", "wall street",
    "iran", "russia ukraine", "west asia", "middle east",
    "trump tariff", "trade war", "china economy",
    "india gdp", "inflation", "cpi data",
    "ipo listing", "listing gain", "listing loss",
]

BLOCKED_WORDS = [
    "buy or sell", "buy or avoid", "should you buy", "should you invest",
    "target price", "price target", "stop loss",
    "top stocks to buy", "best stocks", "stocks to buy",
    "multibagger", "brokerage recommend", "analyst recommend",
    "technical view", "technical analysis", "chart pattern",
    "stock recommendation", "expert suggests", "expert pick",
    "share price target", "investment strategy", "portfolio strategy",
    "what's fueling", "what is fueling", "here's why",
    "why this stock", "reasons to buy", "time to buy",
    "gmp today", "grey market premium",
    "mutual fund nav", "sip returns",
    "5 stocks", "10 stocks", "top 5", "top 10",
    "morning trade setup", "trading guide", "trading strategy",
    "market outlook", "weekly outlook", "monthly outlook",
    "check latest", "city-wise rates", "city wise rates",
    "check prices", "rates today", "price today in your city",
    "how to invest", "how to trade", "beginners guide",
    "stock under rs 100", "stock under rs 50",
    "mid-cap stock under", "small-cap stock under",
    "live: from", "live updates", "live blog",
    "ipo allotment status", "ipo gmp", "ipo review",
    "morning report", "morning digest", "weekly wrap",
    "market wrap", "daily wrap", "reits may be",
]

BLOCKED_NEWS = [
    "bitcoin", "ethereum", "crypto", "cryptocurrency", "blockchain",
    "nft", "defi", "binance", "coinbase", "dogecoin",
    "cricket", "ipl", "football", "tennis",
    "bollywood", "hollywood", "celebrity", "movie release",
    "music album", "entertainment", "actor", "actress",
    "weather forecast", "tourism", "recipe",
    "fashion", "lifestyle", "horoscope", "astrology",
    "health tips", "diet plan", "travel guide",
    "lincoln international", "greystone", "microvast",
    "canada election", "uk politics", "australia election",
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

SENT_NEWS = []
LAST_BRIEFING_DATE = None


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
    title = title.lower()
    for word in ["latest", "live", "today", "update", "updates", "|"]:
        title = title.replace(word, "")
    return " ".join(title.split())


def is_duplicate(title):
    cleaned = clean_title(title)
    for old in SENT_NEWS:
        if fuzz.token_set_ratio(cleaned, old) > 72:
            return True
    SENT_NEWS.append(cleaned)
    if len(SENT_NEWS) > 3000:
        SENT_NEWS.pop(0)
    return False


def is_watchlist_news(title):
    return any(stock in title.lower() for stock in WATCHLIST)


def is_real_news(title):
    t = title.lower()
    if any(w in t for w in BLOCKED_WORDS):
        return False
    if any(w in t for w in BLOCKED_NEWS):
        return False
    has_keyword = any(k in t for k in IMPORTANT_KEYWORDS)
    has_stock = is_watchlist_news(title)
    return has_keyword or has_stock


def get_sentiment(title):
    t = title.lower()
    positive = [
        "profit up", "profit rises", "profit jumps", "revenue up",
        "revenue grows", "order win", "bags order", "wins order",
        "dividend declared", "dividend record", "bonus shares",
        "buyback", "rating upgrade", "fii buying", "inflow",
        "rally", "surge", "gain", "approval", "mou signed",
        "rate cut", "record high", "capacity expansion",
        "listing gain", "strong demand", "jump", "swings into profit",
        "record revenue", "record annual"
    ]
    negative = [
        "loss", "fall", "drop", "decline", "crash", "weak",
        "sebi ban", "sebi penalty", "fraud", "default",
        "promoter selling", "stake sale", "fii selling", "outflow",
        "rating downgrade", "profit miss", "revenue miss",
        "resignation", "war escalation", "oil surge",
        "rupee falls", "listing loss", "misleading"
    ]
    for word in positive:
        if word in t:
            return "🟢"
    for word in negative:
        if word in t:
            return "🔴"
    return "🔵"


def get_stock_name(title):
    """Extract stock name from title"""
    t = title.lower()
    for stock in WATCHLIST:
        if stock in t:
            return stock.upper()
    return ""


def get_bullet_points(title, summary=""):
    """Generate 2-3 meaningful bullet points for the news"""
    t = title.lower()
    points = []

    # First bullet — the news headline itself (cleaned)
    points.append(title.strip())

    # Second bullet — context based on news type
    if "results" in t or "profit" in t or "revenue" in t:
        if "jump" in t or "surge" in t or "rise" in t or "up" in t:
            points.append("Strong quarterly performance with earnings beat — revenue and margin expansion noted.")
        elif "loss" in t or "fall" in t or "decline" in t:
            points.append("Below-expectation quarterly performance — margin pressure and revenue decline noted.")
        else:
            points.append("Quarterly earnings in focus — investors tracking margins, revenue and future guidance.")
        if "dividend" in t:
            points.append("Dividend declared alongside results — positive signal for income investors.")

    elif "order" in t and ("win" in t or "bag" in t or "award" in t or "inflow" in t):
        points.append("Fresh order win improves revenue visibility and strengthens the order book significantly.")
        points.append("Positive earnings outlook and business momentum may attract fresh buying interest.")

    elif "dividend" in t:
        points.append("Dividend announcement rewards shareholders and signals strong cash flow position.")
        points.append("Investors may accumulate stock before the record date to qualify for dividend.")

    elif "sebi" in t and ("penalty" in t or "ban" in t or "action" in t):
        points.append("Regulatory action by SEBI raises governance concerns — stock may see near-term pressure.")
        points.append("Company may appeal the order — outcome will be closely tracked by investors.")

    elif "promoter" in t and ("sell" in t or "stake" in t):
        points.append("Promoter stake reduction signals potential insider exit — monitor closely for further selling.")
        points.append("FII and retail investor activity in the stock will be closely watched post this development.")

    elif "fii" in t or "fpi" in t:
        if "buy" in t or "inflow" in t:
            points.append("FII inflows signal foreign confidence in India — positive for broader market sentiment.")
        else:
            points.append("FII outflows may create near-term selling pressure — watch for reversal signals.")

    elif "rbi" in t or "repo rate" in t:
        points.append("RBI commentary may impact banking and rate-sensitive sectors sharply.")
        points.append("Market will closely watch any change in monetary policy stance or liquidity guidance.")

    elif "crude oil" in t or "brent" in t or "opec" in t:
        points.append("Crude oil movement directly impacts India's import bill, current account and rupee.")
        points.append("Oil-sensitive sectors like OMCs, aviation and paints may react to this development.")

    elif "gold" in t and "price" in t:
        points.append("Gold price movement impacts GoldBees ETF, jewellery stocks and MCX commodity traders.")
        points.append("Rising gold often signals global risk-off sentiment — watch FII flows accordingly.")

    elif "rupee" in t:
        points.append("Rupee weakness benefits IT exporters but pressures import-heavy sectors like oil and electronics.")
        points.append("RBI may intervene in forex markets if rupee movement becomes disorderly.")

    elif "gift nifty" in t or "sgx nifty" in t:
        points.append("Pre-market indicator signals likely opening direction for Nifty 50 today.")
        points.append("Investors will watch if opening gap sustains or reverses in early trade.")

    elif "dow" in t or "nasdaq" in t or "wall street" in t:
        points.append("US market performance sets the tone for Asian markets and FII sentiment toward India.")
        points.append("Tech-heavy Nasdaq movement may influence Indian IT sector stocks at open.")

    elif "iran" in t or "middle east" in t or "west asia" in t or "war" in t:
        points.append("Geopolitical tension may spike crude oil prices — negative for India's trade deficit.")
        points.append("Risk-off global sentiment may trigger FII outflows from emerging markets including India.")

    elif "merger" in t or "acquisition" in t or "takeover" in t:
        points.append("M&A deal may unlock significant value — target company stock likely to see sharp movement.")
        points.append("Synergy benefits and deal premium will be closely evaluated by institutional investors.")

    elif "buyback" in t:
        points.append("Buyback signals management confidence in the company's fundamentals and future outlook.")
        points.append("Shareholders tendering at premium price may benefit — watch buyback price vs market price.")

    elif "mou" in t or "agreement" in t:
        points.append("Strategic partnership opens new revenue opportunities and strengthens long-term growth outlook.")
        points.append("Execution of the agreement and timeline will be key monitorables going forward.")

    else:
        points.append("Development closely tracked by market participants for potential sector and stock impact.")

    return points[:3]  # Max 3 bullet points


def get_source_short(source):
    """Shorten source name"""
    source_map = {
        "Markets-Economic Times": "ET",
        "Economic Times": "ET",
        "Moneycontrol": "Moneycontrol",
        "NDTV Profit - Latest": "NDTV Profit",
        "NDTV Profit": "NDTV Profit",
        "Business Standard": "Business Standard",
        "mint - markets": "LiveMint",
        "LiveMint": "LiveMint",
        "The Hindu": "The Hindu",
    }
    for key, val in source_map.items():
        if key.lower() in source.lower():
            return val
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

    for news in news_list[:5]:
        title = news["title"]
        source = get_source_short(news["source"])
        sentiment = get_sentiment(title)
        stock_name = get_stock_name(title)
        bullets = get_bullet_points(title)

        # Build header
        if stock_name:
            header = f"{sentiment} *{stock_name}:*"
        else:
            header = f"{sentiment}"

        # Build bullet points
        bullet_text = ""
        for point in bullets:
            bullet_text += f"\n▪️ {point}"

        msg = (
            f"{header}\n"
            f"{bullet_text}\n\n"
            f"📰 Source: {source}"
        )

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
    dow = get_change("^DJI")
    nasdaq = get_change("^IXIC")
    sp500 = get_change("^GSPC")
    nifty = get_change("^NSEI")
    banknifty = get_change("^NSEBANK")

    msg = (
        f"🌅 *MORNING MARKET BRIEFING*\n"
        f"*{date_str} | 7:00 AM IST*\n\n"
        f"──────────────────────────────\n\n"
        f"📊 *GLOBAL MARKETS (Overnight)*\n\n"
        f"▪️ Dow Jones : {dow}\n"
        f"▪️ Nasdaq : {nasdaq}\n"
        f"▪️ S&P 500 : {sp500}\n\n"
        f"──────────────────────────────\n\n"
        f"🇮🇳 *INDIAN MARKET SETUP*\n\n"
        f"▪️ Nifty 50 : {nifty}\n"
        f"▪️ Bank Nifty : {banknifty}\n\n"
        f"📌 Global cues indicate cautious to volatile opening. "
        f"Investors tracking crude oil, FII activity and RBI commentary closely.\n\n"
        f"──────────────────────────────\n\n"
        f"🔥 *STOCKS IN FOCUS TODAY*\n\n"
        f"🟢 RVNL – Railway capex theme strong\n"
        f"🟢 SUZLON – Renewable energy momentum\n"
        f"🟢 BEL – Defence sector continues strong\n"
        f"🟢 IREDA – Green energy financing active\n"
        f"🟢 IEX – Power exchange volume in focus\n"
        f"🟢 YES BANK – Banking sector active\n"
        f"⚪ COAL INDIA – Commodity prices key trigger\n"
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


async def main():
    print("✅ Premium India Market Bot Started!")
    await send_live_news()
    while True:
        now = datetime.now(IST)
        if now.hour == 7 and now.minute == 0:
            await morning_briefing()
        if now.minute % 10 == 0:
            await send_live_news()
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
