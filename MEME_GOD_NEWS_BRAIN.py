#!/usr/bin/env python3

"""
============================================================
        ALVIN MEME GOD V2.0 COMBO BRAINIAC
============================================================

NEWS + HYPE + TOKEN DISCOVERY + MARKET ANALYSIS
+ MEMORY + RANKING

PAPER / RESEARCH ONLY
NO LIVE TRADING
NO WALLET
NO PRIVATE KEYS
NO ORDER EXECUTION

Created for Termux / Android
============================================================
"""

import json
import re
import time
import html
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET

# ==========================================================
# CONFIG
# ==========================================================

BOT_NAME = "ALVIN MEME GOD"
VERSION = "V2.0 COMBO BRAINIAC"

CHAIN = "solana"

SCAN_INTERVAL = 300
REQUEST_TIMEOUT = 15

STATE_FILE = Path.home() / "MEME_GOD_NEWS_STATE.json"
HISTORY_FILE = Path.home() / "MEME_GOD_NEWS_HISTORY.txt"
JOURNAL_FILE = Path.home() / "MEME_GOD_NEWS_JOURNAL.txt"

PROFILE_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
PAIR_URL = "https://api.dexscreener.com/token-pairs/v1/solana/{}"

MIN_LIQUIDITY = 25000
MIN_VOLUME_5M = 5000
MIN_VOLUME_1H = 15000

MAX_TOKENS_PER_SCAN = 30
MAX_HISTORY = 500

# ==========================================================
# RSS SOURCES
# ==========================================================

RSS_FEEDS = {
    "CoinDesk":
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph":
        "https://cointelegraph.com/rss",
}

# ==========================================================
# NARRATIVES
# ==========================================================

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
        "cat",
        "kitty",
        "catcoin",
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
        "sol",
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


# ==========================================================
# TERMINAL COLORS
# ==========================================================

RESET = "\033[0m"

BOLD = "\033[1m"

WHITE = "\033[97m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"


def c(text, color):
    return f"{color}{text}{RESET}"


# ==========================================================
# BASIC HELPERS
# ==========================================================

def now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        return float(value)

    except Exception:
        return default


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(str(text))

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def fetch_url(url, timeout=REQUEST_TIMEOUT):
    try:

        request = Request(
            url,
            headers={
                "User-Agent":
                    "Mozilla/5.0 ALVIN-MEME-GOD/2.0"
            },
        )

        with urlopen(
            request,
            timeout=timeout
        ) as response:

            return response.read()

    except Exception:
        return None


def get_json(url):
    raw = fetch_url(url)

    if not raw:
        return None

    try:
        return json.loads(
            raw.decode(
                "utf-8",
                errors="ignore"
            )
        )

    except Exception:
        return None


# ==========================================================
# STATE
# ==========================================================

def load_state():

    default = {
        "started": now(),
        "total_scans": 0,
        "news_items": 0,
        "tokens_seen": 0,
        "candidates": 0,
        "history": [],
    }

    if not STATE_FILE.exists():
        return default

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        for key, value in default.items():

            if key not in data:
                data[key] = value

        return data

    except Exception:
        return default


def save_state(state):

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                indent=2
            )

    except Exception as e:

        print(
            c(
                f"STATE SAVE ERROR: {e}",
                RED
            )
        )


# ==========================================================
# FILE LOGGING
# ==========================================================

def append_line(path, line):

    try:

        with open(
            path,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(line + "\n")

    except Exception as e:

        print(
            c(
                f"LOG ERROR: {e}",
                RED
            )
        )


# ==========================================================
# RSS NEWS ENGINE
# ==========================================================

def parse_feed(source, url):

    raw = fetch_url(url)

    if not raw:
        return []

    try:

        root = ET.fromstring(raw)

    except Exception:
        return []

    items = []

    for item in root.iter():

        tag = item.tag.lower()

        if tag.endswith("item") or tag.endswith("entry"):

            title = ""
            description = ""
            link = ""

            for child in list(item):

                child_tag = child.tag.lower()

                if child_tag.endswith("title"):
                    title = clean_text(
                        child.text
                    )

                elif child_tag.endswith("description"):
                    description = clean_text(
                        child.text
                    )

                elif child_tag.endswith("summary"):
                    description = clean_text(
                        child.text
                    )

                elif child_tag.endswith("link"):

                    if child.text:
                        link = child.text.strip()

                    elif "href" in child.attrib:
                        link = child.attrib["href"]

            if title:

                items.append({
                    "source": source,
                    "title": title,
                    "description": description,
                    "link": link,
                })

    return items[:30]


def detect_narratives(text):

    text = text.lower()

    found = []

    for name, keywords in NARRATIVES.items():

        for keyword in keywords:

            if keyword in text:

                found.append(name)
                break

    return found


def calculate_news_hype(item):

    text = (
        item.get("title", "")
        + " "
        + item.get("description", "")
    ).lower()

    score = 0

    # Strong crypto/meme language
    strong_terms = [
        "viral",
        "trending",
        "memecoin",
        "meme coin",
        "listing",
        "listed",
        "explodes",
        "surges",
        "community",
        "launch",
        "rally",
        "momentum",
    ]

    for term in strong_terms:

        if term in text:
            score += 8

    # Narrative bonus
    narratives = detect_narratives(text)

    score += min(
        len(narratives) * 5,
        25
    )

    # Hype language
    hype_terms = [
        "moon",
        "100x",
        "1000x",
        "massive",
        "huge",
        "breakout",
        "attention",
        "influencer",
    ]

    for term in hype_terms:

        if term in text:
            score += 5

    return min(score, 100)


def collect_news():

    all_news = []

    for source, url in RSS_FEEDS.items():

        items = parse_feed(
            source,
            url
        )

        for item in items:

            text = (
                item["title"]
                + " "
                + item["description"]
            )

            narratives = detect_narratives(text)

            if not narratives:
                continue

            item["narratives"] = narratives

            item["hype_score"] = (
                calculate_news_hype(item)
            )

            item["timestamp"] = now()

            all_news.append(item)

    return all_news


# ==========================================================
# DEXSCREENER TOKEN DISCOVERY
# ==========================================================

def discover_tokens():

    data = get_json(PROFILE_URL)

    if not data:
        return []

    if isinstance(data, dict):

        if "pairs" in data:
            data = data["pairs"]

        elif "profiles" in data:
            data = data["profiles"]

        else:
            data = []

    if not isinstance(data, list):
        return []

    tokens = []

    seen = set()

    for item in data:

        if not isinstance(item, dict):
            continue

        chain_id = str(
            item.get("chainId", "")
        ).lower()

        if chain_id != CHAIN:
            continue

        token_address = (
            item.get("tokenAddress")
            or item.get("address")
        )

        if not token_address:
            continue

        if token_address in seen:
            continue

        seen.add(token_address)

        tokens.append({
            "token_address": token_address,
            "profile": item,
        })

        if len(tokens) >= MAX_TOKENS_PER_SCAN:
            break

    return tokens


# ==========================================================
# MARKET DATA
# ==========================================================

def get_token_pairs(address):

    url = PAIR_URL.format(
        quote(address, safe="")
    )

    data = get_json(url)

    if not data:
        return []

    if isinstance(data, dict):

        if "pairs" in data:
            data = data["pairs"]

        else:
            data = []

    if not isinstance(data, list):
        return []

    return data


def choose_best_pair(pairs):

    if not pairs:
        return None

    sol_pairs = []

    for pair in pairs:

        if not isinstance(pair, dict):
            continue

        if str(
            pair.get("chainId", "")
        ).lower() != "solana":
            continue

        sol_pairs.append(pair)

    if not sol_pairs:
        return None

    return max(
        sol_pairs,
        key=lambda x: safe_float(
            x.get("liquidity", {}).get(
                "usd",
                0
            )
        )
    )


# ==========================================================
# MARKET BRAINS
# ==========================================================

def liquidity_score(liquidity):

    if liquidity >= 500000:
        return 100

    if liquidity >= 250000:
        return 90

    if liquidity >= 100000:
        return 80

    if liquidity >= 50000:
        return 70

    if liquidity >= 25000:
        return 60

    return 25


def volume_score(v5, v1h):

    score_5m = min(
        v5 / 50000 * 100,
        100
    )

    score_1h = min(
        v1h / 250000 * 100,
        100
    )

    return (
        score_5m * 0.55
        + score_1h * 0.45
    )


def buyer_score(pair):

    txns = pair.get(
        "txns",
        {}
    )

    m5 = txns.get(
        "m5",
        {}
    )

    buys = safe_float(
        m5.get("buys")
    )

    sells = safe_float(
        m5.get("sells")
    )

    total = buys + sells

    if total <= 0:
        return 50

    return min(
        100,
        (buys / total) * 100
    )


def momentum_score(pair):

    price_change = pair.get(
        "priceChange",
        {}
    )

    p5 = safe_float(
        price_change.get("m5")
    )

    p1h = safe_float(
        price_change.get("h1")
    )

    # Positive momentum is useful,
    # but extreme spikes are penalized.
    score = 50

    score += p5 * 2
    score += p1h * 0.35

    if p5 > 30:
        score -= 25

    if p5 > 50:
        score -= 20

    if p5 < -20:
        score -= 25

    return max(
        0,
        min(100, score)
    )


def risk_score(pair, liquidity):

    risk = 30

    if liquidity < 25000:
        risk += 40

    elif liquidity < 50000:
        risk += 20

    price_change = pair.get(
        "priceChange",
        {}
    )

    p5 = safe_float(
        price_change.get("m5")
    )

    if p5 > 40:
        risk += 20

    if p5 < -20:
        risk += 20

    txns = pair.get(
        "txns",
        {}
    )

    m5 = txns.get(
        "m5",
        {}
    )

    buys = safe_float(
        m5.get("buys")
    )

    sells = safe_float(
        m5.get("sells")
    )

    total = buys + sells

    if total > 0:

        sell_ratio = sells / total

        if sell_ratio > 0.70:
            risk += 25

    return max(
        0,
        min(100, risk)
    )


def age_score(pair):

    created = pair.get(
        "pairCreatedAt"
    )

    if not created:
        return 50

    try:

        created = float(created) / 1000

        age_hours = (
            time.time() - created
        ) / 3600

        if age_hours < 1:
            return 45

        if age_hours < 6:
            return 70

        if age_hours < 24:
            return 80

        if age_hours < 72:
            return 75

        return 65

    except Exception:
        return 50


# ==========================================================
# MARKET ANALYSIS
# ==========================================================

def analyze_market(pair):

    base = pair.get(
        "baseToken",
        {}
    )

    name = base.get(
        "name",
        "Unknown"
    )

    symbol = base.get(
        "symbol",
        "?"
    )

    address = base.get(
        "address",
        ""
    )

    pair_address = pair.get(
        "pairAddress",
        ""
    )

    liquidity = safe_float(
        pair.get(
            "liquidity",
            {}
        ).get(
            "usd"
        )
    )

    volume = pair.get(
        "volume",
        {}
    )

    v5 = safe_float(
        volume.get("m5")
    )

    v1h = safe_float(
        volume.get("h1")
    )

    liq = liquidity_score(
        liquidity
    )

    vol = volume_score(
        v5,
        v1h
    )

    buyers = buyer_score(
        pair
    )

    momentum = momentum_score(
        pair
    )

    risk = risk_score(
        pair,
        liquidity
    )

    age = age_score(
        pair
    )

    market_score = (
        liq * 0.20
        + vol * 0.25
        + buyers * 0.20
        + momentum * 0.20
        + age * 0.15
    )

    market_score -= risk * 0.15

    market_score = max(
        0,
        min(
            100,
            market_score
        )
    )

    return {
        "name": name,
        "symbol": symbol,
        "token_address": address,
        "pair_address": pair_address,
        "pair_url": pair.get(
            "url",
            ""
        ),
        "dex": pair.get(
            "dexId",
            "unknown"
        ),
        "price": safe_float(
            pair.get("priceUsd")
        ),
        "liquidity": liquidity,
        "volume_5m": v5,
        "volume_1h": v1h,
        "buy_power": buyers,
        "momentum": momentum,
        "risk": risk,
        "age_score": age,
        "market_score": market_score,
    }


# ==========================================================
# NEWS / TOKEN RELATIONSHIP
# ==========================================================

def token_news_score(token, news):

    name = str(
        token.get("name", "")
    ).lower()

    symbol = str(
        token.get("symbol", "")
    ).lower()

    combined = (
        name
        + " "
        + symbol
    )

    best = 0
    best_narratives = []

    for item in news:

        text = (
            item.get("title", "")
            + " "
            + item.get("description", "")
        ).lower()

        narratives = item.get(
            "narratives",
            []
        )

        match = False

        # Exact-ish token mention
        if symbol and len(symbol) >= 3:

            if re.search(
                r"\b"
                + re.escape(symbol)
                + r"\b",
                text
            ):
                match = True

        if name and len(name) >= 4:

            if name in text:
                match = True

        if match:

            hype = safe_float(
                item.get("hype_score")
            )

            if hype > best:

                best = hype

                best_narratives = narratives

    return best, best_narratives


# ==========================================================
# NARRATIVE MATCH
# ==========================================================

def market_narrative_score(token, news):

    name = str(
        token.get("name", "")
    ).lower()

    symbol = str(
        token.get("symbol", "")
    ).lower()

    text = (
        name
        + " "
        + symbol
    )

    found = []

    for narrative, keywords in NARRATIVES.items():

        for keyword in keywords:

            if keyword in text:

                found.append(narrative)
                break

    news_narratives = set()

    for item in news:

        for narrative in item.get(
            "narratives",
            []
        ):

            news_narratives.add(
                narrative
            )

    overlap = (
        set(found)
        & news_narratives
    )

    score = min(
        100,
        len(found) * 15
        + len(overlap) * 15
    )

    return score, list(
        set(found)
        | overlap
    )


# ==========================================================
# COMBO BRAIN
# ==========================================================

def final_judgment(
    market,
    news_score,
    narrative_score
):

    market_score = market[
        "market_score"
    ]

    momentum = market[
        "momentum"
    ]

    buyers = market[
        "buy_power"
    ]

    risk = market[
        "risk"
    ]

    liquidity = market[
        "liquidity"
    ]

    volume_5m = market[
        "volume_5m"
    ]

    volume_1h = market[
        "volume_1h"
    ]

    hype = news_score

    combined = (
        market_score * 0.55
        + hype * 0.20
        + narrative_score * 0.10
        + momentum * 0.10
        + buyers * 0.05
    )

    # Risk penalty
    if risk >= 80:
        combined -= 25

    elif risk >= 65:
        combined -= 12

    # Minimum market confirmation
    if liquidity < MIN_LIQUIDITY:
        return (
            "AVOID",
            max(0, combined),
            "Liquidity below research threshold"
        )

    if volume_5m < MIN_VOLUME_5M:
        return (
            "WAIT",
            max(0, combined),
            "5M volume too weak"
        )

    if volume_1h < MIN_VOLUME_1H:
        return (
            "WAIT",
            max(0, combined),
            "1H volume too weak"
        )

    # Risk rejection
    if risk >= 80:
        return (
            "AVOID",
            max(0, combined),
            "Risk too high"
        )

    # Momentum weakness
    if momentum < 30:
        return (
            "WAIT",
            max(0, combined),
            "Momentum too weak"
        )

    # Strong paper candidate
    if (
        combined >= 78
        and market_score >= 65
        and momentum >= 60
        and buyers >= 55
        and risk < 55
    ):

        return (
            "PAPER ENTER",
            combined,
            "Market + hype confirmation"
        )

    # Watch candidate
    if (
        combined >= 62
        and market_score >= 55
    ):

        return (
            "PAPER WATCH",
            combined,
            "Interesting but needs confirmation"
        )

    return (
        "WAIT",
        combined,
        "Insufficient confirmation"
    )


# ==========================================================
# DISPLAY
# ==========================================================

def print_header(state):

    print()
    print(
        c(
            "╔══════════════════════════════════════════════════════╗",
            CYAN
        )
    )

    print(
        c(
            "║       ALVIN MEME GOD V2.0 COMBO BRAINIAC           ║",
            BOLD + CYAN
        )
    )

    print(
        c(
            "║   NEWS + HYPE + MARKET + MEMORY + RANKING           ║",
            CYAN
        )
    )

    print(
        c(
            "╚══════════════════════════════════════════════════════╝",
            CYAN
        )
    )

    print(
        c(
            f"Time: {now()}",
            WHITE
        )
    )

    print(
        c(
            "MODE: PAPER / RESEARCH ONLY",
            YELLOW
        )
    )

    print(
        c(
            f"Scans: {state['total_scans']}",
            WHITE
        )
    )

    print()


def display_news(news):

    print(
        c(
            "📰 NEWS + HYPE BRAIN",
            BOLD + MAGENTA
        )
    )

    if not news:

        print(
            c(
                "No matching crypto narrative news found.",
                GRAY
            )
        )

        return

    for item in news[:8]:

        narratives = "/".join(
            item.get(
                "narratives",
                []
            )
        )

        hype = item.get(
            "hype_score",
            0
        )

        print(
            f"{c('🔥', MAGENTA)} "
            f"{c(str(hype), YELLOW)}/100 "
            f"{c(narratives, MAGENTA)} "
            f"{c(item['title'][:100], WHITE)}"
        )

        print(
            c(
                f"   Source: {item['source']}",
                GRAY
            )
        )

    print()


def display_candidate(candidate, rank):

    market = candidate[
        "market"
    ]

    verdict = candidate[
        "verdict"
    ]

    if verdict == "PAPER ENTER":
        verdict_color = GREEN

    elif verdict == "PAPER WATCH":
        verdict_color = YELLOW

    elif verdict == "AVOID":
        verdict_color = RED

    else:
        verdict_color = WHITE

    print(
        c(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            BLUE
        )
    )

    print(
        c(
            f"🏆 RANK #{rank}",
            BOLD + CYAN
        )
    )

    print(
        f"{c('🪙 NAME:', WHITE)} "
        f"{c(market['name'], BOLD + WHITE)}"
    )

    print(
        f"{c('🏷️ SYMBOL:', WHITE)} "
        f"{c(market['symbol'], YELLOW)}"
    )

    print(
        c(
            "🔑 TOKEN ID:",
            BOLD + CYAN
        )
    )

    print(
        c(
            f"   {market['token_address']}",
            CYAN
        )
    )

    print(
        c(
            "🔗 PAIR ID:",
            BOLD + CYAN
        )
    )

    print(
        c(
            f"   {market['pair_address']}",
            CYAN
        )
    )

    print(
        f"{c('🌐 DEX:', WHITE)} "
        f"{c(str(market['dex']), WHITE)}"
    )

    narratives = candidate[
        "narratives"
    ]

    print(
        f"{c('🔥 NARRATIVE:', WHITE)} "
        f"{c(', '.join(narratives) if narratives else 'NONE', MAGENTA)}"
    )

    print()

    print(
        f"{c('📰 NEWS HYPE:', WHITE)} "
        f"{c(f'{candidate['news_score']:.0f}/100', YELLOW)}"
    )

    print(
        f"{c('🧠 MARKET:', WHITE)} "
        f"{c(f'{market['market_score']:.0f}/100', CYAN)}"
    )

    print(
        f"{c('🎯 NARRATIVE:', WHITE)} "
        f"{c(f'{candidate['narrative_score']:.0f}/100', MAGENTA)}"
    )

    print(
        f"{c('📈 MOMENTUM:', WHITE)} "
        f"{c(f'{market['momentum']:.0f}/100', GREEN if market['momentum'] >= 60 else YELLOW)}"
    )

    print(
        f"{c('🟢 BUY POWER:', WHITE)} "
        f"{c(f'{market['buy_power']:.1f}%', GREEN if market['buy_power'] >= 55 else RED)}"
    )

    print(
        f"{c('💧 LIQUIDITY:', WHITE)} "
        f"{c(f'${market['liquidity']:,.0f}', YELLOW)}"
    )

    print(
        f"{c('📊 5M VOLUME:', WHITE)} "
        f"{c(f'${market['volume_5m']:,.0f}', YELLOW)}"
    )

    print(
        f"{c('📊 1H VOLUME:', WHITE)} "
        f"{c(f'${market['volume_1h']:,.0f}', YELLOW)}"
    )

    risk_color = (
        GREEN
        if market["risk"] < 45
        else YELLOW
        if market["risk"] < 65
        else RED
    )

    print(
        f"{c('⚠️ RISK:', WHITE)} "
        f"{c(f'{market['risk']:.0f}/100', risk_color)}"
    )

    print(
        f"{c('🧠 COMBO SCORE:', WHITE)} "
        f"{c(f'{candidate['combo_score']:.0f}/100', CYAN)}"
    )

    print(
        f"{c('🎯 VERDICT:', WHITE)} "
        f"{c(verdict, BOLD + verdict_color)}"
    )

    print(
        c(
            f"💡 {candidate['reason']}",
            WHITE
        )
    )

    if market["pair_url"]:

        print(
            c(
                f"🔗 {market['pair_url']}",
                GRAY
            )
        )

    print()


# ==========================================================
# JOURNAL
# ==========================================================

def journal_candidate(candidate):

    market = candidate[
        "market"
    ]

    line = (
        f"[{now()}] "
        f"{candidate['verdict']} | "
        f"{market['name']} | "
        f"{market['symbol']} | "
        f"TOKEN={market['token_address']} | "
        f"PAIR={market['pair_address']} | "
        f"COMBO={candidate['combo_score']:.1f} | "
        f"NEWS={candidate['news_score']:.1f} | "
        f"MARKET={market['market_score']:.1f} | "
        f"RISK={market['risk']:.1f}"
    )

    append_line(
        JOURNAL_FILE,
        line
    )


def save_history(state, candidates):

    for candidate in candidates:

        market = candidate[
            "market"
        ]

        record = {
            "timestamp": now(),
            "name": market["name"],
            "symbol": market["symbol"],
            "token_address": market["token_address"],
            "pair_address": market["pair_address"],
            "dex": market["dex"],
            "combo_score": round(
                candidate["combo_score"],
                2
            ),
            "news_score": round(
                candidate["news_score"],
                2
            ),
            "market_score": round(
                market["market_score"],
                2
            ),
            "narrative_score": round(
                candidate["narrative_score"],
                2
            ),
            "risk": round(
                market["risk"],
                2
            ),
            "verdict": candidate[
                "verdict"
            ],
        }

        state["history"].append(
            record
        )

        append_line(
            HISTORY_FILE,
            json.dumps(
                record,
                ensure_ascii=False
            )
        )

        journal_candidate(
            candidate
        )

    state["history"] = state[
        "history"
    ][-MAX_HISTORY:]


# ==========================================================
# MAIN COMBO SCAN
# ==========================================================

def run_scan(state):

    state["total_scans"] += 1

    print_header(state)

    print(
        c(
            "🌐 Collecting crypto news...",
            WHITE
        )
    )

    news = collect_news()

    state["news_items"] += len(news)

    display_news(news)

    print(
        c(
            "🪙 Discovering Solana token profiles...",
            WHITE
        )
    )

    discovered = discover_tokens()

    state["tokens_seen"] += len(
        discovered
    )

    print(
        c(
            f"Discovered: {len(discovered)} tokens",
            CYAN
        )
    )

    print()

    candidates = []

    for index, token in enumerate(
        discovered,
        start=1
    ):

        address = token[
            "token_address"
        ]

        pairs = get_token_pairs(
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

        # Some profile endpoints can disagree
        # with pair baseToken. Keep the actual
        # discovered address if available.
        if not market[
            "token_address"
        ]:
            market[
                "token_address"
            ] = address

        news_score, news_narratives = (
            token_news_score(
                market,
                news
            )
        )

        narrative_score, market_narratives = (
            market_narrative_score(
                market,
                news
            )
        )

        narratives = list(
            dict.fromkeys(
                news_narratives
                + market_narratives
            )
        )

        verdict, combo_score, reason = (
            final_judgment(
                market,
                news_score,
                narrative_score
            )
        )

        candidate = {
            "market": market,
            "news_score": news_score,
            "narrative_score": narrative_score,
            "combo_score": combo_score,
            "verdict": verdict,
            "reason": reason,
            "narratives": narratives,
        }

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda x: x[
            "combo_score"
        ],
        reverse=True
    )

    state["candidates"] += len(
        candidates
    )

    print()

    print(
        c(
            "🧠 BRAINIAC MARKET RANKING",
            BOLD + CYAN
        )
    )

    print()

    if not candidates:

        print(
            c(
                "No candidates passed the initial market-data pipeline.",
                GRAY
            )
        )

    else:

        for rank, candidate in enumerate(
            candidates[:10],
            start=1
        ):

            display_candidate(
                candidate,
                rank
            )

    save_history(
        state,
        candidates[:10]
    )

    save_state(
        state
    )

    print(
        c(
            "✔ Scan complete.",
            GREEN
        )
    )

    print(
        c(
            f"Next scan in {SCAN_INTERVAL // 60} minutes.",
            GRAY
        )
    )

    print()


# ==========================================================
# MAIN LOOP
# ==========================================================

def main():

    state = load_state()

    print(
        c(
            f"{BOT_NAME} {VERSION}",
            BOLD + CYAN
        )
    )

    print(
        c(
            "Starting COMBO BRAINIAC...",
            WHITE
        )
    )

    print(
        c(
            "Paper / research mode only.",
            YELLOW
        )
    )

    print()

    while True:

        try:

            run_scan(
                state
            )

        except KeyboardInterrupt:

            print()
            print(
                c(
                    "Bot stopped by user.",
                    YELLOW
                )
            )

            save_state(
                state
            )

            break

        except Exception as e:

            print(
                c(
                    f"MAIN LOOP ERROR: {e}",
                    RED
                )
            )

            append_line(
                JOURNAL_FILE,
                f"[{now()}] ERROR: {e}"
            )

        try:

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print()
            print(
                c(
                    "Bot stopped by user.",
                    YELLOW
                )
            )

            save_state(
                state
            )

            break


if __name__ == "__main__":
    main()
