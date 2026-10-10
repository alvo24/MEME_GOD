#!/usr/bin/env python3

"""
============================================================
 ALVIN MEME GOD V2.1
 COMBO BRAINIAC + EARLY ENTRY + FOMO PATTERN ENGINE
============================================================

 PAPER / RESEARCH ONLY

Brains:
  NEWS
  HYPE
  NARRATIVE
  TOKEN DISCOVERY
  LIQUIDITY
  VOLUME
  MOMENTUM
  BUY PRESSURE
  EARLY ENTRY
  FOMO PATTERN
  SKEPTIC / RISK
  OUTCOME LEARNING
  FINAL JUDGMENT

No wallet.
No private keys.
No live orders.
No real-money execution.
============================================================
"""

import json
import math
import os
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

BOT_NAME = "ALVIN MEME GOD"
VERSION = "V2.1 COMBO BRAINIAC"

CHAIN = "solana"

SCAN_INTERVAL = 10
REQUEST_TIMEOUT = 15

STATE_FILE = Path.home() / "ALVIN_MEME_GOD_V21_STATE.json"
HISTORY_FILE = Path.home() / "ALVIN_MEME_GOD_V21_HISTORY.txt"
JOURNAL_FILE = Path.home() / "ALVIN_MEME_GOD_V21_JOURNAL.txt"

PROFILE_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
PAIR_URL = "https://api.dexscreener.com/token-pairs/v1/solana/{}"

MIN_LIQUIDITY = 25_000
MIN_VOLUME_5M = 5_000
MIN_VOLUME_1H = 15_000

MAX_TOKENS_PER_SCAN = 30
MAX_HISTORY = 500

# Paper research thresholds
PAPER_ENTER_SCORE = 78
PAPER_WATCH_SCORE = 62

# Maximum number of stored token observations
MAX_TOKEN_MEMORY = 150


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"


# ============================================================
# RSS NEWS
# ============================================================

RSS_FEEDS = {
    "CoinDesk":
        "https://www.coindesk.com/arc/outboundfeeds/rss/",

    "Cointelegraph":
        "https://cointelegraph.com/rss",
}


# ============================================================
# NARRATIVES
# ============================================================

NARRATIVES = {
    "MEME": [
        "meme",
        "memecoin",
        "meme coin",
        "viral meme",
    ],

    "DOG": [
        "doge",
        "dogecoin",
        "shiba",
        "shib",
        "inu",
        "dog",
    ],

    "CAT": [
        "catcoin",
        "cat coin",
        "kitty",
        "cat",
    ],

    "FROG": [
        "pepe",
        "frog",
    ],

    "AI": [
        "ai meme",
        "ai agent",
        "artificial intelligence",
        "ai token",
    ],

    "SOLANA": [
        "solana",
        "solana meme",
    ],

    "COMMUNITY": [
        "viral",
        "trending",
        "community",
        "social media",
        "influencer",
    ],

    "EXCHANGE": [
        "listing",
        "listed",
        "exchange",
    ],

    "CELEBRITY": [
        "celebrity",
        "elon",
        "musk",
        "rapper",
        "influencer",
    ],

    "DEGEN": [
        "degen",
        "moon",
        "100x",
        "1000x",
    ],
}


# ============================================================
# DEFAULT STATE
# ============================================================

def default_state():
    return {
        "created_at": now(),
        "last_scan": None,
        "total_scans": 0,

        "stats": {
            "tokens_seen": 0,
            "tokens_analyzed": 0,
            "paper_enter": 0,
            "paper_watch": 0,
            "wait": 0,
            "avoid": 0,

            "avg_score": 0.0,
            "avg_market": 0.0,
            "avg_hype": 0.0,
            "avg_early": 0.0,
            "avg_fomo": 0.0,
            "avg_risk": 0.0,

            "completed_outcomes": 0,
            "avg_5m": 0.0,
            "avg_15m": 0.0,
            "avg_30m": 0.0,
            "avg_1h": 0.0,
            "avg_4h": 0.0,
        },

        "tokens": {},

        "outcome_samples": [],

        "news_seen": [],
    }


# ============================================================
# BASIC HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc).isoformat()


def clear_screen():
    print("\033[2J\033[H", end="")


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def fmt_money(value):
    value = safe_float(value)

    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    if value >= 1_000:
        return f"${value / 1_000:.1f}K"

    if value > 0:
        return f"${value:.4f}"

    return "$0"


def fmt_price(value):
    value = safe_float(value)

    if value == 0:
        return "$0"

    if value < 0.000001:
        return f"${value:.10f}"

    if value < 0.001:
        return f"${value:.8f}"

    if value < 1:
        return f"${value:.6f}"

    return f"${value:.4f}"


def shorten(text, length=55):
    text = str(text or "")
    text = " ".join(text.split())

    if len(text) <= length:
        return text

    return text[:length - 3] + "..."


# ============================================================
# FILE HELPERS
# ============================================================

def load_state():
    if not STATE_FILE.exists():
        return default_state()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        base = default_state()

        for key, value in base.items():
            if key not in data:
                data[key] = value

        for key, value in base["stats"].items():
            if key not in data["stats"]:
                data["stats"][key] = value

        return data

    except Exception as e:
        print(f"{YELLOW}State file could not be loaded: {e}{RESET}")
        print(f"{YELLOW}Starting with a fresh state.{RESET}")

        return default_state()


def save_state(state):
    temp = STATE_FILE.with_suffix(".tmp")

    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        os.replace(temp, STATE_FILE)

    except Exception as e:
        print(f"{RED}STATE SAVE ERROR: {e}{RESET}")


def append_history(text):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    except Exception:
        pass


def append_journal(text):
    try:
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    except Exception:
        pass


# ============================================================
# HTTP
# ============================================================

def http_get(url):
    headers = {
        "User-Agent":
            "Mozilla/5.0 ALVIN-MEME-GOD-V21-Research/1.0"
    }

    request = urllib.request.Request(
        url,
        headers=headers
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            return response.read()

    except Exception as e:
        print(
            f"{RED}HTTP ERROR:{RESET} "
            f"{shorten(str(e), 100)}"
        )

        return None


def get_json(url):
    data = http_get(url)

    if not data:
        return None

    try:
        return json.loads(data.decode("utf-8"))

    except Exception as e:
        print(
            f"{RED}JSON ERROR:{RESET} "
            f"{shorten(str(e), 100)}"
        )

        return None


# ============================================================
# NEWS PARSER
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_news_feed(source, data):
    articles = []

    try:
        root = ET.fromstring(data)

    except Exception:
        return articles

    # RSS
    for item in root.findall(".//item"):

        title = clean_text(
            item.findtext("title", "")
        )

        description = clean_text(
            item.findtext("description", "")
        )

        link = clean_text(
            item.findtext("link", "")
        )

        pubdate = clean_text(
            item.findtext("pubDate", "")
        )

        if title:
            articles.append({
                "source": source,
                "title": title,
                "description": description,
                "link": link,
                "published": pubdate,
            })

    # Atom fallback
    if not articles:

        ns = {
            "atom":
                "http://www.w3.org/2005/Atom"
        }

        for entry in root.findall(
            ".//atom:entry",
            ns
        ):

            title = clean_text(
                entry.findtext(
                    "atom:title",
                    "",
                    ns
                )
            )

            summary = clean_text(
                entry.findtext(
                    "atom:summary",
                    "",
                    ns
                )
            )

            link = ""

            link_node = entry.find(
                "atom:link",
                ns
            )

            if link_node is not None:
                link = link_node.attrib.get(
                    "href",
                    ""
                )

            if title:
                articles.append({
                    "source": source,
                    "title": title,
                    "description": summary,
                    "link": link,
                    "published": "",
                })

    return articles


def fetch_news():
    all_articles = []

    for source, url in RSS_FEEDS.items():

        data = http_get(url)

        if not data:
            continue

        articles = parse_news_feed(
            source,
            data
        )

        all_articles.extend(
            articles[:30]
        )

    return all_articles


# ============================================================
# NEWS / HYPE BRAIN
# ============================================================

def detect_narratives(text):
    text = text.lower()

    found = []

    for narrative, keywords in NARRATIVES.items():

        for keyword in keywords:

            if keyword in text:
                found.append(narrative)
                break

    return list(dict.fromkeys(found))


def article_hype_score(article):
    title = article.get(
        "title",
        ""
    )

    description = article.get(
        "description",
        ""
    )

    text = (
        title + " " +
        description
    ).lower()

    score = 20

    keywords = [
        "breaking",
        "viral",
        "trending",
        "surge",
        "rally",
        "explodes",
        "explosion",
        "listing",
        "listed",
        "launch",
        "launches",
        "community",
        "influencer",
        "meme",
        "memecoin",
        "100x",
        "1000x",
    ]

    for keyword in keywords:
        if keyword in text:
            score += 5

    if "breaking" in title.lower():
        score += 10

    if "viral" in text:
        score += 8

    if "listing" in text or "listed" in text:
        score += 8

    return int(clamp(score))


def analyze_news(articles, state):
    narratives = {}
    recent = []

    for article in articles:

        text = (
            article.get("title", "") +
            " " +
            article.get("description", "")
        )

        article_narratives = detect_narratives(
            text
        )

        hype = article_hype_score(
            article
        )

        for narrative in article_narratives:

            if narrative not in narratives:
                narratives[narrative] = []

            narratives[narrative].append(
                hype
            )

        recent.append({
            "source": article.get(
                "source",
                ""
            ),

            "title": article.get(
                "title",
                ""
            ),

            "hype": hype,

            "narratives":
                article_narratives,

            "link":
                article.get(
                    "link",
                    ""
                ),

            "time": now(),
        })

    news_scores = {}

    for narrative, scores in narratives.items():

        if scores:
            average = sum(scores) / len(scores)

        else:
            average = 0

        # More articles = stronger narrative signal
        acceleration_bonus = min(
            len(scores) * 4,
            20
        )

        news_scores[narrative] = int(
            clamp(
                average +
                acceleration_bonus
            )
        )

    # Keep memory small
    old = state.get(
        "news_seen",
        []
    )

    combined = (
        recent +
        old
    )

    state["news_seen"] = combined[-200:]

    return {
        "articles": recent,
        "narrative_scores": news_scores,
    }


# ============================================================
# DEXSCREENER DISCOVERY
# ============================================================

def discover_tokens():
    data = get_json(
        PROFILE_URL
    )

    if not isinstance(data, list):
        return []

    tokens = []

    seen = set()

    for item in data:

        if not isinstance(item, dict):
            continue

        chain = str(
            item.get(
                "chainId",
                ""
            )
        ).lower()

        if chain != CHAIN:
            continue

        address = str(
            item.get(
                "tokenAddress",
                ""
            )
        ).strip()

        if not address:
            continue

        if address in seen:
            continue

        seen.add(address)

        tokens.append({
            "address": address,

            "url":
                item.get(
                    "url",
                    ""
                ),

            "description":
                item.get(
                    "description",
                    ""
                ),

            "icon":
                item.get(
                    "icon",
                    ""
                ),
        })

        if len(tokens) >= MAX_TOKENS_PER_SCAN:
            break

    return tokens


# ============================================================
# TOKEN MARKET DATA
# ============================================================

def get_pairs(address):
    url = PAIR_URL.format(
        address
    )

    data = get_json(url)

    if not isinstance(data, list):
        return []

    pairs = []

    for pair in data:

        if not isinstance(pair, dict):
            continue

        if str(
            pair.get(
                "chainId",
                ""
            )
        ).lower() != CHAIN:
            continue

        pairs.append(pair)

    return pairs


def choose_best_pair(pairs):
    if not pairs:
        return None

    def liquidity_value(pair):
        liquidity = pair.get(
            "liquidity",
            {}
        )

        if not isinstance(
            liquidity,
            dict
        ):
            return 0

        return safe_float(
            liquidity.get(
                "usd",
                0
            )
        )

    return max(
        pairs,
        key=liquidity_value
    )


# ============================================================
# MARKET BRAIN
# ============================================================

def analyze_market(pair):
    if not pair:
        return None

    base = pair.get(
        "baseToken",
        {}
    )

    quote = pair.get(
        "quoteToken",
        {}
    )

    if not isinstance(base, dict):
        base = {}

    if not isinstance(quote, dict):
        quote = {}

    symbol = str(
        base.get(
            "symbol",
            "UNKNOWN"
        )
    )

    name = str(
        base.get(
            "name",
            symbol
        )
    )

    address = str(
        base.get(
            "address",
            ""
        )
    )

    pair_address = str(
        pair.get(
            "pairAddress",
            ""
        )
    )

    dex = str(
        pair.get(
            "dexId",
            "unknown"
        )
    )

    price = safe_float(
        pair.get(
            "priceUsd",
            0
        )
    )

    liquidity = pair.get(
        "liquidity",
        {}
    )

    volume = pair.get(
        "volume",
        {}
    )

    txns = pair.get(
        "txns",
        {}
    )

    price_change = pair.get(
        "priceChange",
        {}
    )

    if not isinstance(liquidity, dict):
        liquidity = {}

    if not isinstance(volume, dict):
        volume = {}

    if not isinstance(txns, dict):
        txns = {}

    if not isinstance(price_change, dict):
        price_change = {}

    liq = safe_float(
        liquidity.get(
            "usd",
            0
        )
    )

    vol5 = safe_float(
        volume.get(
            "m5",
            0
        )
    )

    vol1h = safe_float(
        volume.get(
            "h1",
            0
        )
    )

    vol6h = safe_float(
        volume.get(
            "h6",
            0
        )
    )

    vol24h = safe_float(
        volume.get(
            "h24",
            0
        )
    )

    tx5 = txns.get(
        "m5",
        {}
    )

    tx1h = txns.get(
        "h1",
        {}
    )

    if not isinstance(tx5, dict):
        tx5 = {}

    if not isinstance(tx1h, dict):
        tx1h = {}

    buys5 = safe_float(
        tx5.get(
            "buys",
            0
        )
    )

    sells5 = safe_float(
        tx5.get(
            "sells",
            0
        )
    )

    buys1h = safe_float(
        tx1h.get(
            "buys",
            0
        )
    )

    sells1h = safe_float(
        tx1h.get(
            "sells",
            0
        )
    )

    pc5 = safe_float(
        price_change.get(
            "m5",
            0
        )
    )

    pc1h = safe_float(
        price_change.get(
            "h1",
            0
        )
    )

    created = safe_float(
        pair.get(
            "pairCreatedAt",
            0
        )
    )

    age_minutes = 0

    if created > 0:

        age_minutes = max(
            0,
            (
                time.time() * 1000 -
                created
            ) / 60000
        )

    buy_pressure = 50

    total5 = buys5 + sells5

    if total5 > 0:
        buy_pressure = (
            buys5 /
            total5 *
            100
        )

    # --------------------------------------------------------
    # LIQUIDITY BRAIN
    # --------------------------------------------------------

    if liq >= 1_000_000:
        liquidity_score = 100

    elif liq >= 500_000:
        liquidity_score = 95

    elif liq >= 250_000:
        liquidity_score = 90

    elif liq >= 100_000:
        liquidity_score = 82

    elif liq >= 50_000:
        liquidity_score = 72

    elif liq >= 25_000:
        liquidity_score = 60

    else:
        liquidity_score = 20

    # --------------------------------------------------------
    # VOLUME BRAIN
    # --------------------------------------------------------

    volume_score = 20

    if vol5 >= 100_000:
        volume_score += 45

    elif vol5 >= 50_000:
        volume_score += 38

    elif vol5 >= 25_000:
        volume_score += 30

    elif vol5 >= 10_000:
        volume_score += 20

    elif vol5 >= 5_000:
        volume_score += 10

    if vol1h >= 500_000:
        volume_score += 30

    elif vol1h >= 250_000:
        volume_score += 25

    elif vol1h >= 100_000:
        volume_score += 18

    elif vol1h >= 50_000:
        volume_score += 12

    elif vol1h >= 15_000:
        volume_score += 6

    volume_score = int(
        clamp(volume_score)
    )

    # --------------------------------------------------------
    # MOMENTUM BRAIN
    # --------------------------------------------------------

    momentum_score = 40

    if pc5 > 0:
        momentum_score += min(
            pc5 * 2,
            30
        )

    else:
        momentum_score += max(
            pc5,
            -25
        )

    if pc1h > 0:
        momentum_score += min(
            pc1h * 0.5,
            20
        )

    else:
        momentum_score += max(
            pc1h * 0.2,
            -15
        )

    momentum_score = int(
        clamp(momentum_score)
    )

    # --------------------------------------------------------
    # BUY PRESSURE BRAIN
    # --------------------------------------------------------

    buy_score = int(
        clamp(
            buy_pressure
        )
    )

    # --------------------------------------------------------
    # MARKET SCORE
    # --------------------------------------------------------

    market_score = int(
        clamp(
            liquidity_score * 0.30 +
            volume_score * 0.30 +
            momentum_score * 0.25 +
            buy_score * 0.15
        )
    )

    return {
        "name": name,
        "symbol": symbol,
        "address": address,
        "pair_address": pair_address,
        "dex": dex,

        "price": price,

        "liquidity": liq,

        "volume_5m": vol5,
        "volume_1h": vol1h,
        "volume_6h": vol6h,
        "volume_24h": vol24h,

        "buys_5m": buys5,
        "sells_5m": sells5,

        "buys_1h": buys1h,
        "sells_1h": sells1h,

        "buy_pressure": buy_pressure,

        "price_change_5m": pc5,
        "price_change_1h": pc1h,

        "age_minutes": age_minutes,

        "liquidity_score":
            int(liquidity_score),

        "volume_score":
            int(volume_score),

        "momentum_score":
            int(momentum_score),

        "buy_score":
            int(buy_score),

        "market_score":
            int(market_score),

        "pair_url":
            pair.get(
                "url",
                ""
            ),
    }


# ============================================================
# EARLY ENTRY BRAIN
# ============================================================

def early_entry_brain(market):
    """
    This does NOT identify or copy individual traders.

    It estimates whether current market activity is still
    relatively early compared with the token's current
    observable activity.
    """

    age = market["age_minutes"]

    volume5 = market["volume_5m"]
    volume1h = market["volume_1h"]

    buy = market["buy_pressure"]

    momentum = market["momentum_score"]

    price5 = market["price_change_5m"]

    score = 50

    # Very young market
    if age <= 10:
        score += 20

    elif age <= 30:
        score += 15

    elif age <= 60:
        score += 10

    elif age <= 180:
        score += 5

    elif age > 720:
        score -= 15

    # Rising activity
    if volume1h > 0:

        estimated_5m_share = (
            volume5 * 12 /
            volume1h
        )

        if estimated_5m_share >= 0.45:
            score += 15

        elif estimated_5m_share >= 0.30:
            score += 10

        elif estimated_5m_share >= 0.20:
            score += 5

    # Buyer confirmation
    if buy >= 65:
        score += 10

    elif buy >= 58:
        score += 6

    elif buy < 40:
        score -= 10

    # Positive momentum
    if momentum >= 75:
        score += 8

    elif momentum >= 60:
        score += 5

    # Too much immediate price movement can indicate chasing
    if price5 > 30:
        score -= 18

    elif price5 > 20:
        score -= 10

    return int(
        clamp(score)
    )


# ============================================================
# FOMO PATTERN BRAIN
# ============================================================

def fomo_pattern_brain(market, hype_score):
    """
    Market-behaviour FOMO model.

    Signals:
      - volume acceleration
      - buy pressure
      - price acceleration
      - transaction acceleration
      - narrative/hype
      - late-chasing penalty

    This is a heuristic research signal.
    """

    volume5 = market["volume_5m"]
    volume1h = market["volume_1h"]

    buys5 = market["buys_5m"]
    sells5 = market["sells_5m"]

    buy_pressure = market["buy_pressure"]

    price5 = market["price_change_5m"]

    age = market["age_minutes"]

    score = 0

    volume_acceleration = 0

    if volume1h > 0:
        volume_acceleration = (
            volume5 * 12 /
            volume1h
        )

    # --------------------------------------------------------
    # Volume acceleration
    # --------------------------------------------------------

    if volume_acceleration >= 0.60:
        score += 25

    elif volume_acceleration >= 0.45:
        score += 20

    elif volume_acceleration >= 0.30:
        score += 15

    elif volume_acceleration >= 0.20:
        score += 8

    # --------------------------------------------------------
    # Buy pressure acceleration
    # --------------------------------------------------------

    if buy_pressure >= 70:
        score += 20

    elif buy_pressure >= 62:
        score += 15

    elif buy_pressure >= 55:
        score += 8

    # --------------------------------------------------------
    # Transaction acceleration
    # --------------------------------------------------------

    total5 = buys5 + sells5

    if total5 >= 500:
        score += 20

    elif total5 >= 250:
        score += 15

    elif total5 >= 100:
        score += 10

    elif total5 >= 50:
        score += 5

    # --------------------------------------------------------
    # Price acceleration
    # --------------------------------------------------------

    if 5 <= price5 <= 20:
        score += 15

    elif 20 < price5 <= 30:
        score += 8

    elif price5 > 30:
        score += 3

    # --------------------------------------------------------
    # Narrative / news hype
    # --------------------------------------------------------

    if hype_score >= 80:
        score += 15

    elif hype_score >= 60:
        score += 10

    elif hype_score >= 40:
        score += 5

    # --------------------------------------------------------
    # Late-chasing penalty
    # --------------------------------------------------------

    penalty = 0

    if price5 > 40:
        penalty += 30

    elif price5 > 30:
        penalty += 20

    elif price5 > 20:
        penalty += 10

    if age > 360 and price5 > 20:
        penalty += 10

    score -= penalty

    score = int(
        clamp(score)
    )

    # Pattern label
    if score >= 75:
        pattern = "STRONG ACCELERATION"

    elif score >= 55:
        pattern = "RISING FOMO"

    elif score >= 35:
        pattern = "MODERATE ACTIVITY"

    elif score >= 20:
        pattern = "LOW FOMO"

    else:
        pattern = "NO FOMO"

    return {
        "score": score,
        "pattern": pattern,
        "volume_acceleration":
            volume_acceleration,
        "late_penalty":
            penalty,
    }


# ============================================================
# RISK / SKEPTIC BRAIN
# ============================================================

def risk_brain(market, early_score, fomo_score):
    risk = 20

    liq = market["liquidity"]
    vol5 = market["volume_5m"]
    vol1h = market["volume_1h"]

    buy = market["buy_pressure"]

    pc5 = market["price_change_5m"]

    age = market["age_minutes"]

    # --------------------------------------------------------
    # Liquidity risk
    # --------------------------------------------------------

    if liq < 10_000:
        risk += 35

    elif liq < 25_000:
        risk += 20

    elif liq < 50_000:
        risk += 8

    # --------------------------------------------------------
    # Volume risk
    # --------------------------------------------------------

    if vol5 < 2_000:
        risk += 20

    elif vol5 < 5_000:
        risk += 10

    if vol1h < 10_000:
        risk += 15

    elif vol1h < 15_000:
        risk += 7

    # --------------------------------------------------------
    # Seller pressure
    # --------------------------------------------------------

    if buy < 35:
        risk += 25

    elif buy < 45:
        risk += 12

    # --------------------------------------------------------
    # Excessive price spike
    # --------------------------------------------------------

    if pc5 > 50:
        risk += 25

    elif pc5 > 35:
        risk += 18

    elif pc5 > 25:
        risk += 10

    # --------------------------------------------------------
    # Extremely new token
    # --------------------------------------------------------

    if age < 3:
        risk += 10

    # --------------------------------------------------------
    # FOMO risk
    # --------------------------------------------------------

    if fomo_score >= 85:
        risk += 10

    # Early signal can reduce risk slightly,
    # but never below the base level.
    if early_score >= 75:
        risk -= 5

    risk = int(
        clamp(
            risk,
            0,
            100
        )
    )

    if risk >= 80:
        label = "VERY HIGH"

    elif risk >= 60:
        label = "HIGH"

    elif risk >= 40:
        label = "MEDIUM"

    else:
        label = "LOW"

    return {
        "score": risk,
        "label": label,
    }


# ============================================================
# TOKEN / NARRATIVE RELATIONSHIP
# ============================================================

def token_narratives(market, news):
    text = (
        market["name"] + " " +
        market["symbol"]
    ).lower()

    detected = detect_narratives(
        text
    )

    # Also use market-wide narrative context
    # as a weak research signal.
    news_scores = news.get(
        "narrative_scores",
        {}
    )

    active = []

    for narrative in detected:

        score = news_scores.get(
            narrative,
            0
        )

        active.append(
            (
                narrative,
                score
            )
        )

    # If no exact token narrative was found,
    # choose strongest current narrative as context.
    if not active and news_scores:

        strongest = sorted(
            news_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]

        active = strongest

    return active


def narrative_score(active):
    if not active:
        return 20

    values = [
        safe_float(score)
        for _, score in active
    ]

    return int(
        clamp(
            max(values)
        )
    )


# ============================================================
# COMBINED SCORE
# ============================================================

def combined_score(
    market,
    hype,
    narrative,
    early,
    fomo,
    risk
):

    base = (
        market * 0.32 +
        hype * 0.14 +
        narrative * 0.10 +
        early * 0.18 +
        fomo * 0.14 +
        market * 0.07 +
        (100 - risk) * 0.05
    )

    # Chasing penalty
    if fomo >= 80 and early < 55:
        base -= 8

    # Strong risk penalty
    if risk >= 80:
        base -= 20

    return int(
        clamp(base)
    )


# ============================================================
# FINAL JUDGMENT
# ============================================================

def final_judgment(
    market,
    combined,
    early,
    fomo,
    risk
):

    if market["liquidity"] < MIN_LIQUIDITY:
        return "AVOID"

    if market["volume_5m"] < MIN_VOLUME_5M:
        return "WAIT"

    if market["volume_1h"] < MIN_VOLUME_1H:
        return "WAIT"

    if risk >= 80:
        return "AVOID"

    if market["momentum_score"] < 30:
        return "WAIT"

    # Paper candidate only.
    if (
        combined >= PAPER_ENTER_SCORE
        and
        market["market_score"] >= 65
        and
        early >= 60
        and
        fomo >= 45
        and
        market["buy_pressure"] >= 55
        and
        risk < 55
    ):
        return "PAPER ENTER"

    if (
        combined >= PAPER_WATCH_SCORE
        and
        market["market_score"] >= 50
    ):
        return "PAPER WATCH"

    return "WAIT"


# ============================================================
# TOKEN MEMORY
# ============================================================

def update_token_memory(
    state,
    market,
    combined,
    early,
    fomo,
    risk,
    verdict
):

    address = market["address"]

    if address not in state["tokens"]:
        state["tokens"][address] = {
            "first_seen": now(),
            "last_seen": None,
            "symbol":
                market["symbol"],
            "name":
                market["name"],
            "observations": [],
        }

    token = state["tokens"][address]

    token["last_seen"] = now()

    observations = token.get(
        "observations",
        []
    )

    observations.append({
        "time": now(),
        "price":
            market["price"],
        "liquidity":
            market["liquidity"],
        "volume_5m":
            market["volume_5m"],
        "volume_1h":
            market["volume_1h"],
        "buy_pressure":
            market["buy_pressure"],
        "price_change_5m":
            market["price_change_5m"],
        "combined":
            combined,
        "early":
            early,
        "fomo":
            fomo,
        "risk":
            risk,
        "verdict":
            verdict,
    })

    token["observations"] = (
        observations[-20:]
    )

    # Global token memory limit
    if len(state["tokens"]) > MAX_TOKEN_MEMORY:

        sorted_tokens = sorted(
            state["tokens"].items(),
            key=lambda item:
                item[1].get(
                    "last_seen",
                    ""
                )
        )

        remove_count = (
            len(state["tokens"]) -
            MAX_TOKEN_MEMORY
        )

        for address, _ in sorted_tokens[
            :remove_count
        ]:
            state["tokens"].pop(
                address,
                None
            )


# ============================================================
# OUTCOME LEARNING
# ============================================================

def register_outcome_candidate(
    state,
    market,
    combined,
    verdict
):

    if verdict not in (
        "PAPER ENTER",
        "PAPER WATCH"
    ):
        return

    address = market["address"]

    observations = state[
        "tokens"
    ].get(
        address,
        {}
    ).get(
        "observations",
        []
    )

    if not observations:
        return

    latest = observations[-1]

    # Avoid duplicate candidate from same moment
    candidate = {
        "id":
            f"{address}_{int(time.time())}",

        "created":
            now(),

        "address":
            address,

        "name":
            market["name"],

        "symbol":
            market["symbol"],

        "pair":
            market["pair_address"],

        "entry_price":
            market["price"],

        "entry_score":
            combined,

        "entry_early":
            latest["early"],

        "entry_fomo":
            latest["fomo"],

        "entry_risk":
            latest["risk"],

        "status":
            "TRACKING",

        "checks": {},
    }

    samples = state.get(
        "outcome_samples",
        []
    )

    # Keep one active sample per token
    for sample in samples:

        if (
            sample.get("address")
            == address
            and
            sample.get("status")
            == "TRACKING"
        ):
            return

    samples.append(
        candidate
    )

    state["outcome_samples"] = (
        samples[-200:]
    )


def evaluate_outcomes(state):
    samples = state.get(
        "outcome_samples",
        []
    )

    completed = []

    for sample in samples:

        if sample.get(
            "status"
        ) != "TRACKING":
            continue

        address = sample.get(
            "address"
        )

        token = state[
            "tokens"
        ].get(
            address
        )

        if not token:
            continue

        observations = token.get(
            "observations",
            []
        )

        entry_time = sample.get(
            "created"
        )

        entry_price = safe_float(
            sample.get(
                "entry_price"
            )
        )

        if entry_price <= 0:
            continue

        try:
            entry_dt = datetime.fromisoformat(
                entry_time
            )
        except Exception:
            continue

        elapsed_minutes = (
            datetime.now(
                timezone.utc
            ) -
            entry_dt
        ).total_seconds() / 60

        checkpoints = {
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
        }

        for label, minutes in checkpoints.items():

            if (
                label in
                sample["checks"]
            ):
                continue

            if elapsed_minutes < minutes:
                continue

            # Find observation closest to checkpoint
            best = None
            best_diff = None

            for obs in observations:

                try:
                    obs_dt = datetime.fromisoformat(
                        obs["time"]
                    )

                except Exception:
                    continue

                obs_elapsed = (
                    obs_dt -
                    entry_dt
                ).total_seconds() / 60

                diff = abs(
                    obs_elapsed -
                    minutes
                )

                if best_diff is None or diff < best_diff:

                    best = obs
                    best_diff = diff

            if best is None:
                continue

            current_price = safe_float(
                best.get(
                    "price"
                )
            )

            if current_price <= 0:
                continue

            pnl = (
                (
                    current_price /
                    entry_price
                ) - 1
            ) * 100

            sample["checks"][label] = {
                "pnl_pct":
                    round(pnl, 2),

                "price":
                    current_price,

                "time":
                    best["time"],
            }

        required = [
            "5m",
            "15m",
            "30m",
            "1h",
            "4h",
        ]

        if all(
            key in sample["checks"]
            for key in required
        ):

            sample["status"] = "COMPLETE"

            completed.append(
                sample
            )

    # Update aggregate learning stats
    for sample in completed:

        checks = sample[
            "checks"
        ]

        stats = state[
            "stats"
        ]

        fields = [
            ("avg_5m", "5m"),
            ("avg_15m", "15m"),
            ("avg_30m", "30m"),
            ("avg_1h", "1h"),
            ("avg_4h", "4h"),
        ]

        previous_count = stats[
            "completed_outcomes"
        ]

        new_count = (
            previous_count + 1
        )

        for stat_key, check_key in fields:

            old_avg = safe_float(
                stats.get(
                    stat_key,
                    0
                )
            )

            new_value = safe_float(
                checks[
                    check_key
                ].get(
                    "pnl_pct",
                    0
                )
            )

            new_avg = (
                (
                    old_avg *
                    previous_count
                ) +
                new_value
            ) / new_count

            stats[stat_key] = round(
                new_avg,
                2
            )

        stats[
            "completed_outcomes"
        ] = new_count

        append_journal(
            f"[{now()}] "
            f"OUTCOME COMPLETE | "
            f"{sample.get('symbol')} | "
            f"5m={checks['5m']['pnl_pct']}% | "
            f"15m={checks['15m']['pnl_pct']}% | "
            f"30m={checks['30m']['pnl_pct']}% | "
            f"1h={checks['1h']['pnl_pct']}% | "
            f"4h={checks['4h']['pnl_pct']}%"
        )


# ============================================================
# DISPLAY
# ============================================================

def print_header(state):
    print(
        f"{CYAN}{BOLD}"
        "============================================================"
        f"{RESET}"
    )

    print(
        f"{CYAN}{BOLD}"
        f"      {BOT_NAME} {VERSION}"
        f"{RESET}"
    )

    print(
        f"{CYAN}"
        "      NEWS + HYPE + EARLY ENTRY + FOMO RESEARCH"
        f"{RESET}"
    )

    print(
        f"{CYAN}{BOLD}"
        "============================================================"
        f"{RESET}"
    )

    print(
        f"{YELLOW}"
        " PAPER / RESEARCH MODE — NO LIVE TRADING"
        f"{RESET}"
    )

    print(
        f"{GRAY}"
        f"Last scan: {state.get('last_scan')}"
        f"{RESET}"
    )

    print()


def print_news(news):
    articles = news.get(
        "articles",
        []
    )

    scores = news.get(
        "narrative_scores",
        {}
    )

    print(
        f"{MAGENTA}{BOLD}"
        "🌐 NEWS + HYPE BRAIN"
        f"{RESET}"
    )

    print(
        f"   Articles: "
        f"{YELLOW}{len(articles)}{RESET}"
    )

    if scores:

        strongest = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        print(
            f"   Narratives: "
            f"{MAGENTA}"
            +
            ", ".join(
                f"{name}={score}"
                for name, score
                in strongest
            )
            +
            f"{RESET}"
        )

    else:
        print(
            f"   Narratives: "
            f"{GRAY}No strong current narrative{RESET}"
        )

    print()


def print_token(
    market,
    active_narratives,
    hype,
    early,
    fomo,
    risk,
    combined,
    verdict
):

    print(
        f"{WHITE}{BOLD}"
        "------------------------------------------------------------"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        f"🪙 {market['name']}"
        f"{RESET}"
    )

    print(
        f"🏷️  SYMBOL:     "
        f"{YELLOW}{market['symbol']}{RESET}"
    )

    print(
        f"🔑 TOKEN ID:"
    )

    print(
        f"   {CYAN}{market['address']}{RESET}"
    )

    print(
        f"🔗 PAIR ID:"
    )

    print(
        f"   {CYAN}{market['pair_address']}{RESET}"
    )

    print(
        f"🌐 DEX:        "
        f"{BLUE}{market['dex']}{RESET}"
    )

    narrative_text = ", ".join(
        name
        for name, _ in active_narratives
    )

    if not narrative_text:
        narrative_text = "NONE"

    print(
        f"🔥 NARRATIVE:  "
        f"{MAGENTA}{narrative_text}{RESET}"
    )

    print(
        f"📰 NEWS HYPE:  "
        f"{YELLOW}{hype}/100{RESET}"
    )

    print()

    print(
        f"💵 PRICE:      "
        f"{YELLOW}{fmt_price(market['price'])}{RESET}"
    )

    print(
        f"💧 LIQUIDITY:  "
        f"{YELLOW}{fmt_money(market['liquidity'])}{RESET}"
    )

    print(
        f"📊 5M VOLUME:  "
        f"{YELLOW}{fmt_money(market['volume_5m'])}{RESET}"
    )

    print(
        f"📊 1H VOLUME:  "
        f"{YELLOW}{fmt_money(market['volume_1h'])}{RESET}"
    )

    print(
        f"🟢 BUY POWER:  "
        f"{GREEN}{market['buy_pressure']:.1f}%{RESET}"
    )

    print(
        f"📈 MOMENTUM:   "
        f"{GREEN}{market['momentum_score']}/100{RESET}"
    )

    print(
        f"⏱️  AGE:        "
        f"{WHITE}{market['age_minutes']:.1f} min{RESET}"
    )

    print()

    print(
        f"🎯 EARLY ENTRY: "
        f"{GREEN}{early}/100{RESET}"
    )

    print(
        f"🔥 FOMO SCORE:  "
        f"{MAGENTA}{fomo['score']}/100{RESET}"
    )

    print(
        f"   Pattern:     "
        f"{MAGENTA}{fomo['pattern']}{RESET}"
    )

    print(
        f"   Vol accel:   "
        f"{fomo['volume_acceleration']:.2f}x{RESET}"
    )

    if fomo["late_penalty"] > 0:

        print(
            f"   Chase risk:  "
            f"{RED}-{fomo['late_penalty']}{RESET}"
        )

    print()

    risk_color = (
        RED
        if risk["score"] >= 60
        else YELLOW
        if risk["score"] >= 40
        else GREEN
    )

    print(
        f"⚠️  RISK:        "
        f"{risk_color}"
        f"{risk['score']}/100 "
        f"{risk['label']}"
        f"{RESET}"
    )

    print(
        f"🧠 MARKET:      "
        f"{BLUE}{market['market_score']}/100{RESET}"
    )

    print(
        f"📰 HYPE:        "
        f"{YELLOW}{hype}/100{RESET}"
    )

    print(
        f"🎯 COMBINED:    "
        f"{CYAN}{combined}/100{RESET}"
    )

    if verdict == "PAPER ENTER":
        verdict_color = GREEN

    elif verdict == "PAPER WATCH":
        verdict_color = YELLOW

    elif verdict == "AVOID":
        verdict_color = RED

    else:
        verdict_color = GRAY

    print(
        f"🧠 VERDICT:     "
        f"{verdict_color}{BOLD}"
        f"{verdict}"
        f"{RESET}"
    )

    print()


# ============================================================
# STATS
# ============================================================

def update_stats(
    state,
    market,
    hype,
    early,
    fomo,
    risk,
    combined,
    verdict
):

    stats = state[
        "stats"
    ]

    stats["tokens_analyzed"] += 1

    if verdict == "PAPER ENTER":
        stats["paper_enter"] += 1

    elif verdict == "PAPER WATCH":
        stats["paper_watch"] += 1

    elif verdict == "WAIT":
        stats["wait"] += 1

    elif verdict == "AVOID":
        stats["avoid"] += 1

    count = stats[
        "tokens_analyzed"
    ]

    def rolling_average(
        key,
        value
    ):

        old = safe_float(
            stats.get(
                key,
                0
            )
        )

        return (
            (
                old *
                (count - 1)
            ) +
            value
        ) / count

    stats["avg_score"] = round(
        rolling_average(
            "avg_score",
            combined
        ),
        2
    )

    stats["avg_market"] = round(
        rolling_average(
            "avg_market",
            market["market_score"]
        ),
        2
    )

    stats["avg_hype"] = round(
        rolling_average(
            "avg_hype",
            hype
        ),
        2
    )

    stats["avg_early"] = round(
        rolling_average(
            "avg_early",
            early
        ),
        2
    )

    stats["avg_fomo"] = round(
        rolling_average(
            "avg_fomo",
            fomo["score"]
        ),
        2
    )

    stats["avg_risk"] = round(
        rolling_average(
            "avg_risk",
            risk["score"]
        ),
        2
    )


def print_stats(state):
    stats = state[
        "stats"
    ]

    print(
        f"{CYAN}{BOLD}"
        "============================================================"
        f"{RESET}"
    )

    print(
        f"{CYAN}{BOLD}"
        "📊 V2.1 LEARNING / RESEARCH STATS"
        f"{RESET}"
    )

    print(
        f"Scans:              "
        f"{WHITE}{state.get('total_scans', 0)}{RESET}"
    )

    print(
        f"Tokens analyzed:    "
        f"{WHITE}{stats['tokens_analyzed']}{RESET}"
    )

    print(
        f"PAPER ENTER:        "
        f"{GREEN}{stats['paper_enter']}{RESET}"
    )

    print(
        f"PAPER WATCH:        "
        f"{YELLOW}{stats['paper_watch']}{RESET}"
    )

    print(
        f"WAIT:               "
        f"{GRAY}{stats['wait']}{RESET}"
    )

    print(
        f"AVOID:              "
        f"{RED}{stats['avoid']}{RESET}"
    )

    print()

    print(
        f"Average combined:   "
        f"{CYAN}{stats['avg_score']:.1f}{RESET}"
    )

    print(
        f"Average market:     "
        f"{BLUE}{stats['avg_market']:.1f}{RESET}"
    )

    print(
        f"Average hype:       "
        f"{YELLOW}{stats['avg_hype']:.1f}{RESET}"
    )

    print(
        f"Average early:      "
        f"{GREEN}{stats['avg_early']:.1f}{RESET}"
    )

    print(
        f"Average FOMO:       "
        f"{MAGENTA}{stats['avg_fomo']:.1f}{RESET}"
    )

    print(
        f"Average risk:       "
        f"{RED}{stats['avg_risk']:.1f}{RESET}"
    )

    print()

    print(
        f"Completed outcomes: "
        f"{WHITE}"
        f"{stats['completed_outcomes']}"
        f"{RESET}"
    )

    print(
        f"Average 5m result:  "
        f"{stats['avg_5m']:.2f}%"
    )

    print(
        f"Average 15m result: "
        f"{stats['avg_15m']:.2f}%"
    )

    print(
        f"Average 30m result: "
        f"{stats['avg_30m']:.2f}%"
    )

    print(
        f"Average 1h result:  "
        f"{stats['avg_1h']:.2f}%"
    )

    print(
        f"Average 4h result:  "
        f"{stats['avg_4h']:.2f}%"
    )

    print(
        f"{CYAN}{BOLD}"
        "============================================================"
        f"{RESET}"
    )


# ============================================================
# JOURNAL
# ============================================================

def journal_candidate(
    market,
    active_narratives,
    hype,
    early,
    fomo,
    risk,
    combined,
    verdict
):

    narrative_text = ",".join(
        name
        for name, _ in active_narratives
    )

    line = (
        f"[{now()}] "
        f"{verdict} | "
        f"{market['symbol']} | "
        f"TOKEN={market['address']} | "
        f"PAIR={market['pair_address']} | "
        f"MARKET={market['market_score']} | "
        f"HYPE={hype} | "
        f"NARRATIVE={narrative_text} | "
        f"EARLY={early} | "
        f"FOMO={fomo['score']} | "
        f"RISK={risk['score']} | "
        f"COMBINED={combined} | "
        f"PRICE={market['price']}"
    )

    append_history(line)

    if verdict in (
        "PAPER ENTER",
        "PAPER WATCH"
    ):
        append_journal(line)


# ============================================================
# MAIN SCAN
# ============================================================

def run_scan(state):
    clear_screen()

    print_header(
        state
    )

    print(
        f"{BLUE}"
        "Running market analysis..."
        f"{RESET}"
    )

    print()

    # --------------------------------------------------------
    # NEWS
    # --------------------------------------------------------

    articles = fetch_news()

    news = analyze_news(
        articles,
        state
    )

    print_news(
        news
    )

    # --------------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------------

    print(
        f"{CYAN}{BOLD}"
        "🪙 TOKEN DISCOVERY"
        f"{RESET}"
    )

    discovered = discover_tokens()

    state["stats"][
        "tokens_seen"
    ] += len(discovered)

    print(
        f"   Solana profiles found: "
        f"{GREEN}{len(discovered)}{RESET}"
    )

    print()

    results = []

    # --------------------------------------------------------
    # TOKEN ANALYSIS
    # --------------------------------------------------------

    for index, token in enumerate(
        discovered,
        start=1
    ):

        address = token[
            "address"
        ]

        pairs = get_pairs(
            address
        )

        pair = choose_best_pair(
            pairs
        )

        if not pair:
            continue

        market = analyze_market(
            pair
        )

        if not market:
            continue

        # Exact token address from selected pair
        if not market["address"]:
            market["address"] = address

        active_narratives = (
            token_narratives(
                market,
                news
            )
        )

        narrative = narrative_score(
            active_narratives
        )

        # Market news/hype context
        if news["articles"]:

            article_hypes = [
                article.get(
                    "hype",
                    0
                )
                for article in
                news["articles"]
            ]

            hype = int(
                sum(article_hypes) /
                len(article_hypes)
            )

        else:
            hype = 0

        # Boost only when token itself has a
        # recognized narrative.
        if active_narratives:
            strongest = max(
                score
                for _, score
                in active_narratives
            )

            hype = int(
                clamp(
                    hype * 0.65 +
                    strongest * 0.35
                )
            )

        early = early_entry_brain(
            market
        )

        fomo = fomo_pattern_brain(
            market,
            hype
        )

        risk = risk_brain(
            market,
            early,
            fomo["score"]
        )

        combined = combined_score(
            market=market["market_score"],
            hype=hype,
            narrative=narrative,
            early=early,
            fomo=fomo["score"],
            risk=risk["score"]
        )

        verdict = final_judgment(
            market,
            combined,
            early,
            fomo["score"],
            risk["score"]
        )

        update_token_memory(
            state,
            market,
            combined,
            early,
            fomo["score"],
            risk["score"],
            verdict
        )

        update_stats(
            state,
            market,
            hype,
            early,
            fomo,
            risk,
            combined,
            verdict
        )

        journal_candidate(
            market,
            active_narratives,
            hype,
            early,
            fomo,
            risk,
            combined,
            verdict
        )

        register_outcome_candidate(
            state,
            market,
            combined,
            verdict
        )

        results.append({
            "market": market,
            "narratives":
                active_narratives,
            "hype":
                hype,
            "early":
                early,
            "fomo":
                fomo,
            "risk":
                risk,
            "combined":
                combined,
            "verdict":
                verdict,
        })

    # --------------------------------------------------------
    # OUTCOME LEARNING
    # --------------------------------------------------------

    evaluate_outcomes(
        state
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    results.sort(
        key=lambda x:
            x["combined"],
        reverse=True
    )

    print(
        f"{CYAN}{BOLD}"
        "🧠 TOP V2.1 RESEARCH CANDIDATES"
        f"{RESET}"
    )

    print()

    if not results:

        print(
            f"{YELLOW}"
            "No usable Solana token pairs were found."
            f"{RESET}"
        )

    else:

        # Show top 12
        for result in results[:12]:

            print_token(
                result["market"],
                result["narratives"],
                result["hype"],
                result["early"],
                result["fomo"],
                result["risk"],
                result["combined"],
                result["verdict"]
            )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    state["total_scans"] += 1

    state["last_scan"] = now()

    save_state(
        state
    )

    # Telegram notifications; paper/research mode only.
    try:
        from telegram_helper import telegram_notify_scan
        telegram_notify_scan(results, state)
    except Exception as exc:
        print("Telegram integration error:", type(exc).__name__)

    print_stats(
        state
    )

    print()

    print(
        f"{GRAY}"
        f"Next scan in {SCAN_INTERVAL} seconds."
        f"{RESET}"
    )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    state = load_state()

    print(
        f"{GREEN}{BOLD}"
        "ALVIN MEME GOD V2.1 starting..."
        f"{RESET}"
    )

    print(
        f"{YELLOW}"
        "Paper/research mode only."
        f"{RESET}"
    )

    print()

    time.sleep(1)

    while True:

        try:

            run_scan(
                state
            )

        except KeyboardInterrupt:

            print()

            print(
                f"{YELLOW}"
                "V2.1 stopped by user."
                f"{RESET}"
            )

            save_state(
                state
            )

            break

        except Exception as e:

            print()

            print(
                f"{RED}{BOLD}"
                "MAIN LOOP ERROR:"
                f"{RESET} "
                f"{e}"
            )

            append_journal(
                f"[{now()}] "
                f"MAIN LOOP ERROR: {e}"
            )

        try:

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print()

            print(
                f"{YELLOW}"
                "V2.1 stopped by user."
                f"{RESET}"
            )

            save_state(
                state
            )

            break


if __name__ == "__main__":
    main()
