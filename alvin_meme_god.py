#!/usr/bin/env python3

"""
===============================================================
                 ALVIN MEME GOD V3.0
                  BRAINIAC ENGINE
===============================================================

PAPER-TRADING / RESEARCH ENGINE ONLY

Architecture:

DISCOVERY
    ↓
MEME BRAIN
    ↓
MARKET BRAIN
    ↓
VOLUME BRAIN
    ↓
MOMENTUM BRAIN
    ↓
BUYER BRAIN
    ↓
AGE BRAIN
    ↓
RISK BRAIN
    ↓
SKEPTIC BRAIN
    ↓
TIMING BRAIN
    ↓
MEMORY BRAIN
    ↓
JUDGMENT ENGINE
    ↓
PAPER ENTER / WATCH / WAIT / AVOID

No wallet.
No private keys.
No real-money transactions.
===============================================================
"""

import os
import json
import time
from datetime import datetime, timezone

import requests


# ===============================================================
# CONFIG
# ===============================================================

BOT_NAME = "ALVIN MEME GOD"
VERSION = "V3.0 BRAINIAC"

CHAIN = "solana"

PROFILE_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
PAIR_URL = "https://api.dexscreener.com/token-pairs/v1/solana/{}"

SCAN_INTERVAL = 10

STARTING_BALANCE = 100.00
PAPER_TRADE_SIZE = 10.00
MAX_OPEN_TRADES = 5

MIN_LIQUIDITY = 25_000
MIN_VOLUME_5M = 5_000
MIN_VOLUME_1H = 15_000

MIN_MEME_SCORE = 45
MIN_QUALITY = 55

PAPER_ENTRY_SCORE = 72

MAX_HOLD_HOURS = 6

# How many historical observations to retain per token.
MAX_TOKEN_MEMORY = 30


# ===============================================================
# FILES
# ===============================================================

STATE_FILE = "MEME_GOD_V30_STATE.json"
SEARCH_LOG = "MEME_GOD_V30_SEARCH_HISTORY.txt"
TRADE_LOG = "MEME_GOD_V30_TRADES.txt"
BRAIN_LOG = "MEME_GOD_V30_BRAIN_JOURNAL.txt"


# ===============================================================
# COLORS
# ===============================================================

RESET = "\033[0m"
BOLD = "\033[1m"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"


# ===============================================================
# HTTP
# ===============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD/3.0",
    "Accept": "application/json",
})


# ===============================================================
# HELPERS
# ===============================================================

def clear_screen():
    os.system("clear")


def timestamp():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def money(value):
    return f"${safe_float(value):,.2f}"


def percent(value):
    value = safe_float(value)

    if value >= 0:
        return f"+{value:.2f}%"

    return f"{value:.2f}%"


def append_log(filename, text):

    try:

        with open(
            filename,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(text + "\n")

    except Exception:
        pass


# ===============================================================
# STATE
# ===============================================================

def default_state():

    return {
        "balance": STARTING_BALANCE,

        "open_trades": [],

        "closed_trades": [],

        "token_memory": {},

        "watchlist": {},

        "total_scans": 0,

        "total_entries": 0,

        "total_exits": 0,

        "total_tokens_analyzed": 0,
    }


def load_state():

    if not os.path.exists(STATE_FILE):
        return default_state()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            state = json.load(f)

        base = default_state()
        base.update(state)

        return base

    except Exception as e:

        print(
            f"{YELLOW}"
            f"Could not load state: {e}"
            f"{RESET}"
        )

        return default_state()


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
            f"{RED}"
            f"State save error: {e}"
            f"{RESET}"
        )


# ===============================================================
# DISCOVERY
# ===============================================================

def discover_tokens():

    try:

        response = session.get(
            PROFILE_URL,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):
            return []

        results = []

        seen = set()

        for item in data:

            if not isinstance(item, dict):
                continue

            chain = str(
                item.get("chainId") or ""
            ).lower()

            if chain != CHAIN:
                continue

            address = (
                item.get("tokenAddress")
                or item.get("address")
            )

            if not address:
                continue

            address = str(address)

            if address in seen:
                continue

            seen.add(address)

            results.append({
                "address": address,
                "profile": item
            })

        return results

    except Exception as e:

        print(
            f"{RED}"
            f"Discovery error: {e}"
            f"{RESET}"
        )

        return []


# ===============================================================
# PAIR LOOKUP
# ===============================================================

def get_pairs(address):

    try:

        response = session.get(
            PAIR_URL.format(address),
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            return data

        return []

    except Exception:

        return []


def best_pair(pairs):

    valid = []

    for pair in pairs:

        if not isinstance(pair, dict):
            continue

        if str(
            pair.get("chainId") or ""
        ).lower() != CHAIN:
            continue

        valid.append(pair)

    if not valid:
        return None

    def liquidity(pair):

        liq = pair.get("liquidity") or {}

        return safe_float(
            liq.get("usd")
        )

    return max(
        valid,
        key=liquidity
    )


# ===============================================================
# MARKET DATA
# ===============================================================

def prepare_pair(pair, profile=None):

    liquidity = pair.get("liquidity") or {}

    volume = pair.get("volume") or {}

    txns = pair.get("txns") or {}

    changes = pair.get("priceChange") or {}

    m5 = txns.get("m5") or {}

    buys = safe_int(
        m5.get("buys")
    )

    sells = safe_int(
        m5.get("sells")
    )

    total = buys + sells

    if total > 0:

        buy_pressure = (
            buys / total
        ) * 100

    else:

        buy_pressure = 50

    pair["_profile"] = profile or {}

    pair["_price"] = safe_float(
        pair.get("priceUsd")
    )

    pair["_liquidity"] = safe_float(
        liquidity.get("usd")
    )

    pair["_volume_5m"] = safe_float(
        volume.get("m5")
    )

    pair["_volume_1h"] = safe_float(
        volume.get("h1")
    )

    pair["_volume_24h"] = safe_float(
        volume.get("h24")
    )

    pair["_buys"] = buys
    pair["_sells"] = sells

    pair["_buy_pressure"] = buy_pressure

    pair["_change_5m"] = safe_float(
        changes.get("m5")
    )

    pair["_change_1h"] = safe_float(
        changes.get("h1")
    )

    pair["_change_6h"] = safe_float(
        changes.get("h6")
    )

    pair["_change_24h"] = safe_float(
        changes.get("h24")
    )

    return pair


# ===============================================================
# MEME BRAIN
# ===============================================================

MEME_KEYWORDS = {
    "meme",
    "memecoin",
    "meme coin",
    "pepe",
    "wojak",
    "chad",
    "degen",
    "based",
    "dog",
    "doge",
    "shib",
    "shiba",
    "inu",
    "cat",
    "kitty",
    "frog",
    "ape",
    "monkey",
    "hamster",
    "rat",
    "goat",
    "pig",
    "duck",
    "chicken",
    "penguin",
    "fish",
    "whale",
    "wolf",
    "fox",
    "lion",
    "tiger",
    "sigma",
    "gigachad",
    "skibidi",
    "brainrot",
    "rizz",
    "gm",
    "wagmi",
    "moon",
    "rocket",
    "bonk",
    "floki",
    "wif",
}


def meme_brain(pair):

    token = pair.get("baseToken") or {}

    name = str(
        token.get("name") or ""
    )

    symbol = str(
        token.get("symbol") or ""
    )

    profile = pair.get("_profile") or {}

    description = str(
        profile.get("description") or ""
    )

    text = (
        name
        + " "
        + symbol
        + " "
        + description
    ).lower()

    matches = []

    for keyword in MEME_KEYWORDS:

        if keyword in text:
            matches.append(keyword)

    score = 0

    # Identity
    score += min(
        len(matches) * 10,
        55
    )

    # Market behavior
    if pair["_volume_5m"] >= 10_000:
        score += 5

    if pair["_volume_1h"] >= 50_000:
        score += 5

    if pair["_liquidity"] >= 25_000:
        score += 5

    if pair["_change_5m"] >= 5:
        score += 5

    # Social/profile information
    if profile.get("links"):
        score += 10

    score = int(
        clamp(score)
    )

    if score >= 75:

        classification = "STRONG MEME"

    elif score >= 55:

        classification = "POSSIBLE MEME"

    elif score >= 35:

        classification = "WEAK MEME"

    else:

        classification = "UNKNOWN"

    return {
        "score": score,
        "classification": classification,
        "matches": matches,
    }


# ===============================================================
# MARKET BRAIN
# ===============================================================

def market_brain(pair):

    liquidity = pair["_liquidity"]

    volume_5m = pair["_volume_5m"]

    volume_1h = pair["_volume_1h"]

    volume_24h = pair["_volume_24h"]

    buy_pressure = pair["_buy_pressure"]

    score = 0

    reasons = []

    # Liquidity
    if liquidity >= 250_000:

        score += 30
        reasons.append("strong liquidity")

    elif liquidity >= 100_000:

        score += 25
        reasons.append("good liquidity")

    elif liquidity >= 50_000:

        score += 18
        reasons.append("acceptable liquidity")

    elif liquidity >= 25_000:

        score += 10
        reasons.append("minimum liquidity")

    else:

        reasons.append("low liquidity")

    # Volume
    if volume_5m >= 50_000:

        score += 20

    elif volume_5m >= 20_000:

        score += 16

    elif volume_5m >= 5_000:

        score += 10

    # Hourly activity
    if volume_1h >= 250_000:

        score += 20

    elif volume_1h >= 100_000:

        score += 16

    elif volume_1h >= 50_000:

        score += 12

    elif volume_1h >= 15_000:

        score += 8

    # Daily activity
    if volume_24h >= 1_000_000:

        score += 15

    elif volume_24h >= 500_000:

        score += 12

    elif volume_24h >= 100_000:

        score += 8

    # Buyers
    if buy_pressure >= 65:

        score += 15
        reasons.append("buyers dominant")

    elif buy_pressure >= 55:

        score += 10
        reasons.append("buyers stronger")

    elif buy_pressure < 40:

        reasons.append("seller pressure")

    score = int(
        clamp(score)
    )

    return score, reasons


# ===============================================================
# VOLUME BRAIN
# ===============================================================

def volume_brain(pair):

    volume_5m = pair["_volume_5m"]

    volume_1h = pair["_volume_1h"]

    if volume_1h <= 0:

        return 50, 1.0, "insufficient history"

    baseline = volume_1h / 12

    if baseline <= 0:

        return 50, 1.0, "insufficient baseline"

    acceleration = (
        volume_5m / baseline
    )

    if acceleration >= 5:

        score = 100
        label = "EXPLOSIVE"

    elif acceleration >= 3:

        score = 90
        label = "VERY STRONG"

    elif acceleration >= 2:

        score = 80
        label = "STRONG"

    elif acceleration >= 1.5:

        score = 70
        label = "BUILDING"

    elif acceleration >= 1:

        score = 55
        label = "NORMAL"

    elif acceleration >= 0.75:

        score = 40
        label = "COOLING"

    else:

        score = 25
        label = "WEAK"

    return score, acceleration, label


# ===============================================================
# MOMENTUM BRAIN
# ===============================================================

def momentum_brain(pair):

    c5 = pair["_change_5m"]

    c1 = pair["_change_1h"]

    c6 = pair["_change_6h"]

    volume_score, acceleration, volume_label = (
        volume_brain(pair)
    )

    score = 50

    reasons = []

    # 5m
    if c5 >= 10:

        score += 18
        reasons.append("strong short-term momentum")

    elif c5 >= 5:

        score += 12
        reasons.append("positive short-term momentum")

    elif c5 >= 2:

        score += 6

    elif c5 < -5:

        score -= 18
        reasons.append("short-term weakness")

    elif c5 < 0:

        score -= 5

    # 1h
    if c1 >= 20:

        score += 15
        reasons.append("strong hourly trend")

    elif c1 >= 10:

        score += 10
        reasons.append("positive hourly trend")

    elif c1 < -15:

        score -= 15
        reasons.append("negative hourly trend")

    # 6h
    if c6 >= 30:

        score += 8

    elif c6 < -20:

        score -= 8

    # Volume acceleration
    if acceleration >= 3:

        score += 15
        reasons.append("volume exploding")

    elif acceleration >= 2:

        score += 10
        reasons.append("volume accelerating")

    elif acceleration >= 1.5:

        score += 6
        reasons.append("volume building")

    elif acceleration < 0.75:

        score -= 8
        reasons.append("volume cooling")

    score = int(
        clamp(score)
    )

    return score, reasons


# ===============================================================
# BUYER BRAIN
# ===============================================================

def buyer_brain(pair, previous):

    current = pair["_buy_pressure"]

    previous_pressure = None

    if previous:

        previous_pressure = safe_float(
            previous.get("buy_pressure"),
            50
        )

    score = current

    reasons = []

    if current >= 70:

        score = min(
            100,
            score + 15
        )

        reasons.append(
            "strong buyer control"
        )

    elif current >= 60:

        score = min(
            100,
            score + 10
        )

        reasons.append(
            "buyers in control"
        )

    elif current < 40:

        score -= 15

        reasons.append(
            "sellers in control"
        )

    if previous_pressure is not None:

        delta = current - previous_pressure

        if delta >= 10:

            score += 15

            reasons.append(
                "buyer pressure accelerating"
            )

        elif delta >= 5:

            score += 8

            reasons.append(
                "buyer pressure improving"
            )

        elif delta <= -10:

            score -= 15

            reasons.append(
                "buyer pressure collapsing"
            )

        elif delta <= -5:

            score -= 8

            reasons.append(
                "buyer pressure weakening"
            )

    return int(
        clamp(score)
    ), reasons


# ===============================================================
# AGE BRAIN
# ===============================================================

def age_brain(pair):

    created = pair.get("pairCreatedAt")

    if not created:

        return 50, "AGE UNKNOWN", 0

    try:

        created_ms = safe_float(
            created
        )

        now_ms = (
            time.time() * 1000
        )

        age_hours = (
            now_ms - created_ms
        ) / 3_600_000

        if age_hours < 0:
            age_hours = 0

    except Exception:

        return 50, "AGE UNKNOWN", 0

    if age_hours < 0.083:

        return (
            20,
            "EXTREMELY NEW",
            age_hours
        )

    if age_hours < 0.5:

        return (
            40,
            "VERY NEW",
            age_hours
        )

    if age_hours < 2:

        return (
            65,
            "EARLY",
            age_hours
        )

    if age_hours < 12:

        return (
            80,
            "ESTABLISHED",
            age_hours
        )

    if age_hours < 48:

        return (
            90,
            "MATURE",
            age_hours
        )

    return (
        85,
        "OLD MARKET",
        age_hours
    )


# ===============================================================
# RISK BRAIN
# ===============================================================

def risk_brain(pair):

    risk = 20

    reasons = []

    liquidity = pair["_liquidity"]

    c5 = pair["_change_5m"]

    c1 = pair["_change_1h"]

    pressure = pair["_buy_pressure"]

    volume_5m = pair["_volume_5m"]

    # Liquidity
    if liquidity < 25_000:

        risk += 35
        reasons.append("very low liquidity")

    elif liquidity < 50_000:

        risk += 20
        reasons.append("limited liquidity")

    elif liquidity < 100_000:

        risk += 10

    # Short-term pump
    if c5 >= 30:

        risk += 30
        reasons.append("extreme 5m pump")

    elif c5 >= 20:

        risk += 20
        reasons.append("large 5m pump")

    elif c5 >= 12:

        risk += 10
        reasons.append("extended 5m move")

    # Hourly extension
    if c1 >= 100:

        risk += 25
        reasons.append("extreme hourly extension")

    elif c1 >= 60:

        risk += 18
        reasons.append("large hourly extension")

    elif c1 >= 40:

        risk += 10
        reasons.append("extended hourly move")

    # Sellers
    if pressure < 35:

        risk += 25
        reasons.append("heavy selling")

    elif pressure < 45:

        risk += 10
        reasons.append("weak buyer control")

    # Volume/liquidity stress
    if liquidity > 0:

        ratio = volume_5m / liquidity

        if ratio > 1:

            risk += 15
            reasons.append(
                "extreme volume/liquidity ratio"
            )

        elif ratio > 0.5:

            risk += 8

    return int(
        clamp(risk)
    ), reasons


# ===============================================================
# SKEPTIC BRAIN
# ===============================================================

def skeptic_brain(
    pair,
    meme_score,
    quality,
    momentum,
    buyers,
    risk,
    age_score
):

    objections = []

    confidence_penalty = 0

    # Meme uncertainty
    if meme_score < 55:

        objections.append(
            "meme identity is not strongly established"
        )

        confidence_penalty += 8

    # Liquidity
    if pair["_liquidity"] < MIN_LIQUIDITY:

        objections.append(
            "liquidity is below minimum"
        )

        confidence_penalty += 20

    # Momentum contradiction
    if momentum >= 70 and pair["_change_5m"] < 0:

        objections.append(
            "momentum score conflicts with current 5m price"
        )

        confidence_penalty += 8

    # Buyer contradiction
    if buyers >= 70 and pair["_buy_pressure"] < 45:

        objections.append(
            "buyer score conflicts with transaction pressure"
        )

        confidence_penalty += 10

    # Risk
    if risk >= 70:

        objections.append(
            "risk is elevated"
        )

        confidence_penalty += 15

    # New market
    if age_score < 40:

        objections.append(
            "market is extremely young"
        )

        confidence_penalty += 10

    # Pump
    if pair["_change_5m"] >= 20:

        objections.append(
            "possible chase situation"
        )

        confidence_penalty += 12

    if not objections:

        objections.append(
            "no major contradiction detected"
        )

    return objections, confidence_penalty


# ===============================================================
# MEMORY BRAIN
# ===============================================================

def get_memory(state, address):

    return state.get(
        "token_memory",
        {}
    ).get(
        address,
        []
    )


def previous_observation(state, address):

    history = get_memory(
        state,
        address
    )

    if not history:
        return None

    return history[-1]


def memory_brain(state, address, current):

    history = get_memory(
        state,
        address
    )

    if not history:

        return {
            "status": "FIRST OBSERVATION",
            "trend": "UNKNOWN",
            "delta_entry": 0,
            "delta_momentum": 0,
            "delta_risk": 0,
            "delta_volume": 0,
        }

    previous = history[-1]

    delta_entry = (
        current["_entry"]
        - safe_float(
            previous.get("entry")
        )
    )

    delta_momentum = (
        current["_momentum"]
        - safe_float(
            previous.get("momentum")
        )
    )

    delta_risk = (
        current["_risk"]
        - safe_float(
            previous.get("risk")
        )
    )

    old_volume = safe_float(
        previous.get("volume_5m")
    )

    current_volume = current["_volume_5m"]

    if old_volume > 0:

        delta_volume = (
            current_volume / old_volume
        )

    else:

        delta_volume = 1

    improving = (
        delta_entry > 5
        and delta_risk <= 5
    )

    deteriorating = (
        delta_entry < -5
        or delta_risk >= 10
    )

    if improving:

        trend = "IMPROVING"

    elif deteriorating:

        trend = "DETERIORATING"

    else:

        trend = "STABLE"

    return {
        "status": "REMEMBERED",
        "trend": trend,
        "delta_entry": delta_entry,
        "delta_momentum": delta_momentum,
        "delta_risk": delta_risk,
        "delta_volume": delta_volume,
    }


def save_observation(
    state,
    address,
    pair
):

    history = state[
        "token_memory"
    ].setdefault(
        address,
        []
    )

    observation = {

        "time": timestamp(),

        "price":
            pair["_price"],

        "volume_5m":
            pair["_volume_5m"],

        "buy_pressure":
            pair["_buy_pressure"],

        "meme":
            pair["_meme"]["score"],

        "quality":
            pair["_quality"],

        "momentum":
            pair["_momentum"],

        "buyers":
            pair["_buyers"],

        "risk":
            pair["_risk"],

        "entry":
            pair["_entry"],

        "confidence":
            pair["_confidence"],

        "decision":
            pair["_decision"],
    }

    history.append(observation)

    if len(history) > MAX_TOKEN_MEMORY:

        del history[
            :-MAX_TOKEN_MEMORY
        ]


# ===============================================================
# TIMING BRAIN
# ===============================================================

def timing_brain(pair, memory):

    score = 50

    reasons = []

    c5 = pair["_change_5m"]

    volume_score = pair["_volume_score"]

    risk = pair["_risk"]

    momentum = pair["_momentum"]

    # Momentum
    if momentum >= 75:

        score += 15

        reasons.append(
            "momentum supports timing"
        )

    elif momentum >= 60:

        score += 8

    elif momentum < 40:

        score -= 12

        reasons.append(
            "momentum is weak"
        )

    # Volume
    if volume_score >= 80:

        score += 15

        reasons.append(
            "volume confirms activity"
        )

    elif volume_score >= 65:

        score += 8

    elif volume_score < 40:

        score -= 10

        reasons.append(
            "volume confirmation weak"
        )

    # Risk
    if risk < 35:

        score += 10

    elif risk >= 70:

        score -= 20

        reasons.append(
            "risk hurts timing"
        )

    # Chasing
    if c5 >= 25:

        score -= 20

        reasons.append(
            "too extended"
        )

    elif c5 >= 15:

        score -= 10

        reasons.append(
            "some chasing risk"
        )

    # Memory
    if memory["trend"] == "IMPROVING":

        score += 12

        reasons.append(
            "historical state improving"
        )

    elif memory["trend"] == "DETERIORATING":

        score -= 12

        reasons.append(
            "historical state deteriorating"
        )

    return int(
        clamp(score)
    ), reasons


# ===============================================================
# FINAL JUDGMENT
# ===============================================================

def final_judgment(pair):

    meme = pair["_meme"]["score"]

    quality = pair["_quality"]

    momentum = pair["_momentum"]

    buyers = pair["_buyers"]

    risk = pair["_risk"]

    timing = pair["_timing"]

    opportunity = pair["_opportunity"]

    confidence = pair["_confidence"]

    reasons = []

    # -----------------------------------------------------------
    # Hard filters
    # -----------------------------------------------------------

    if pair["_liquidity"] < MIN_LIQUIDITY:

        return (
            "AVOID",
            [
                "liquidity below minimum"
            ]
        )

    if pair["_volume_5m"] < MIN_VOLUME_5M:

        return (
            "WAIT",
            [
                "5m volume insufficient"
            ]
        )

    if pair["_volume_1h"] < MIN_VOLUME_1H:

        return (
            "WAIT",
            [
                "1h volume insufficient"
            ]
        )

    if meme < MIN_MEME_SCORE:

        return (
            "AVOID",
            [
                "meme fit below threshold"
            ]
        )

    if risk >= 80:

        return (
            "AVOID",
            [
                "risk too high"
            ]
        )

    # -----------------------------------------------------------
    # Human reasoning
    # -----------------------------------------------------------

    if meme >= 75:

        reasons.append(
            "strong meme identity"
        )

    elif meme >= 55:

        reasons.append(
            "recognizable meme characteristics"
        )

    if quality >= 75:

        reasons.append(
            "strong market quality"
        )

    elif quality >= 55:

        reasons.append(
            "acceptable market quality"
        )

    if momentum >= 75:

        reasons.append(
            "strong momentum"
        )

    elif momentum >= 60:

        reasons.append(
            "constructive momentum"
        )

    if buyers >= 70:

        reasons.append(
            "buyers showing strong control"
        )

    elif buyers >= 60:

        reasons.append(
            "buyers showing control"
        )

    if timing >= 75:

        reasons.append(
            "entry timing favorable"
        )

    elif timing < 50:

        reasons.append(
            "entry timing weak"
        )

    if risk >= 60:

        reasons.append(
            "risk requires caution"
        )

    # -----------------------------------------------------------
    # Decision
    # -----------------------------------------------------------

    if (
        opportunity >= 78
        and timing >= 72
        and confidence >= 70
        and risk < 55
        and momentum >= 60
    ):

        decision = "PAPER ENTER"

    elif (
        opportunity >= 65
        and confidence >= 55
    ):

        decision = "WATCH"

    elif timing < 45:

        decision = "WAIT"

    else:

        decision = "WAIT"

    return decision, reasons


# ===============================================================
# ANALYSIS ENGINE
# ===============================================================

def analyze(pair, state):

    token = pair.get("baseToken") or {}

    address = token.get("address")

    previous = previous_observation(
        state,
        address
    )

    # Brains
    meme = meme_brain(pair)

    quality, quality_reasons = (
        market_brain(pair)
    )

    volume_score, acceleration, volume_label = (
        volume_brain(pair)
    )

    momentum, momentum_reasons = (
        momentum_brain(pair)
    )

    buyers, buyer_reasons = (
        buyer_brain(
            pair,
            previous
        )
    )

    age_score, age_label, age_hours = (
        age_brain(pair)
    )

    risk, risk_reasons = (
        risk_brain(pair)
    )

    skepticism, penalty = (
        skeptic_brain(
            pair,
            meme["score"],
            quality,
            momentum,
            buyers,
            risk,
            age_score
        )
    )

    # Opportunity
    opportunity = (
        meme["score"] * 0.20
        + quality * 0.20
        + momentum * 0.25
        + buyers * 0.15
        + volume_score * 0.10
        + age_score * 0.10
    )

    opportunity = int(
        clamp(opportunity)
    )

    # Memory
    temporary = {
        "_entry": opportunity,
        "_momentum": momentum,
        "_risk": risk,
        "_volume_5m": pair["_volume_5m"],
    }

    memory = memory_brain(
        state,
        address,
        temporary
    )

    pair["_memory"] = memory

    # Timing
    pair["_momentum"] = momentum

    pair["_risk"] = risk

    pair["_volume_score"] = volume_score

    timing, timing_reasons = (
        timing_brain(
            pair,
            memory
        )
    )

    # Entry score
    entry = (
        opportunity * 0.60
        + timing * 0.40
    )

    entry = int(
        clamp(entry)
    )

    # Confidence
    confidence = (
        opportunity * 0.45
        + timing * 0.25
        + quality * 0.15
        + (100 - risk) * 0.15
        - penalty
    )

    confidence = int(
        clamp(confidence)
    )

    pair["_meme"] = meme

    pair["_quality"] = quality

    pair["_quality_reasons"] = (
        quality_reasons
    )

    pair["_volume_score"] = volume_score

    pair["_volume_acceleration"] = (
        acceleration
    )

    pair["_volume_label"] = (
        volume_label
    )

    pair["_momentum"] = momentum

    pair["_momentum_reasons"] = (
        momentum_reasons
    )

    pair["_buyers"] = buyers

    pair["_buyer_reasons"] = (
        buyer_reasons
    )

    pair["_age_score"] = age_score

    pair["_age_label"] = age_label

    pair["_age_hours"] = age_hours

    pair["_risk"] = risk

    pair["_risk_reasons"] = (
        risk_reasons
    )

    pair["_skepticism"] = skepticism

    pair["_skeptic_penalty"] = penalty

    pair["_opportunity"] = opportunity

    pair["_timing"] = timing

    pair["_timing_reasons"] = (
        timing_reasons
    )

    pair["_entry"] = entry

    pair["_confidence"] = confidence

    decision, judgment_reasons = (
        final_judgment(pair)
    )

    pair["_decision"] = decision

    pair["_judgment_reasons"] = (
        judgment_reasons
    )

    return pair


# ===============================================================
# DISPLAY
# ===============================================================

def decision_color(decision):

    if decision == "PAPER ENTER":
        return GREEN

    if decision == "WATCH":
        return YELLOW

    if decision == "AVOID":
        return RED

    return CYAN


def display_pair(pair, number):

    token = pair.get("baseToken") or {}

    name = token.get("name") or "Unknown"

    symbol = token.get("symbol") or "UNKNOWN"

    address = token.get("address") or "UNKNOWN"

    print()

    print(
        f"{MAGENTA}{BOLD}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )

    print(
        f"{WHITE}{BOLD}"
        f"[{number}] {name} ({symbol})"
        f"{RESET}"
    )

    print(
        f"{CYAN}FULL TOKEN ID:{RESET}"
    )

    print(address)

    print(
        f"{CYAN}PAIR:{RESET} "
        f"{pair.get('pairAddress', 'UNKNOWN')}"
    )

    print(
        f"{CYAN}DEX:{RESET} "
        f"{pair.get('dexId', 'UNKNOWN')}"
    )

    print(
        f"{CYAN}PRICE:{RESET} "
        f"{money(pair['_price'])}"
    )

    print()

    print(
        f"{BOLD}{YELLOW}"
        f"🧬 MEME BRAIN"
        f"{RESET}"
    )

    print(
        f"Meme Fit: "
        f"{pair['_meme']['score']}/100"
    )

    print(
        f"Type: "
        f"{pair['_meme']['classification']}"
    )

    if pair["_meme"]["matches"]:

        print(
            "Signals: "
            + ", ".join(
                pair["_meme"]["matches"][:12]
            )
        )

    else:

        print(
            "Signals: none"
        )

    print()

    print(
        f"{BOLD}{BLUE}"
        f"📊 MARKET BRAIN"
        f"{RESET}"
    )

    print(
        f"Liquidity: "
        f"{money(pair['_liquidity'])}"
    )

    print(
        f"5m Volume: "
        f"{money(pair['_volume_5m'])}"
    )

    print(
        f"1h Volume: "
        f"{money(pair['_volume_1h'])}"
    )

    print(
        f"24h Volume: "
        f"{money(pair['_volume_24h'])}"
    )

    print()

    print(
        f"{BOLD}{CYAN}"
        f"📈 MOMENTUM BRAIN"
        f"{RESET}"
    )

    print(
        f"5m: "
        f"{percent(pair['_change_5m'])}"
    )

    print(
        f"1h: "
        f"{percent(pair['_change_1h'])}"
    )

    print(
        f"6h: "
        f"{percent(pair['_change_6h'])}"
    )

    print(
        f"Momentum: "
        f"{pair['_momentum']}/100"
    )

    print(
        f"Volume Acceleration: "
        f"{pair['_volume_acceleration']:.2f}x"
    )

    print(
        f"Volume State: "
        f"{pair['_volume_label']}"
    )

    print()

    print(
        f"{BOLD}{GREEN}"
        f"🟢 BUYER BRAIN"
        f"{RESET}"
    )

    print(
        f"Buys: {pair['_buys']} | "
        f"Sells: {pair['_sells']}"
    )

    print(
        f"Current Buy Pressure: "
        f"{pair['_buy_pressure']:.1f}%"
    )

    print(
        f"Buyer Score: "
        f"{pair['_buyers']}/100"
    )

    print()

    print(
        f"{BOLD}{WHITE}"
        f"🕐 AGE BRAIN"
        f"{RESET}"
    )

    print(
        f"Market Age: "
        f"{pair['_age_hours']:.2f} hours"
    )

    print(
        f"Age Classification: "
        f"{pair['_age_label']}"
    )

    print()

    print(
        f"{BOLD}{RED}"
        f"⚠️ RISK BRAIN"
        f"{RESET}"
    )

    print(
        f"Risk: "
        f"{pair['_risk']}/100"
    )

    if pair["_risk_reasons"]:

        for reason in pair["_risk_reasons"]:

            print(
                f"• {reason}"
            )

    print()

    print(
        f"{BOLD}{MAGENTA}"
        f"🕵️ SKEPTIC BRAIN"
        f"{RESET}"
    )

    for objection in pair["_skepticism"]:

        print(
            f"• {objection}"
        )

    print()

    print(
        f"{BOLD}{CYAN}"
        f"🧠 BRAINIAC MEMORY"
        f"{RESET}"
    )

    memory = pair["_memory"]

    print(
        f"Memory: "
        f"{memory['status']}"
    )

    print(
        f"Trend: "
        f"{memory['trend']}"
    )

    if memory["status"] == "REMEMBERED":

        print(
            f"Entry Score Change: "
            f"{memory['delta_entry']:+.1f}"
        )

        print(
            f"Momentum Change: "
            f"{memory['delta_momentum']:+.1f}"
        )

        print(
            f"Risk Change: "
            f"{memory['delta_risk']:+.1f}"
        )

        print(
            f"5m Volume Change: "
            f"{memory['delta_volume']:.2f}x"
        )

    print()

    print(
        f"{BOLD}{YELLOW}"
        f"🎯 TIMING BRAIN"
        f"{RESET}"
    )

    print(
        f"Opportunity: "
        f"{pair['_opportunity']}/100"
    )

    print(
        f"Entry Timing: "
        f"{pair['_timing']}/100"
    )

    print(
        f"Entry Score: "
        f"{pair['_entry']}/100"
    )

    print(
        f"Confidence: "
        f"{pair['_confidence']}/100"
    )

    print()

    print(
        f"{BOLD}{WHITE}"
        f"🧠 BRAINIAC THINKING"
        f"{RESET}"
    )

    for reason in pair["_judgment_reasons"]:

        print(
            f"• {reason}"
        )

    print()

    color = decision_color(
        pair["_decision"]
    )

    print(
        f"{BOLD}{color}"
        f"FINAL JUDGMENT: "
        f"{pair['_decision']}"
        f"{RESET}"
    )

    print(
        f"{MAGENTA}{BOLD}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )


# ===============================================================
# WATCHLIST
# ===============================================================

def update_watchlist(state, pair):

    token = pair.get("baseToken") or {}

    address = token.get("address")

    if not address:
        return

    decision = pair["_decision"]

    if decision in (
        "WATCH",
        "PAPER ENTER"
    ):

        state["watchlist"][address] = {

            "name":
                token.get("name") or "Unknown",

            "symbol":
                token.get("symbol") or "UNKNOWN",

            "last_seen":
                timestamp(),

            "decision":
                decision,

            "meme":
                pair["_meme"]["score"],

            "opportunity":
                pair["_opportunity"],

            "timing":
                pair["_timing"],

            "risk":
                pair["_risk"],

            "entry":
                pair["_entry"],
        }

    elif decision == "AVOID":

        # Remove from active watchlist if it has
        # clearly deteriorated.
        state["watchlist"].pop(
            address,
            None
        )


# ===============================================================
# PAPER TRADING
# ===============================================================

def paper_enter(state, pair):

    if len(
        state["open_trades"]
    ) >= MAX_OPEN_TRADES:

        return False

    if state["balance"] < PAPER_TRADE_SIZE:

        return False

    token = pair.get("baseToken") or {}

    address = token.get("address")

    if not address:
        return False

    for trade in state["open_trades"]:

        if trade.get(
            "token_address"
        ) == address:

            return False

    price = pair["_price"]

    if price <= 0:
        return False

    trade = {

        "name":
            token.get("name") or "Unknown",

        "symbol":
            token.get("symbol") or "UNKNOWN",

        "token_address":
            address,

        "pair_address":
            pair.get("pairAddress"),

        "entry_price":
            price,

        "amount":
            PAPER_TRADE_SIZE,

        "entry_timestamp":
            time.time(),

        "entry_time":
            timestamp(),

        "meme":
            pair["_meme"]["score"],

        "opportunity":
            pair["_opportunity"],

        "timing":
            pair["_timing"],

        "risk":
            pair["_risk"],

        "entry":
            pair["_entry"],

        "confidence":
            pair["_confidence"],
    }

    state["balance"] -= PAPER_TRADE_SIZE

    state["open_trades"].append(
        trade
    )

    state["total_entries"] += 1

    append_log(
        TRADE_LOG,
        (
            f"{timestamp()} | "
            f"PAPER ENTRY | "
            f"{trade['name']} | "
            f"{trade['symbol']} | "
            f"{address} | "
            f"price={price} | "
            f"meme={trade['meme']} | "
            f"opportunity={trade['opportunity']} | "
            f"timing={trade['timing']} | "
            f"risk={trade['risk']} | "
            f"entry={trade['entry']} | "
            f"confidence={trade['confidence']}"
        )
    )

    return True


def paper_exit(
    state,
    trade,
    current_price,
    reason
):

    entry_price = safe_float(
        trade.get("entry_price")
    )

    amount = safe_float(
        trade.get("amount")
    )

    if entry_price <= 0:
        return

    change = (
        (current_price - entry_price)
        / entry_price
    ) * 100

    exit_value = (
        amount
        * (1 + change / 100)
    )

    pnl = (
        exit_value - amount
    )

    state["balance"] += exit_value

    trade["exit_price"] = current_price

    trade["exit_time"] = timestamp()

    trade["exit_reason"] = reason

    trade["pnl_percent"] = change

    trade["pnl"] = pnl

    state["closed_trades"].append(
        trade
    )

    state["total_exits"] += 1

    append_log(
        TRADE_LOG,
        (
            f"{timestamp()} | "
            f"PAPER EXIT | "
            f"{trade.get('name')} | "
            f"{trade.get('symbol')} | "
            f"{trade.get('token_address')} | "
            f"entry={entry_price} | "
            f"exit={current_price} | "
            f"pnl={pnl:+.4f} | "
            f"change={change:+.2f}% | "
            f"reason={reason}"
        )
    )


# ===============================================================
# POSITION MANAGEMENT
# ===============================================================

def manage_positions(
    state,
    pairs
):

    if not state["open_trades"]:
        return

    lookup = {}

    for pair in pairs:

        token = pair.get(
            "baseToken"
        ) or {}

        address = token.get(
            "address"
        )

        if address:

            lookup[address] = pair

    remaining = []

    for trade in state["open_trades"]:

        address = trade.get(
            "token_address"
        )

        pair = lookup.get(address)

        if not pair:

            remaining.append(trade)
            continue

        current_price = pair["_price"]

        if current_price <= 0:

            remaining.append(trade)
            continue

        entry_price = safe_float(
            trade.get("entry_price")
        )

        change = 0

        if entry_price > 0:

            change = (
                (current_price - entry_price)
                / entry_price
            ) * 100

        age_hours = (
            time.time()
            - safe_float(
                trade.get(
                    "entry_timestamp"
                )
            )
        ) / 3600

        reason = None

        # Deterioration
        if (
            pair["_risk"] >= 85
            and change < -5
        ):

            reason = "risk deterioration"

        # Heavy selling
        elif (
            pair["_buy_pressure"] < 35
            and change < -3
        ):

            reason = "selling pressure"

        # Momentum collapse
        elif (
            pair["_momentum"] < 30
            and change < -3
        ):

            reason = "momentum collapse"

        # Paper profit protection
        elif change >= 15:

            reason = "paper profit protection"

        # Maximum holding time
        elif age_hours >= MAX_HOLD_HOURS:

            reason = "maximum hold time"

        if reason:

            paper_exit(
                state,
                trade,
                current_price,
                reason
            )

            print(
                f"{GREEN}"
                f"PAPER EXIT: "
                f"{trade.get('symbol')} | "
                f"{change:+.2f}% | "
                f"{reason}"
                f"{RESET}"
            )

        else:

            remaining.append(trade)

    state["open_trades"] = remaining


# ===============================================================
# PORTFOLIO
# ===============================================================

def portfolio(state):

    print()

    print(
        f"{BOLD}{MAGENTA}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )

    print(
        f"{BOLD}{WHITE}"
        f"💰 PAPER PORTFOLIO"
        f"{RESET}"
    )

    print(
        f"Available: "
        f"{GREEN}"
        f"{money(state['balance'])}"
        f"{RESET}"
    )

    print(
        f"Open trades: "
        f"{len(state['open_trades'])}/"
        f"{MAX_OPEN_TRADES}"
    )

    print(
        f"Entries: "
        f"{state['total_entries']}"
    )

    print(
        f"Exits: "
        f"{state['total_exits']}"
    )

    print(
        f"Watchlist: "
        f"{len(state['watchlist'])}"
    )

    print(
        f"{BOLD}{MAGENTA}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )


# ===============================================================
# JOURNAL
# ===============================================================

def journal(pair):

    token = pair.get(
        "baseToken"
    ) or {}

    address = token.get(
        "address"
    )

    append_log(
        BRAIN_LOG,
        (
            f"\n"
            f"{timestamp()}\n"
            f"TOKEN: "
            f"{token.get('name', 'Unknown')}\n"
            f"SYMBOL: "
            f"{token.get('symbol', 'UNKNOWN')}\n"
            f"ADDRESS: "
            f"{address}\n"
            f"MEME: "
            f"{pair['_meme']['score']}\n"
            f"QUALITY: "
            f"{pair['_quality']}\n"
            f"MOMENTUM: "
            f"{pair['_momentum']}\n"
            f"BUYERS: "
            f"{pair['_buyers']}\n"
            f"RISK: "
            f"{pair['_risk']}\n"
            f"OPPORTUNITY: "
            f"{pair['_opportunity']}\n"
            f"TIMING: "
            f"{pair['_timing']}\n"
            f"ENTRY: "
            f"{pair['_entry']}\n"
            f"CONFIDENCE: "
            f"{pair['_confidence']}\n"
            f"DECISION: "
            f"{pair['_decision']}\n"
            f"MEMORY: "
            f"{pair['_memory']['trend']}\n"
            f"SKEPTIC: "
            f"{' | '.join(pair['_skepticism'])}\n"
            f"--------------------------------------------"
        )
    )


# ===============================================================
# MAIN SCAN
# ===============================================================

def run_scan(state):

    print(
        f"{CYAN}"
        f"Discovering Solana candidates..."
        f"{RESET}"
    )

    tokens = discover_tokens()

    if not tokens:

        print(
            f"{RED}"
            f"No candidates discovered."
            f"{RESET}"
        )

        return []

    print(
        f"{GREEN}"
        f"Discovered {len(tokens)} candidates."
        f"{RESET}"
    )

    analyzed = []

    for token_data in tokens:

        address = token_data[
            "address"
        ]

        profile = token_data.get(
            "profile"
        ) or {}

        pairs = get_pairs(
            address
        )

        pair = best_pair(
            pairs
        )

        if not pair:
            continue

        pair = prepare_pair(
            pair,
            profile
        )

        if pair["_price"] <= 0:
            continue

        pair = analyze(
            pair,
            state
        )

        analyzed.append(pair)

        state[
            "total_tokens_analyzed"
        ] += 1

        update_watchlist(
            state,
            pair
        )

        journal(pair)

        append_log(
            SEARCH_LOG,
            (
                f"{timestamp()} | "
                f"{pair.get('baseToken', {}).get('name', 'Unknown')} | "
                f"{pair.get('baseToken', {}).get('symbol', 'UNKNOWN')} | "
                f"{address} | "
                f"meme={pair['_meme']['score']} | "
                f"quality={pair['_quality']} | "
                f"momentum={pair['_momentum']} | "
                f"buyers={pair['_buyers']} | "
                f"risk={pair['_risk']} | "
                f"opportunity={pair['_opportunity']} | "
                f"timing={pair['_timing']} | "
                f"entry={pair['_entry']} | "
                f"confidence={pair['_confidence']} | "
                f"decision={pair['_decision']}"
            )
        )

    return analyzed


# ===============================================================
# RANKING
# ===============================================================

def rank_pairs(pairs):

    return sorted(
        pairs,
        key=lambda x: (
            x["_entry"],
            x["_confidence"],
            x["_opportunity"],
            x["_meme"]["score"],
        ),
        reverse=True
    )


# ===============================================================
# HEADER
# ===============================================================

def header(state):

    print(
        f"{BOLD}{MAGENTA}"
        f"╔══════════════════════════════════════════════════════╗"
        f"{RESET}"
    )

    print(
        f"{BOLD}{MAGENTA}"
        f"║              ALVIN MEME GOD V3.0                   ║"
        f"{RESET}"
    )

    print(
        f"{BOLD}{CYAN}"
        f"║                 BRAINIAC ENGINE                    ║"
        f"{RESET}"
    )

    print(
        f"{BOLD}{YELLOW}"
        f"║              PAPER TRADING ONLY                   ║"
        f"{RESET}"
    )

    print(
        f"{BOLD}{MAGENTA}"
        f"╚══════════════════════════════════════════════════════╝"
        f"{RESET}"
    )

    print(
        timestamp()
    )

    print(
        f"Balance: "
        f"{GREEN}"
        f"{money(state['balance'])}"
        f"{RESET}"
    )


# ===============================================================
# MAIN
# ===============================================================

def main():

    state = load_state()

    print(
        f"{GREEN}"
        f"Starting {BOT_NAME} {VERSION}"
        f"{RESET}"
    )

    print(
        f"{YELLOW}"
        f"Paper research mode ACTIVE."
        f"{RESET}"
    )

    time.sleep(1)

    while True:

        try:

            clear_screen()

            header(state)

            # ---------------------------------------------------
            # Refresh open positions
            # ---------------------------------------------------

            position_pairs = []

            for trade in state[
                "open_trades"
            ]:

                address = trade.get(
                    "token_address"
                )

                if not address:
                    continue

                pairs = get_pairs(
                    address
                )

                pair = best_pair(
                    pairs
                )

                if pair:

                    pair = prepare_pair(
                        pair
                    )

                    if pair["_price"] > 0:

                        pair = analyze(
                            pair,
                            state
                        )

                        position_pairs.append(
                            pair
                        )

            manage_positions(
                state,
                position_pairs
            )

            # ---------------------------------------------------
            # New scan
            # ---------------------------------------------------

            print()

            print(
                f"{BLUE}"
                f"🧠 BRAINIAC SCAN STARTING..."
                f"{RESET}"
            )

            pairs = run_scan(
                state
            )

            ranked = rank_pairs(
                pairs
            )

            # ---------------------------------------------------
            # Display all
            # ---------------------------------------------------

            print()

            print(
                f"{BOLD}{GREEN}"
                f"========== BRAINIAC MARKET =========="
                f"{RESET}"
            )

            for number, pair in enumerate(
                ranked,
                start=1
            ):

                display_pair(
                    pair,
                    number
                )

                # Save memory AFTER display
                token = pair.get(
                    "baseToken"
                ) or {}

                address = token.get(
                    "address"
                )

                if address:

                    save_observation(
                        state,
                        address,
                        pair
                    )

            # ---------------------------------------------------
            # Paper entries
            # ---------------------------------------------------

            entered = 0

            for pair in ranked:

                if (
                    pair["_decision"]
                    != "PAPER ENTER"
                ):

                    continue

                if len(
                    state["open_trades"]
                ) >= MAX_OPEN_TRADES:

                    break

                if paper_enter(
                    state,
                    pair
                ):

                    entered += 1

                    token = pair.get(
                        "baseToken"
                    ) or {}

                    print()

                    print(
                        f"{BOLD}{GREEN}"
                        f"🟢 BRAINIAC PAPER ENTRY"
                        f"{RESET}"
                    )

                    print(
                        f"Token: "
                        f"{token.get('name', 'Unknown')}"
                    )

                    print(
                        f"Symbol: "
                        f"{token.get('symbol', 'UNKNOWN')}"
                    )

                    print(
                        f"Full ID: "
                        f"{token.get('address')}"
                    )

                    print(
                        f"Opportunity: "
                        f"{pair['_opportunity']}"
                    )

                    print(
                        f"Timing: "
                        f"{pair['_timing']}"
                    )

                    print(
                        f"Confidence: "
                        f"{pair['_confidence']}"
                    )

            if entered == 0:

                print()

                print(
                    f"{YELLOW}"
                    f"No new paper entries."
                    f"{RESET}"
                )

            portfolio(state)

            save_state(state)

            print()

            print(
                f"{CYAN}"
                f"Scan #{state['total_scans']} complete."
                f"{RESET}"
            )

            # Increment after successful scan.
            state["total_scans"] += 1

            save_state(state)

            print(
                f"{CYAN}"
                f"Next Brainiac scan in "
                f"{SCAN_INTERVAL} seconds..."
                f"{RESET}"
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print()

            print(
                f"{YELLOW}"
                f"ALVIN MEME GOD stopped."
                f"{RESET}"
            )

            save_state(
                state
            )

            break

        except Exception as e:

            print()

            print(
                f"{RED}"
                f"ENGINE ERROR: {e}"
                f"{RESET}"
            )

            save_state(
                state
            )

            time.sleep(10)


# ===============================================================
# START
# ===============================================================

if __name__ == "__main__":

    main()
