#!/usr/bin/env python3

"""
============================================================
             ALVIN MEME GOD V7.1
        SMART EARLY-SIGNAL PAPER ENGINE
============================================================

PUBLIC DATA + PAPER TRADING ONLY

Features:
- DexScreener public market data
- Rate-limit protection
- Candidate pre-filtering
- Volume acceleration
- Buy-pressure acceleration
- Transaction acceleration
- Liquidity monitoring
- Early breakout detection
- Pullback/recovery detection
- Anti-chasing protection
- Quality score
- Entry score
- Risk score
- Adaptive runner trailing
- 2X / 5X / 10X / 50X / 100X milestones
- Missed-runner tracking
- Persistent state
- Colorful Termux dashboard
============================================================
"""

import json
import os
import time
import requests


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"


def C(color, text):
    return f"{color}{text}{RESET}"


def score_color(score):
    if score >= 80:
        return BRIGHT_GREEN
    if score >= 70:
        return GREEN
    if score >= 60:
        return YELLOW
    return RED


def risk_color(risk):
    if risk >= 40:
        return BRIGHT_RED
    if risk >= 25:
        return YELLOW
    return GREEN


def pressure_color(value):
    if value >= 0.65:
        return BRIGHT_GREEN
    if value >= 0.55:
        return YELLOW
    return BRIGHT_RED


def change_color(value):
    if value > 0:
        return BRIGHT_GREEN
    if value < 0:
        return BRIGHT_RED
    return WHITE


# ============================================================
# CONFIGURATION
# ============================================================

BOT_NAME = "ALVIN MEME GOD V7.1"

BASE_URL = "https://api.dexscreener.com"
CHAIN = "solana"

# Scanning
SCAN_INTERVAL = 10
REQUEST_DELAY = 0.30
RATE_LIMIT_SLEEP = 20

# Paper account
STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# Candidate filters
MIN_LIQUIDITY = 25_000
MIN_VOLUME_5M = 5_000
MIN_BUY_PRESSURE = 58

# Scores
QUALITY_SCORE_MIN = 60
ENTRY_SCORE_MIN = 72
WATCH_SCORE = 55

# Anti-chasing
MAX_ENTRY_SPIKE_5M = 20.0

# User requested wide paper stop
INITIAL_STOP = -0.50

# Maximum paper holding period
MAX_HOLD_HOURS = 6

# Maximum candidates deeply analysed each scan
MAX_DEEP_ANALYSIS = 15

# Adaptive runner protection
#
# threshold = profit multiple
# protection = maximum drawdown from peak
#
TRAILING_LEVELS = [
    (0.15, 0.25),
    (0.30, 0.20),
    (1.00, 0.18),
    (2.00, 0.15),
    (5.00, 0.12),
    (10.00, 0.10),
    (50.00, 0.08),
]

MILESTONES = [
    (2.0, "2X"),
    (5.0, "5X"),
    (10.0, "10X"),
    (50.0, "50X"),
    (100.0, "100X"),
]


# ============================================================
# FILES
# ============================================================

TARGETS_FILE = "MEME_GOD_V7_1_TARGETS.txt"
TRADES_FILE = "MEME_GOD_V7_1_TRADES.txt"
STATS_FILE = "MEME_GOD_V7_1_STATS.txt"
MISSED_FILE = "MEME_GOD_V7_1_MISSED_RUNNERS.txt"
STATE_FILE = "MEME_GOD_V7_1_STATE.json"


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD-PAPER/7.1",
    "Accept": "application/json",
})


# ============================================================
# STATE
# ============================================================

state = {
    "balance": STARTING_BALANCE,

    "open_trades": {},

    "closed_trades": [],

    "observations": {},

    "missed_candidates": {},

    "milestones": {
        "2X": 0,
        "5X": 0,
        "10X": 0,
        "50X": 0,
        "100X": 0,
    },

    "stats": {
        "scans": 0,
        "api_calls": 0,
        "rate_limits": 0,
        "entries": 0,
        "exits": 0,
        "wins": 0,
        "losses": 0,
        "missed_candidates": 0,
        "missed_runners": 0,
    },
}


# ============================================================
# TIME / FILE HELPERS
# ============================================================

def now():
    return time.strftime(
        "%Y-%m-%d %H:%M:%S",
        time.localtime()
    )


def safe_float(value, default=0.0):

    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def write_line(filename, text):

    try:
        with open(
            filename,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(text + "\n")

    except Exception as e:

        print(
            C(
                BRIGHT_RED,
                f"File write error: {e}"
            )
        )


# ============================================================
# STATE MANAGEMENT
# ============================================================

def save_state():

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
            C(
                BRIGHT_RED,
                f"State save error: {e}"
            )
        )


def load_state():

    global state

    if not os.path.exists(STATE_FILE):
        return

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            saved = json.load(f)

        if not isinstance(saved, dict):
            return

        for key, value in saved.items():

            state[key] = value

    except Exception as e:

        print(
            C(
                BRIGHT_YELLOW,
                f"State load warning: {e}"
            )
        )


def repair_state():

    state.setdefault(
        "balance",
        STARTING_BALANCE
    )

    state.setdefault(
        "open_trades",
        {}
    )

    state.setdefault(
        "closed_trades",
        []
    )

    state.setdefault(
        "observations",
        {}
    )

    state.setdefault(
        "missed_candidates",
        {}
    )

    state.setdefault(
        "milestones",
        {}
    )

    state.setdefault(
        "stats",
        {}
    )

    for key in [
        "2X",
        "5X",
        "10X",
        "50X",
        "100X",
    ]:

        state["milestones"].setdefault(
            key,
            0
        )

    for key in [
        "scans",
        "api_calls",
        "rate_limits",
        "entries",
        "exits",
        "wins",
        "losses",
        "missed_candidates",
        "missed_runners",
    ]:

        state["stats"].setdefault(
            key,
            0
        )


# ============================================================
# API
# ============================================================

def api_get(endpoint):

    url = BASE_URL + endpoint

    try:

        time.sleep(REQUEST_DELAY)

        response = session.get(
            url,
            timeout=15
        )

        state["stats"]["api_calls"] += 1

        if response.status_code == 429:

            state["stats"]["rate_limits"] += 1

            print()
            print(
                C(
                    BRIGHT_RED,
                    "⚠ RATE LIMITED — COOLING DOWN"
                )
            )

            time.sleep(
                RATE_LIMIT_SLEEP
            )

            return None

        if response.status_code != 200:

            return None

        return response.json()

    except requests.RequestException:

        return None

    except Exception:

        return None


# ============================================================
# TOKEN DISCOVERY
# ============================================================

def discover_tokens():

    endpoints = [
        "/token-profiles/latest/v1",
        "/token-boosts/latest/v1",
        "/token-boosts/top/v1",
    ]

    discovered = {}

    for endpoint in endpoints:

        data = api_get(endpoint)

        if not isinstance(data, list):
            continue

        for item in data:

            if not isinstance(item, dict):
                continue

            if item.get("chainId") != CHAIN:
                continue

            address = item.get(
                "tokenAddress"
            )

            if not address:
                continue

            discovered[address] = item

    return list(
        discovered.keys()
    )


# ============================================================
# PAIR LOOKUP
# ============================================================

def get_pairs(address):

    data = api_get(
        f"/token-pairs/v1/{CHAIN}/{address}"
    )

    if not isinstance(data, list):

        return []

    return data


def choose_best_pair(pairs):

    if not pairs:
        return None

    valid = []

    for pair in pairs:

        if not isinstance(pair, dict):
            continue

        liquidity = safe_float(
            pair.get(
                "liquidity",
                {}
            ).get("usd")
        )

        volume = safe_float(
            pair.get(
                "volume",
                {}
            ).get("h24")
        )

        if liquidity <= 0:
            continue

        valid.append(
            (
                liquidity,
                volume,
                pair
            )
        )

    if not valid:
        return None

    valid.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    return valid[0][2]


# ============================================================
# NORMALIZE PAIR
# ============================================================

def normalize(pair):

    if not pair:
        return None

    txns = pair.get(
        "txns",
        {}
    )

    m5 = txns.get(
        "m5",
        {}
    )

    h1 = txns.get(
        "h1",
        {}
    )

    h6 = txns.get(
        "h6",
        {}
    )

    h24 = txns.get(
        "h24",
        {}
    )

    buys_5m = safe_float(
        m5.get("buys")
    )

    sells_5m = safe_float(
        m5.get("sells")
    )

    buys_1h = safe_float(
        h1.get("buys")
    )

    sells_1h = safe_float(
        h1.get("sells")
    )

    buys_6h = safe_float(
        h6.get("buys")
    )

    sells_6h = safe_float(
        h6.get("sells")
    )

    buys_24h = safe_float(
        h24.get("buys")
    )

    sells_24h = safe_float(
        h24.get("sells")
    )

    total_5m = (
        buys_5m +
        sells_5m
    )

    total_1h = (
        buys_1h +
        sells_1h
    )

    total_6h = (
        buys_6h +
        sells_6h
    )

    total_24h = (
        buys_24h +
        sells_24h
    )

    buy_pressure = (
        buys_5m / total_5m
        if total_5m > 0
        else 0
    )

    buy_pressure_1h = (
        buys_1h / total_1h
        if total_1h > 0
        else 0
    )

    buy_pressure_6h = (
        buys_6h / total_6h
        if total_6h > 0
        else 0
    )

    price_change = pair.get(
        "priceChange",
        {}
    )

    price_5m = safe_float(
        price_change.get("m5")
    )

    price_1h = safe_float(
        price_change.get("h1")
    )

    price_6h = safe_float(
        price_change.get("h6")
    )

    price_24h = safe_float(
        price_change.get("h24")
    )

    volume = pair.get(
        "volume",
        {}
    )

    volume_5m = safe_float(
        volume.get("m5")
    )

    volume_1h = safe_float(
        volume.get("h1")
    )

    volume_6h = safe_float(
        volume.get("h6")
    )

    volume_24h = safe_float(
        volume.get("h24")
    )

    liquidity = safe_float(
        pair.get(
            "liquidity",
            {}
        ).get("usd")
    )

    fdv = safe_float(
        pair.get("fdv")
    )

    price = safe_float(
        pair.get("priceUsd")
    )

    base = pair.get(
        "baseToken",
        {}
    )

    symbol = base.get(
        "symbol",
        "UNKNOWN"
    )

    name = base.get(
        "name",
        symbol
    )

    address = base.get(
        "address",
        ""
    )

    pair_address = pair.get(
        "pairAddress",
        ""
    )

    return {
        "symbol": symbol,
        "name": name,
        "address": address,
        "pair_address": pair_address,

        "price": price,

        "liquidity": liquidity,
        "fdv": fdv,

        "volume_5m": volume_5m,
        "volume_1h": volume_1h,
        "volume_6h": volume_6h,
        "volume_24h": volume_24h,

        "buys_5m": buys_5m,
        "sells_5m": sells_5m,

        "buys_1h": buys_1h,
        "sells_1h": sells_1h,

        "buys_6h": buys_6h,
        "sells_6h": sells_6h,

        "buys_24h": buys_24h,
        "sells_24h": sells_24h,

        "txns_5m": total_5m,
        "txns_1h": total_1h,
        "txns_6h": total_6h,
        "txns_24h": total_24h,

        "buy_pressure": buy_pressure,
        "buy_pressure_1h": buy_pressure_1h,
        "buy_pressure_6h": buy_pressure_6h,

        "price_5m": price_5m,
        "price_1h": price_1h,
        "price_6h": price_6h,
        "price_24h": price_24h,

        "url": pair.get(
            "url",
            ""
        ),
    }


# ============================================================
# OBSERVATION HISTORY
# ============================================================

def get_history(address):

    if address not in state["observations"]:

        state["observations"][address] = []

    return state["observations"][address]


def add_observation(data):

    address = data["address"]

    history = get_history(
        address
    )

    history.append({
        "time": time.time(),

        "price": data["price"],

        "volume_5m": data["volume_5m"],

        "buy_pressure": data["buy_pressure"],

        "txns_5m": data["txns_5m"],

        "liquidity": data["liquidity"],

        "price_5m": data["price_5m"],
    })

    # Keep last 12 observations
    state["observations"][address] = (
        history[-12:]
    )


def previous_observation(data):

    history = get_history(
        data["address"]
    )

    if len(history) < 2:

        return None

    return history[-2]


# ============================================================
# ACCELERATION ENGINE
# ============================================================

def acceleration(data):

    previous = previous_observation(
        data
    )

    result = {
        "volume_accel": 0.0,
        "buy_accel": 0.0,
        "txn_accel": 0.0,
        "liquidity_change": 0.0,
        "price_accel": 0.0,
    }

    if not previous:

        return result

    old_volume = safe_float(
        previous.get("volume_5m")
    )

    old_buy = safe_float(
        previous.get("buy_pressure")
    )

    old_txns = safe_float(
        previous.get("txns_5m")
    )

    old_liq = safe_float(
        previous.get("liquidity")
    )

    old_price = safe_float(
        previous.get("price")
    )

    if old_volume > 0:

        result["volume_accel"] = (
            data["volume_5m"] /
            old_volume
        ) - 1

    result["buy_accel"] = (
        data["buy_pressure"] -
        old_buy
    )

    if old_txns > 0:

        result["txn_accel"] = (
            data["txns_5m"] /
            old_txns
        ) - 1

    if old_liq > 0:

        result["liquidity_change"] = (
            data["liquidity"] /
            old_liq
        ) - 1

    if old_price > 0:

        result["price_accel"] = (
            data["price"] /
            old_price
        ) - 1

    return result


# ============================================================
# RISK ENGINE
# ============================================================

def risk_score(data):

    risk = 0
    reasons = []

    if data["liquidity"] < 15_000:

        risk += 30

        reasons.append(
            "VERY LOW LIQUIDITY"
        )

    elif data["liquidity"] < MIN_LIQUIDITY:

        risk += 20

        reasons.append(
            "LOW LIQUIDITY"
        )

    if data["price_5m"] > 40:

        risk += 25

        reasons.append(
            "EXTREME 5M SPIKE"
        )

    elif data["price_5m"] > MAX_ENTRY_SPIKE_5M:

        risk += 12

        reasons.append(
            "LARGE 5M SPIKE"
        )

    if data["buy_pressure"] < 0.45:

        risk += 25

        reasons.append(
            "SELL PRESSURE"
        )

    elif data["buy_pressure"] < 0.52:

        risk += 12

        reasons.append(
            "WEAK BUY PRESSURE"
        )

    if (
        data["volume_1h"] > 0
        and
        data["volume_5m"]
        <
        data["volume_1h"] * 0.01
    ):

        risk += 10

        reasons.append(
            "VOLUME COLLAPSE"
        )

    return risk, reasons


# ============================================================
# QUALITY SCORE
# ============================================================

def quality_score(data):

    score = 0

    reasons = []

    # Liquidity
    if data["liquidity"] >= 250_000:

        score += 15

    elif data["liquidity"] >= 100_000:

        score += 12

    elif data["liquidity"] >= 50_000:

        score += 9

    elif data["liquidity"] >= MIN_LIQUIDITY:

        score += 6

    else:

        reasons.append(
            "LOW LIQUIDITY"
        )

    # 5M volume
    if data["volume_5m"] >= 50_000:

        score += 15

    elif data["volume_5m"] >= 20_000:

        score += 12

    elif data["volume_5m"] >= 10_000:

        score += 9

    elif data["volume_5m"] >= MIN_VOLUME_5M:

        score += 5

    else:

        reasons.append(
            "LOW 5M VOLUME"
        )

    # Buy pressure
    if data["buy_pressure"] >= 0.70:

        score += 15

    elif data["buy_pressure"] >= 0.64:

        score += 12

    elif data["buy_pressure"] >= 0.58:

        score += 9

    elif data["buy_pressure"] >= 0.52:

        score += 5

    else:

        reasons.append(
            "WEAK BUY PRESSURE"
        )

    # Momentum
    if data["price_5m"] >= 10:

        score += 15

    elif data["price_5m"] >= 5:

        score += 12

    elif data["price_5m"] >= 2:

        score += 9

    elif data["price_5m"] >= 0:

        score += 5

    # 1H trend
    if data["price_1h"] >= 30:

        score += 15

    elif data["price_1h"] >= 15:

        score += 12

    elif data["price_1h"] >= 5:

        score += 9

    elif data["price_1h"] >= 0:

        score += 5

    acc = acceleration(data)

    # Volume acceleration
    if acc["volume_accel"] >= 2:

        score += 10

    elif acc["volume_accel"] >= 0.75:

        score += 8

    elif acc["volume_accel"] >= 0.25:

        score += 5

    # Buy acceleration
    if acc["buy_accel"] >= 0.10:

        score += 10

    elif acc["buy_accel"] >= 0.05:

        score += 7

    elif acc["buy_accel"] > 0:

        score += 4

    # Structure
    if (
        data["price_1h"] > 0
        and
        data["price_5m"] > 0
    ):

        score += 5

    return min(
        score,
        100
    ), reasons


# ============================================================
# SMART EARLY SIGNAL
# ============================================================

def early_signal(data):

    acc = acceleration(data)

    score = 0

    reasons = []

    # Volume
    if acc["volume_accel"] >= 2.0:

        score += 20

        reasons.append(
            "VOLUME SURGE"
        )

    elif acc["volume_accel"] >= 0.75:

        score += 14

        reasons.append(
            "VOLUME ACCELERATION"
        )

    elif acc["volume_accel"] >= 0.25:

        score += 8

        reasons.append(
            "VOLUME RISING"
        )

    # Buy pressure
    if acc["buy_accel"] >= 0.12:

        score += 20

        reasons.append(
            "BUY PRESSURE ACCELERATING"
        )

    elif acc["buy_accel"] >= 0.06:

        score += 14

        reasons.append(
            "BUY PRESSURE RISING"
        )

    elif acc["buy_accel"] > 0:

        score += 7

    # Transactions
    if acc["txn_accel"] >= 2:

        score += 20

        reasons.append(
            "TRANSACTION SURGE"
        )

    elif acc["txn_accel"] >= 0.75:

        score += 14

        reasons.append(
            "TRANSACTIONS ACCELERATING"
        )

    elif acc["txn_accel"] >= 0.25:

        score += 7

    # Liquidity
    if data["liquidity"] >= 100_000:

        score += 10

    elif data["liquidity"] >= MIN_LIQUIDITY:

        score += 5

    # Early breakout
    if (
        data["price_5m"] >= 3
        and
        data["price_5m"] <= MAX_ENTRY_SPIKE_5M
        and
        data["buy_pressure"] >= 0.60
    ):

        score += 15

        reasons.append(
            "EARLY BREAKOUT"
        )

    # Recovery structure
    if (
        data["price_1h"] > 0
        and
        data["price_5m"] > 0
        and
        data["buy_pressure"] >= 0.60
    ):

        score += 5

        reasons.append(
            "RECOVERY STRUCTURE"
        )

    # Anti-chasing
    if data["price_5m"] > 35:

        score -= 25

        reasons.append(
            "ANTI-CHASE"
        )

    return (
        max(0, min(score, 100)),
        reasons
    )


# ============================================================
# ENTRY SCORE
# ============================================================

def entry_score(data):

    quality, _ = quality_score(
        data
    )

    early, early_reasons = early_signal(
        data
    )

    risk, risk_reasons = risk_score(
        data
    )

    score = (
        quality * 0.45
        +
        early * 0.55
    )

    reasons = list(
        early_reasons
    )

    if data["buy_pressure"] >= 0.65:

        score += 5

        reasons.append(
            "STRONG BUY PRESSURE"
        )

    if data["price_1h"] > 0:

        score += 3

    if data["txns_5m"] >= 50:

        score += 4

        reasons.append(
            "ACTIVE TRADING"
        )

    if data["price_5m"] > MAX_ENTRY_SPIKE_5M:

        score -= 20

        reasons.append(
            "TOO EXTENDED"
        )

    if risk >= 40:

        score -= 30

    elif risk >= 25:

        score -= 10

    return (
        max(0, min(score, 100)),
        reasons,
        risk,
        risk_reasons
    )


# ============================================================
# CANDIDATE ANALYSIS
# ============================================================

def analyze(address):

    pairs = get_pairs(
        address
    )

    pair = choose_best_pair(
        pairs
    )

    if not pair:

        return None

    data = normalize(
        pair
    )

    if not data:

        return None

    add_observation(
        data
    )

    quality, quality_reasons = (
        quality_score(data)
    )

    early, early_reasons = (
        early_signal(data)
    )

    entry, entry_reasons, risk, risk_reasons = (
        entry_score(data)
    )

    data["quality"] = quality

    data["early"] = early

    data["entry"] = entry

    data["risk"] = risk

    data["quality_reasons"] = (
        quality_reasons
    )

    data["early_reasons"] = (
        early_reasons
    )

    data["entry_reasons"] = (
        entry_reasons
    )

    data["risk_reasons"] = (
        risk_reasons
    )

    acc = acceleration(
        data
    )

    data["volume_accel"] = (
        acc["volume_accel"]
    )

    data["buy_accel"] = (
        acc["buy_accel"]
    )

    data["txn_accel"] = (
        acc["txn_accel"]
    )

    data["liquidity_change"] = (
        acc["liquidity_change"]
    )

    return data


# ============================================================
# CANDIDATE PREFILTER
# ============================================================

def prefilter(addresses):

    ranked = []

    for address in addresses:

        history = get_history(
            address
        )

        if not history:

            priority = 100_000

        else:

            last = history[-1]

            volume = safe_float(
                last.get(
                    "volume_5m"
                )
            )

            pressure = safe_float(
                last.get(
                    "buy_pressure"
                )
            )

            txns = safe_float(
                last.get(
                    "txns_5m"
                )
            )

            priority = (
                volume
                +
                pressure * 10_000
                +
                txns * 50
            )

        ranked.append(
            (
                priority,
                address
            )
        )

    ranked.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        address
        for _, address in
        ranked[:MAX_DEEP_ANALYSIS]
    ]


# ============================================================
# PAPER ENTRY
# ============================================================

def can_enter(data):

    if len(
        state["open_trades"]
    ) >= MAX_OPEN_TRADES:

        return False, "MAX OPEN TRADES"

    if (
        state["balance"]
        <
        PAPER_TRADE_SIZE
    ):

        return False, "LOW PAPER BALANCE"

    if data["quality"] < QUALITY_SCORE_MIN:

        return False, "QUALITY TOO LOW"

    if data["entry"] < ENTRY_SCORE_MIN:

        return False, "NO VALID SETUP"

    if data["risk"] >= 40:

        return False, "HIGH RISK"

    if data["liquidity"] < MIN_LIQUIDITY:

        return False, "LOW LIQUIDITY"

    if data["volume_5m"] < MIN_VOLUME_5M:

        return False, "LOW 5M VOLUME"

    if (
        data["buy_pressure"]
        <
        MIN_BUY_PRESSURE / 100
    ):

        return False, "WEAK BUY PRESSURE"

    if (
        data["price_5m"]
        >
        MAX_ENTRY_SPIKE_5M
    ):

        return False, "CHASING SPIKE"

    return True, "ENTRY CONFIRMED"


def paper_enter(data):

    allowed, reason = can_enter(
        data
    )

    if not allowed:

        return False

    address = data["address"]

    if address in state["open_trades"]:

        return False

    entry_price = data["price"]

    trade = {

        "address": address,

        "symbol": data["symbol"],

        "name": data["name"],

        "pair_address": (
            data["pair_address"]
        ),

        "entry_price": entry_price,

        "entry_time": time.time(),

        "size": PAPER_TRADE_SIZE,

        "highest_multiple": 1.0,

        "highest_price": entry_price,

        "milestones": [],

        "quality": data["quality"],

        "early_score": data["early"],

        "entry_score": data["entry"],

        "risk": data["risk"],

        "initial_stop": INITIAL_STOP,

        "status": "OPEN",
    }

    state["balance"] -= (
        PAPER_TRADE_SIZE
    )

    state["open_trades"][
        address
    ] = trade

    state["stats"]["entries"] += 1

    write_line(
        TRADES_FILE,
        (
            f"{now()} | "
            f"PAPER ENTRY | "
            f"{data['symbol']} | "
            f"price={entry_price:.12f} | "
            f"Q={data['quality']} | "
            f"Early={data['early']} | "
            f"E={data['entry']:.1f} | "
            f"Risk={data['risk']} | "
            f"reason={reason} | "
            f"address={address}"
        )
    )

    print()
    print(
        C(
            BRIGHT_GREEN,
            "🚀 PAPER ENTRY: "
        )
        +
        C(
            BOLD + BRIGHT_WHITE,
            data["symbol"]
        )
    )

    print(
        C(
            GREEN,
            f"   Entry ${entry_price:.12f}"
        )
    )

    print(
        C(
            GREEN,
            f"   Quality {data['quality']} | "
            f"Early {data['early']} | "
            f"Entry {data['entry']:.0f}"
        )
    )

    save_state()

    return True


# ============================================================
# TRAILING PROTECTION
# ============================================================

def get_trailing_protection(
    profit
):

    protection = None

    for threshold, value in (
        TRAILING_LEVELS
    ):

        if profit >= threshold:

            protection = value

    return protection


# ============================================================
# EXIT ENGINE
# ============================================================

def evaluate_exit(
    trade,
    data
):

    entry_price = (
        trade["entry_price"]
    )

    current_price = (
        data["price"]
    )

    if entry_price <= 0:

        return False, ""

    mult = (
        current_price /
        entry_price
    )

    profit = mult - 1

    # --------------------------------------------------------
    # Highest price
    # --------------------------------------------------------

    if (
        current_price
        >
        trade["highest_price"]
    ):

        trade["highest_price"] = (
            current_price
        )

    trade["highest_multiple"] = max(
        trade["highest_multiple"],
        mult
    )

    # --------------------------------------------------------
    # Milestones
    # --------------------------------------------------------

    for threshold, label in MILESTONES:

        if (
            mult >= threshold
            and
            label not in trade["milestones"]
        ):

            trade["milestones"].append(
                label
            )

            state["milestones"][
                label
            ] += 1

            write_line(
                TARGETS_FILE,
                (
                    f"{now()} | "
                    f"{label} | "
                    f"{data['symbol']} | "
                    f"multiple={mult:.2f}X | "
                    f"price={current_price:.12f} | "
                    f"address={data['address']}"
                )
            )

            print()
            print(
                C(
                    BRIGHT_MAGENTA,
                    f"🎯 {label} MILESTONE: "
                )
                +
                C(
                    BOLD + BRIGHT_WHITE,
                    data["symbol"]
                )
            )

    # --------------------------------------------------------
    # Initial stop
    # --------------------------------------------------------

    if profit <= INITIAL_STOP:

        return (
            True,
            "INITIAL STOP"
        )

    # --------------------------------------------------------
    # Adaptive trailing
    # --------------------------------------------------------

    protection = (
        get_trailing_protection(
            profit
        )
    )

    if protection is not None:

        peak = (
            trade["highest_price"]
        )

        if peak > 0:

            drawdown = (
                current_price /
                peak
            ) - 1

            if drawdown <= -protection:

                return (
                    True,
                    (
                        "TRAILING EXIT "
                        f"peak="
                        f"{trade['highest_multiple']:.2f}X"
                    )
                )

    # --------------------------------------------------------
    # Momentum deterioration
    # --------------------------------------------------------

    if profit > 0.15:

        if (
            data["buy_pressure"]
            <
            0.45
        ):

            return (
                True,
                "BUY PRESSURE COLLAPSE"
            )

        if (
            data["price_5m"] < -10
            and
            data["volume_5m"]
            <
            MIN_VOLUME_5M
        ):

            return (
                True,
                "MOMENTUM + VOLUME COLLAPSE"
            )

    # --------------------------------------------------------
    # Maximum hold
    # --------------------------------------------------------

    age_hours = (
        time.time()
        -
        trade["entry_time"]
    ) / 3600

    if age_hours >= MAX_HOLD_HOURS:

        return (
            True,
            "MAX HOLD TIME"
        )

    return False, ""


# ============================================================
# PAPER EXIT
# ============================================================

def paper_exit(
    address,
    data,
    reason
):

    trade = state[
        "open_trades"
    ].get(address)

    if not trade:

        return

    entry_price = (
        trade["entry_price"]
    )

    exit_price = (
        data["price"]
    )

    if entry_price <= 0:

        return

    mult = (
        exit_price /
        entry_price
    )

    pnl_pct = mult - 1

    pnl_cash = (
        PAPER_TRADE_SIZE *
        pnl_pct
    )

    state["balance"] += (
        PAPER_TRADE_SIZE
        +
        pnl_cash
    )

    trade["exit_price"] = (
        exit_price
    )

    trade["exit_time"] = (
        time.time()
    )

    trade["exit_reason"] = (
        reason
    )

    trade["pnl_pct"] = (
        pnl_pct
    )

    trade["pnl_cash"] = (
        pnl_cash
    )

    trade["status"] = "CLOSED"

    state["closed_trades"].append(
        trade
    )

    del state[
        "open_trades"
    ][address]

    state["stats"]["exits"] += 1

    if pnl_cash >= 0:

        state["stats"]["wins"] += 1

        result_color = (
            BRIGHT_GREEN
        )

    else:

        state["stats"]["losses"] += 1

        result_color = (
            BRIGHT_RED
        )

    write_line(
        TRADES_FILE,
        (
            f"{now()} | "
            f"PAPER EXIT | "
            f"{data['symbol']} | "
            f"multiple={mult:.2f}X | "
            f"PnL={pnl_pct * 100:.2f}% | "
            f"cash={pnl_cash:.2f} | "
            f"reason={reason} | "
            f"address={address}"
        )
    )

    print()
    print(
        C(
            result_color,
            "🏁 PAPER EXIT: "
        )
        +
        C(
            BOLD + BRIGHT_WHITE,
            data["symbol"]
        )
    )

    print(
        C(
            result_color,
            f"   {mult:.2f}X | "
            f"PnL {pnl_pct * 100:+.2f}% | "
            f"${pnl_cash:+.2f}"
        )
    )

    print(
        C(
            YELLOW,
            f"   Reason: {reason}"
        )
    )

    save_state()


# ============================================================
# MISSED RUNNER TRACKER
# ============================================================

def track_missed_candidate(
    data
):

    address = data["address"]

    if address in state["open_trades"]:

        return

    # Don't waste memory on weak candidates
    if (
        data["quality"] < WATCH_SCORE
        and
        data["entry"] < ENTRY_SCORE_MIN
    ):

        return

    existing = (
        state["missed_candidates"]
    )

    if address not in existing:

        existing[address] = {

            "symbol": data["symbol"],

            "address": address,

            "start_price": data["price"],

            "start_time": time.time(),

            "highest_multiple": 1.0,

            "logged_2x": False,

            "last_price": data["price"],
        }

        state["stats"][
            "missed_candidates"
        ] += 1

    item = existing[address]

    start_price = safe_float(
        item.get(
            "start_price"
        )
    )

    if start_price <= 0:

        return

    mult = (
        data["price"] /
        start_price
    )

    if (
        mult >
        item["highest_multiple"]
    ):

        item["highest_multiple"] = (
            mult
        )

    item["last_price"] = (
        data["price"]
    )

    # Log first 2X
    if (
        mult >= 2
        and
        not item["logged_2x"]
    ):

        item["logged_2x"] = True

        state["stats"][
            "missed_runners"
        ] += 1

        write_line(
            MISSED_FILE,
            (
                f"{now()} | "
                f"MISSED RUNNER | "
                f"{data['symbol']} | "
                f"2X+ | "
                f"multiple={mult:.2f}X | "
                f"quality={data['quality']} | "
                f"early={data['early']} | "
                f"entry={data['entry']:.1f} | "
                f"risk={data['risk']} | "
                f"address={address}"
            )
        )

        print()
        print(
            C(
                BRIGHT_YELLOW,
                "👀 MISSED RUNNER: "
            )
            +
            C(
                BOLD + BRIGHT_WHITE,
                f"{data['symbol']} "
            )
            +
            C(
                BRIGHT_GREEN,
                f"{mult:.2f}X"
            )
        )

    # Keep database manageable
    if len(existing) > 1000:

        weakest = sorted(
            existing.items(),
            key=lambda item: item[1].get(
                "highest_multiple",
                1
            )
        )

        for old_address, _ in (
            weakest[:200]
        ):

            del existing[
                old_address
            ]


# ============================================================
# DISPLAY
# ============================================================

def clear_screen():

    os.system("clear")


def banner():

    print(
        C(
            BRIGHT_CYAN,
            "╔" + "═" * 76 + "╗"
        )
    )

    title = (
        "🚀 ALVIN MEME GOD V7.1"
    )

    subtitle = (
        "🧠 SMART EARLY-SIGNAL PAPER ENGINE"
    )

    mode = (
        "⚡ PUBLIC DATA • PAPER TRADING ONLY"
    )

    print(
        C(
            BRIGHT_CYAN,
            "║ "
        )
        +
        C(
            BOLD + BRIGHT_GREEN,
            title
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "║ "
        )
        +
        C(
            BOLD + BRIGHT_YELLOW,
            subtitle
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "║ "
        )
        +
        C(
            BRIGHT_MAGENTA,
            mode
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "╚" + "═" * 76 + "╝"
        )
    )


def display_open_trades():

    print()

    print(
        C(
            BRIGHT_CYAN,
            "━" * 78
        )
    )

    print(
        C(
            BOLD + BRIGHT_CYAN,
            "🚀 OPEN PAPER TRADES"
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "━" * 78
        )
    )

    if not state["open_trades"]:

        print(
            C(
                YELLOW,
                "  NO OPEN PAPER TRADES"
            )
        )

        return

    for trade in (
        state["open_trades"].values()
    ):

        print(
            " "
            +
            C(
                BRIGHT_GREEN,
                f"{trade['symbol']:<14}"
            )
            +
            C(
                WHITE,
                " Entry="
            )
            +
            C(
                CYAN,
                f"{trade['entry_price']:.10f}"
            )
            +
            C(
                WHITE,
                " Peak="
            )
            +
            C(
                BRIGHT_MAGENTA,
                f"{trade['highest_multiple']:.2f}X"
            )
            +
            C(
                WHITE,
                " Q="
            )
            +
            C(
                score_color(
                    trade["quality"]
                ),
                str(
                    trade["quality"]
                )
            )
            +
            C(
                WHITE,
                " E="
            )
            +
            C(
                score_color(
                    trade["entry_score"]
                ),
                f"{trade['entry_score']:.0f}"
            )
        )


def display_candidates(
    candidates
):

    print()

    print(
        C(
            BRIGHT_BLUE,
            "━" * 78
        )
    )

    print(
        C(
            BOLD + BRIGHT_BLUE,
            "🧠 TOP CURRENT CANDIDATES"
        )
    )

    print(
        C(
            BRIGHT_BLUE,
            "━" * 78
        )
    )

    print(
        C(
            WHITE,
            " #   TOKEN           Q      EARLY   ENTRY   RISK   STATUS"
        )
    )

    print(
        C(
            BLUE,
            "─" * 78
        )
    )

    for i, data in enumerate(
        candidates[:10],
        start=1
    ):

        if (
            data["entry"]
            >=
            ENTRY_SCORE_MIN
        ):

            status = C(
                BRIGHT_GREEN,
                "🔥 ENTRY"
            )

        elif data["risk"] >= 40:

            status = C(
                BRIGHT_RED,
                "⚠ HIGH RISK"
            )

        elif (
            data["quality"]
            >=
            QUALITY_SCORE_MIN
        ):

            status = C(
                BRIGHT_YELLOW,
                "👀 WATCH"
            )

        else:

            status = C(
                WHITE,
                "WATCH"
            )

        print(
            f"{i:2}. "
            +
            C(
                BRIGHT_WHITE,
                f"{data['symbol'][:15]:<15}"
            )
            +
            " "
            +
            C(
                score_color(
                    data["quality"]
                ),
                f"{data['quality']:>3}"
            )
            +
            "      "
            +
            C(
                score_color(
                    data["early"]
                ),
                f"{data['early']:>3}"
            )
            +
            "      "
            +
            C(
                score_color(
                    data["entry"]
                ),
                f"{data['entry']:>3.0f}"
            )
            +
            "     "
            +
            C(
                risk_color(
                    data["risk"]
                ),
                f"{data['risk']:>3}"
            )
            +
            "     "
            +
            status
        )


def display_details(
    data
):

    print()

    print(
        C(
            BRIGHT_MAGENTA,
            "╔" + "═" * 76 + "╗"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            BOLD + BRIGHT_WHITE,
            "🔎 SMART MARKET ANALYSIS"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "╠" + "═" * 76 + "╣"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            BRIGHT_CYAN,
            "TOKEN: "
        )
        +
        C(
            BOLD + BRIGHT_WHITE,
            data["symbol"]
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Contract: "
        )
        +
        C(
            CYAN,
            data["address"]
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Price: "
        )
        +
        C(
            BRIGHT_YELLOW,
            f"${data['price']:.12f}"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Liquidity: "
        )
        +
        C(
            BRIGHT_CYAN,
            f"${data['liquidity']:,.0f}"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "5M Volume: "
        )
        +
        C(
            BRIGHT_CYAN,
            f"${data['volume_5m']:,.0f}"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Buys/Sells: "
        )
        +
        C(
            BRIGHT_GREEN,
            str(int(data["buys_5m"]))
        )
        +
        C(
            WHITE,
            " / "
        )
        +
        C(
            BRIGHT_RED,
            str(int(data["sells_5m"]))
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Buy Pressure: "
        )
        +
        C(
            pressure_color(
                data["buy_pressure"]
            ),
            f"{data['buy_pressure'] * 100:.1f}%"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "5M Price: "
        )
        +
        C(
            change_color(
                data["price_5m"]
            ),
            f"{data['price_5m']:+.2f}%"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "1H Price: "
        )
        +
        C(
            change_color(
                data["price_1h"]
            ),
            f"{data['price_1h']:+.2f}%"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "╠" + "═" * 76 + "╣"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            BOLD + BRIGHT_YELLOW,
            "⚡ SMART EARLY SIGNAL"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Volume Acceleration: "
        )
        +
        C(
            BRIGHT_GREEN
            if data["volume_accel"] > 0
            else BRIGHT_RED,
            f"{data['volume_accel']:+.2f}x"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Buy Acceleration: "
        )
        +
        C(
            BRIGHT_GREEN
            if data["buy_accel"] > 0
            else BRIGHT_RED,
            f"{data['buy_accel'] * 100:+.2f} pts"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "Transaction Acceleration: "
        )
        +
        C(
            BRIGHT_GREEN
            if data["txn_accel"] > 0
            else BRIGHT_RED,
            f"{data['txn_accel']:+.2f}x"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "╠" + "═" * 76 + "╣"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "QUALITY: "
        )
        +
        C(
            score_color(
                data["quality"]
            ),
            f"{data['quality']}/100"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "EARLY SIGNAL: "
        )
        +
        C(
            score_color(
                data["early"]
            ),
            f"{data['early']}/100"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "ENTRY: "
        )
        +
        C(
            score_color(
                data["entry"]
            ),
            f"{data['entry']:.0f}/100"
        )
    )

    print(
        C(
            BRIGHT_MAGENTA,
            "║ "
        )
        +
        C(
            WHITE,
            "RISK: "
        )
        +
        C(
            risk_color(
                data["risk"]
            ),
            f"{data['risk']}/100"
        )
    )

    if data["early_reasons"]:

        print(
            C(
                BRIGHT_MAGENTA,
                "║ "
            )
            +
            C(
                BRIGHT_GREEN,
                "Signals: "
            )
            +
            C(
                WHITE,
                ", ".join(
                    data["early_reasons"][
                        :4
                    ]
                )
            )
        )

    if data["risk_reasons"]:

        print(
            C(
                BRIGHT_MAGENTA,
                "║ "
            )
            +
            C(
                BRIGHT_RED,
                "Risk: "
            )
            +
            C(
                WHITE,
                ", ".join(
                    data["risk_reasons"][
                        :4
                    ]
                )
            )
        )

    if data["url"]:

        print(
            C(
                BRIGHT_MAGENTA,
                "║ "
            )
            +
            C(
                WHITE,
                "Pair: "
            )
            +
            C(
                CYAN,
                data["url"]
            )
        )

    print(
        C(
            BRIGHT_MAGENTA,
            "╚" + "═" * 76 + "╝"
        )
    )


def display_stats():

    print()

    print(
        C(
            BRIGHT_CYAN,
            "━" * 78
        )
    )

    print(
        C(
            BOLD + BRIGHT_CYAN,
            "📊 PAPER ENGINE STATISTICS"
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "━" * 78
        )
    )

    balance = state["balance"]

    print(
        C(
            WHITE,
            "Paper Balance: "
        )
        +
        C(
            BRIGHT_GREEN,
            f"${balance:.2f}"
        )
    )

    print(
        C(
            WHITE,
            "Scans: "
        )
        +
        C(
            BRIGHT_CYAN,
            str(
                state["stats"]["scans"]
            )
        )
        +
        C(
            WHITE,
            "   API Calls: "
        )
        +
        C(
            BRIGHT_CYAN,
            str(
                state["stats"]["api_calls"]
            )
        )
    )

    print(
        C(
            WHITE,
            "Entries: "
        )
        +
        C(
            BRIGHT_GREEN,
            str(
                state["stats"]["entries"]
            )
        )
        +
        C(
            WHITE,
            "   Exits: "
        )
        +
        C(
            YELLOW,
            str(
                state["stats"]["exits"]
            )
        )
    )

    print(
        C(
            WHITE,
            "Wins: "
        )
        +
        C(
            BRIGHT_GREEN,
            str(
                state["stats"]["wins"]
            )
        )
        +
        C(
            WHITE,
            "   Losses: "
        )
        +
        C(
            BRIGHT_RED,
            str(
                state["stats"]["losses"]
            )
        )
    )

    print(
        C(
            WHITE,
            "Rate Limits: "
        )
        +
        C(
            YELLOW,
            str(
                state["stats"]["rate_limits"]
            )
        )
    )

    print(
        C(
            WHITE,
            "Missed Candidates: "
        )
        +
        C(
            BRIGHT_YELLOW,
            str(
                state["stats"][
                    "missed_candidates"
                ]
            )
        )
        +
        C(
            WHITE,
            "   Missed 2X+: "
        )
        +
        C(
            BRIGHT_MAGENTA,
            str(
                state["stats"][
                    "missed_runners"
                ]
            )
        )
    )

    print()

    print(
        C(
            BOLD + BRIGHT_MAGENTA,
            "🎯 MILESTONES"
        )
    )

    print(
        C(
            BRIGHT_GREEN,
            f"2X={state['milestones']['2X']}"
        )
        +
        "  "
        +
        C(
            BRIGHT_GREEN,
            f"5X={state['milestones']['5X']}"
        )
        +
        "  "
        +
        C(
            BRIGHT_YELLOW,
            f"10X={state['milestones']['10X']}"
        )
        +
        "  "
        +
        C(
            BRIGHT_MAGENTA,
            f"50X={state['milestones']['50X']}"
        )
        +
        "  "
        +
        C(
            BRIGHT_CYAN,
            f"100X={state['milestones']['100X']}"
        )
    )


# ============================================================
# WRITE STATISTICS FILE
# ============================================================

def write_stats():

    try:

        with open(
            STATS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"{BOT_NAME}\n"
            )

            f.write(
                "=" * 60 + "\n"
            )

            f.write(
                f"Updated: {now()}\n\n"
            )

            f.write(
                f"Paper Balance: "
                f"${state['balance']:.2f}\n\n"
            )

            for key, value in (
                state["stats"].items()
            ):

                f.write(
                    f"{key}: {value}\n"
                )

            f.write(
                "\nMilestones:\n"
            )

            for key, value in (
                state["milestones"].items()
            ):

                f.write(
                    f"{key}: {value}\n"
                )

    except Exception:
        pass


# ============================================================
# MONITOR OPEN TRADES
# ============================================================

def monitor_open_trades(
    candidates
):

    if not state["open_trades"]:

        return

    by_address = {
        item["address"]: item
        for item in candidates
    }

    for address in list(
        state["open_trades"].keys()
    ):

        data = by_address.get(
            address
        )

        if not data:

            continue

        trade = state[
            "open_trades"
        ].get(address)

        if not trade:

            continue

        should_exit, reason = (
            evaluate_exit(
                trade,
                data
            )
        )

        if should_exit:

            paper_exit(
                address,
                data,
                reason
            )


# ============================================================
# MAIN SCAN
# ============================================================

def scan():

    state["stats"]["scans"] += 1

    addresses = discover_tokens()

    if not addresses:

        return []

    selected = prefilter(
        addresses
    )

    candidates = []

    for address in selected:

        data = analyze(
            address
        )

        if not data:

            continue

        candidates.append(
            data
        )

        track_missed_candidate(
            data
        )

    # Sort strongest opportunities first
    candidates.sort(
        key=lambda x: (
            x["entry"],
            x["quality"],
            x["early"],
            x["volume_accel"]
        ),
        reverse=True
    )

    # Monitor existing positions first
    monitor_open_trades(
        candidates
    )

    # New paper entries
    for data in candidates:

        if (
            len(
                state["open_trades"]
            )
            >=
            MAX_OPEN_TRADES
        ):

            break

        if (
            data["entry"]
            >=
            ENTRY_SCORE_MIN
        ):

            paper_enter(
                data
            )

    save_state()

    write_stats()

    return candidates


# ============================================================
# STARTUP
# ============================================================

def startup():

    load_state()

    repair_state()

    save_state()


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    startup()

    while True:

        try:

            clear_screen()

            banner()

            print()

            print(
                C(
                    BRIGHT_YELLOW,
                    f"🕒 {now()}"
                )
            )

            print(
                C(
                    CYAN,
                    "Scanning public market data..."
                )
            )

            candidates = scan()

            display_open_trades()

            if candidates:

                display_candidates(
                    candidates
                )

                display_details(
                    candidates[0]
                )

            else:

                print()

                print(
                    C(
                        YELLOW,
                        "No usable candidates "
                        "returned this scan."
                    )
                )

            display_stats()

            print()

            print(
                C(
                    BRIGHT_BLUE,
                    "━" * 78
                )
            )

            print(
                C(
                    BRIGHT_YELLOW,
                    f"⏳ Next scan in "
                    f"{SCAN_INTERVAL} seconds..."
                )
            )

            print(
                C(
                    WHITE,
                    "Press CTRL+C to stop safely."
                )
            )

            print(
                C(
                    BRIGHT_BLUE,
                    "━" * 78
                )
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print()

            print(
                C(
                    BRIGHT_YELLOW,
                    "Stopping ALVIN MEME GOD safely..."
                )
            )

            save_state()
            write_stats()

            print(
                C(
                    BRIGHT_GREEN,
                    "State saved. Goodbye."
                )
            )

            break

        except Exception as e:

            print()

            print(
                C(
                    BRIGHT_RED,
                    f"⚠ MAIN LOOP ERROR: {e}"
                )
            )

            save_state()
            write_stats()

            time.sleep(10)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
