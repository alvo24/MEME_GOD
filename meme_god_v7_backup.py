#!/usr/bin/env python3

import os
import json
import time
from datetime import datetime, timezone

import requests


# ============================================================
# ALVIN MEME GOD V7
# SMART MEME RUNNER ENGINE
# PAPER TRADING ONLY
# ============================================================

BOT_NAME = "ALVIN MEME GOD V7"
BASE_URL = "https://api.dexscreener.com"

# Public-data polling interval
SCAN_INTERVAL = 10
TERMINAL_REFRESH = 1

# PAPER ACCOUNT
STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# ============================================================
# QUALITY FILTER
# ============================================================

MIN_LIQUIDITY = 25000
MIN_VOLUME_5M = 5000
MIN_BUY_PRESSURE = 58

QUALITY_SCORE_MIN = 68
ENTRY_SCORE_MIN = 78
WATCH_SCORE = 62

# Avoid buying after an extreme candle
MAX_ENTRY_SPIKE_5M = 20.0

# ============================================================
# PAPER RISK
# ============================================================

# User requested 50%
INITIAL_STOP = -0.50

MAX_HOLD_HOURS = 6

# Gain -> trailing distance
TRAILING_LEVELS = [
    (0.15, 0.25),
    (0.30, 0.20),
    (1.00, 0.18),
    (2.00, 0.15),
    (5.00, 0.12),
    (10.00, 0.10),
    (50.00, 0.08),
]

# ============================================================
# FILES
# ============================================================

TARGETS_FILE = "MEME_GOD_V7_TARGETS.txt"
TRADES_FILE = "MEME_GOD_V7_TRADES.txt"
STATS_FILE = "MEME_GOD_V7_STATS.txt"
STATE_FILE = "MEME_GOD_V7_STATE.json"


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BLUE = "\033[94m"


# ============================================================
# HELPERS
# ============================================================

def clear_screen():
    os.system("clear")


def now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def fnum(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def inum(x, default=0):
    try:
        return int(float(x))
    except Exception:
        return default


def write_log(filename, text):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def pct_change(new, old):
    if old is None or old == 0:
        return 0.0

    return ((new / old) - 1.0) * 100.0


# ============================================================
# STATE
# ============================================================

def default_state():

    return {
        "balance": STARTING_BALANCE,

        "open_trades": [],

        "closed_trades": [],

        "watchlist": {},

        "milestones": {
            "2X": 0,
            "5X": 0,
            "10X": 0,
            "50X": 0,
            "100X": 0
        },

        "peak_equity": STARTING_BALANCE,

        "max_drawdown": 0.0,

        "scans": 0
    }


def repair_state(state):

    base = default_state()

    if not isinstance(state, dict):
        return base

    for key, value in base.items():

        if key not in state:
            state[key] = value

    if not isinstance(state.get("open_trades"), list):
        state["open_trades"] = []

    if not isinstance(state.get("closed_trades"), list):
        state["closed_trades"] = []

    if not isinstance(state.get("watchlist"), dict):
        state["watchlist"] = {}

    if not isinstance(state.get("milestones"), dict):
        state["milestones"] = base["milestones"].copy()

    for key in base["milestones"]:

        if key not in state["milestones"]:
            state["milestones"][key] = 0

    return state


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

        return repair_state(state)

    except Exception:

        return default_state()


def save_state(state):

    state = repair_state(state)

    temp_file = STATE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=2
        )

    os.replace(
        temp_file,
        STATE_FILE
    )


# ============================================================
# API
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD-V7-PAPER"
})


def api_get(endpoint):

    try:

        response = session.get(
            BASE_URL + endpoint,
            timeout=20
        )

        if response.status_code == 429:

            print(
                f"{YELLOW}"
                "Rate limited. Waiting..."
                f"{RESET}"
            )

            time.sleep(20)

            return []

        if response.status_code != 200:
            return []

        return response.json()

    except Exception:

        return []


# ============================================================
# DISCOVERY
# ============================================================

def discover():

    found = {}

    endpoints = [
        "/token-profiles/latest/v1",
        "/token-boosts/latest/v1",
        "/token-boosts/top/v1"
    ]

    for endpoint in endpoints:

        data = api_get(endpoint)

        if not isinstance(data, list):
            continue

        for item in data:

            chain = str(
                item.get("chainId", "")
            ).lower()

            if chain != "solana":
                continue

            address = item.get(
                "tokenAddress"
            )

            if address:
                found[address] = endpoint

    return found


# ============================================================
# GET BEST PAIR
# ============================================================

def get_pair(address):

    data = api_get(
        f"/token-pairs/v1/solana/{address}"
    )

    if not isinstance(data, list):
        return None

    pairs = []

    for pair in data:

        if str(
            pair.get("chainId", "")
        ).lower() != "solana":
            continue

        liquidity = fnum(
            (pair.get("liquidity") or {}).get(
                "usd"
            )
        )

        pairs.append(
            (
                liquidity,
                pair
            )
        )

    if not pairs:
        return None

    pairs.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return pairs[0][1]


# ============================================================
# NORMALIZE MARKET DATA
# ============================================================

def normalize(pair, source):

    base = pair.get(
        "baseToken",
        {}
    ) or {}

    address = base.get(
        "address"
    )

    if not address:
        return None

    pair_id = pair.get(
        "pairAddress",
        ""
    )

    pair_url = pair.get(
        "url",
        ""
    )

    if not pair_url and pair_id:

        pair_url = (
            "https://dexscreener.com/solana/"
            + pair_id
        )

    txns = pair.get(
        "txns",
        {}
    ) or {}

    m5 = txns.get(
        "m5",
        {}
    ) or {}

    h1 = txns.get(
        "h1",
        {}
    ) or {}

    buys_5m = inum(
        m5.get("buys")
    )

    sells_5m = inum(
        m5.get("sells")
    )

    total_5m = (
        buys_5m +
        sells_5m
    )

    buy_pressure = (
        buys_5m /
        total_5m *
        100
        if total_5m > 0
        else 0
    )

    volume = pair.get(
        "volume",
        {}
    ) or {}

    changes = pair.get(
        "priceChange",
        {}
    ) or {}

    liquidity = fnum(
        (pair.get("liquidity") or {}).get(
            "usd"
        )
    )

    market_cap = fnum(
        pair.get("marketCap")
    )

    fdv = fnum(
        pair.get("fdv")
    )

    return {

        "address": address,

        "token_id": address,

        "pair_id": pair_id,

        "pair_url": pair_url,

        "symbol": base.get(
            "symbol",
            "UNKNOWN"
        ),

        "name": base.get(
            "name",
            "UNKNOWN"
        ),

        "price": fnum(
            pair.get("priceUsd")
        ),

        "liquidity": liquidity,

        "market_cap": market_cap,

        "fdv": fdv,

        "volume_m5": fnum(
            volume.get("m5")
        ),

        "volume_h1": fnum(
            volume.get("h1")
        ),

        "m5_buys": buys_5m,

        "m5_sells": sells_5m,

        "m5_total": total_5m,

        "h1_buys": inum(
            h1.get("buys")
        ),

        "h1_sells": inum(
            h1.get("sells")
        ),

        "buy_pressure": buy_pressure,

        "change_m5": fnum(
            changes.get("m5")
        ),

        "change_h1": fnum(
            changes.get("h1")
        ),

        "change_h6": fnum(
            changes.get("h6")
        ),

        "change_h24": fnum(
            changes.get("h24")
        ),

        "source": source,

        "observed_at": now()
    }


# ============================================================
# QUALITY SCORE
# ============================================================

def quality_score(d, old=None):

    score = 0

    liquidity = d["liquidity"]
    volume = d["volume_m5"]
    volume_h1 = d["volume_h1"]
    buy_pressure = d["buy_pressure"]

    m5 = d["change_m5"]
    h1 = d["change_h1"]
    h6 = d["change_h6"]

    # --------------------------------------------------------
    # LIQUIDITY / 15
    # --------------------------------------------------------

    if liquidity >= 250000:
        score += 15

    elif liquidity >= 100000:
        score += 13

    elif liquidity >= 50000:
        score += 11

    elif liquidity >= 25000:
        score += 8

    elif liquidity >= 15000:
        score += 4

    # --------------------------------------------------------
    # 5M VOLUME / 15
    # --------------------------------------------------------

    if volume >= 100000:
        score += 15

    elif volume >= 50000:
        score += 13

    elif volume >= 20000:
        score += 11

    elif volume >= 10000:
        score += 8

    elif volume >= 5000:
        score += 5

    # --------------------------------------------------------
    # BUY PRESSURE / 15
    # --------------------------------------------------------

    if buy_pressure >= 75:
        score += 15

    elif buy_pressure >= 70:
        score += 13

    elif buy_pressure >= 65:
        score += 11

    elif buy_pressure >= 60:
        score += 8

    elif buy_pressure >= 58:
        score += 5

    # --------------------------------------------------------
    # MOMENTUM / 15
    # --------------------------------------------------------

    if 3 <= m5 <= 15:
        score += 15

    elif 0 < m5 < 3:
        score += 10

    elif 15 < m5 <= 20:
        score += 8

    elif m5 > 20:
        score += 3

    # --------------------------------------------------------
    # TREND / 15
    # --------------------------------------------------------

    if h1 >= 30:
        score += 15

    elif h1 >= 20:
        score += 13

    elif h1 >= 10:
        score += 10

    elif h1 > 0:
        score += 7

    # --------------------------------------------------------
    # VOLUME ACCELERATION / 10
    # --------------------------------------------------------

    if old:

        old_volume = fnum(
            old.get("volume_m5")
        )

        if old_volume > 0:

            acceleration = (
                volume /
                old_volume
            )

            if acceleration >= 2.0:
                score += 10

            elif acceleration >= 1.5:
                score += 8

            elif acceleration >= 1.2:
                score += 5

            elif acceleration > 1.0:
                score += 2

    # --------------------------------------------------------
    # BUY ACCELERATION / 10
    # --------------------------------------------------------

    if old:

        old_bp = fnum(
            old.get("buy_pressure")
        )

        bp_change = (
            buy_pressure -
            old_bp
        )

        if bp_change >= 10:
            score += 10

        elif bp_change >= 6:
            score += 8

        elif bp_change >= 3:
            score += 5

        elif bp_change > 0:
            score += 2

    # --------------------------------------------------------
    # MARKET STRUCTURE / 5
    # --------------------------------------------------------

    if h1 > 0 and h6 > 0:
        score += 5

    elif h1 > 0:
        score += 3

    return min(
        100,
        max(0, score)
    )


# ============================================================
# RISK / WARNING SCORE
# ============================================================

def risk_score(d, old=None):

    risk = 0
    reasons = []

    liquidity = d["liquidity"]
    volume = d["volume_m5"]
    bp = d["buy_pressure"]
    m5 = d["change_m5"]

    # Very low liquidity
    if liquidity < 15000:

        risk += 35
        reasons.append(
            "VERY LOW LIQUIDITY"
        )

    elif liquidity < 25000:

        risk += 20
        reasons.append(
            "LOW LIQUIDITY"
        )

    # Extreme 5m move
    if m5 >= 80:

        risk += 35
        reasons.append(
            "EXTREME PRICE SPIKE"
        )

    elif m5 >= 50:

        risk += 25
        reasons.append(
            "LARGE PRICE SPIKE"
        )

    elif m5 >= 30:

        risk += 15
        reasons.append(
            "FAST PRICE MOVE"
        )

    # Weak buying
    if bp < 45:

        risk += 30
        reasons.append(
            "SELL PRESSURE"
        )

    elif bp < 52:

        risk += 15
        reasons.append(
            "WEAK BUY PRESSURE"
        )

    # Volume collapsing
    if old:

        old_volume = fnum(
            old.get("volume_m5")
        )

        if old_volume > 0:

            volume_ratio = (
                volume /
                old_volume
            )

            if volume_ratio < 0.50:

                risk += 20
                reasons.append(
                    "VOLUME COLLAPSE"
                )

    # Buying pressure collapsing
    if old:

        old_bp = fnum(
            old.get("buy_pressure")
        )

        if (
            old_bp >= 60
            and bp < old_bp - 10
        ):

            risk += 20
            reasons.append(
                "BUYING COLLAPSE"
            )

    return min(
        100,
        risk
    ), reasons


# ============================================================
# MOMENTUM FEATURES
# ============================================================

def momentum_features(d, old):

    features = {
        "volume_acceleration": 0.0,
        "buy_acceleration": 0.0,
        "momentum_change": 0.0,
        "liquidity_change": 0.0
    }

    if not old:
        return features

    old_volume = fnum(
        old.get("volume_m5")
    )

    if old_volume > 0:

        features["volume_acceleration"] = (
            d["volume_m5"] /
            old_volume
        )

    old_bp = fnum(
        old.get("buy_pressure")
    )

    features["buy_acceleration"] = (
        d["buy_pressure"] -
        old_bp
    )

    features["momentum_change"] = (
        d["change_m5"] -
        fnum(old.get("change_m5"))
    )

    old_liq = fnum(
        old.get("liquidity")
    )

    if old_liq > 0:

        features["liquidity_change"] = (
            d["liquidity"] /
            old_liq
        )

    return features


# ============================================================
# ENTRY SETUP
# ============================================================

def entry_signal(d, old, quality):

    if old is None:

        return (
            False,
            0,
            "WAITING FOR SECOND OBSERVATION"
        )

    if d["liquidity"] < MIN_LIQUIDITY:

        return (
            False,
            0,
            "LOW LIQUIDITY"
        )

    if d["volume_m5"] < MIN_VOLUME_5M:

        return (
            False,
            0,
            "LOW 5M VOLUME"
        )

    if d["buy_pressure"] < MIN_BUY_PRESSURE:

        return (
            False,
            0,
            "WEAK BUY PRESSURE"
        )

    if d["change_h1"] <= 0:

        return (
            False,
            0,
            "NEGATIVE 1H TREND"
        )

    if d["change_m5"] > MAX_ENTRY_SPIKE_5M:

        return (
            False,
            0,
            "CHASING / TOO EXTENDED"
        )

    if quality < QUALITY_SCORE_MIN:

        return (
            False,
            0,
            "LOW QUALITY"
        )

    features = momentum_features(
        d,
        old
    )

    score = 0
    setups = []

    volume_accel = features[
        "volume_acceleration"
    ]

    buy_accel = features[
        "buy_acceleration"
    ]

    momentum_change = features[
        "momentum_change"
    ]

    old_m5 = fnum(
        old.get("change_m5")
    )

    old_bp = fnum(
        old.get("buy_pressure")
    )

    # ========================================================
    # SETUP A: PULLBACK RECOVERY
    # ========================================================

    recovery = (
        old_m5 <= 0
        and d["change_m5"] > 0
        and buy_accel >= 2
        and volume_accel >= 1.10
    )

    if recovery:

        score += 32
        setups.append(
            "PULLBACK RECOVERY"
        )

    # ========================================================
    # SETUP B: MOMENTUM CONTINUATION
    # ========================================================

    continuation = (
        d["change_m5"] > 0
        and d["change_m5"] <= 15
        and momentum_change > 0
        and volume_accel >= 1.15
        and buy_accel >= 2
    )

    if continuation:

        score += 30
        setups.append(
            "MOMENTUM CONTINUATION"
        )

    # ========================================================
    # SETUP C: EARLY BREAKOUT
    # ========================================================

    breakout = (
        old_m5 <= 3
        and d["change_m5"] > 3
        and d["change_m5"] <= 15
        and volume_accel >= 1.40
        and buy_accel >= 4
    )

    if breakout:

        score += 35
        setups.append(
            "EARLY BREAKOUT"
        )

    # ========================================================
    # BUYING ACCELERATION
    # ========================================================

    if buy_accel >= 10:

        score += 15

    elif buy_accel >= 6:

        score += 10

    elif buy_accel >= 3:

        score += 5

    # ========================================================
    # VOLUME ACCELERATION
    # ========================================================

    if volume_accel >= 2.0:

        score += 15

    elif volume_accel >= 1.5:

        score += 10

    elif volume_accel >= 1.2:

        score += 5

    # ========================================================
    # BUYING LEVEL
    # ========================================================

    if d["buy_pressure"] >= 70:

        score += 10

    elif d["buy_pressure"] >= 65:

        score += 7

    # ========================================================
    # CHASING PENALTY
    # ========================================================

    if d["change_m5"] >= 15:

        score -= 20

    elif d["change_m5"] >= 10:

        score -= 10

    # ========================================================
    # DETERIORATION PENALTY
    # ========================================================

    if d["change_m5"] < old_m5:

        score -= 10

    if d["buy_pressure"] < old_bp:

        score -= 10

    score = max(
        0,
        min(100, score)
    )

    if not setups:

        return (
            False,
            score,
            "NO VALID SETUP"
        )

    if score < ENTRY_SCORE_MIN:

        return (
            False,
            score,
            "SETUP SCORE TOO LOW"
        )

    reason = " + ".join(
        setups
    )

    return (
        True,
        score,
        reason
    )


# ============================================================
# TRAILING STOP
# ============================================================

def trailing_stop(trade):

    entry = fnum(
        trade.get("entry_price")
    )

    highest = fnum(
        trade.get("highest_price")
    )

    if entry <= 0 or highest <= 0:
        return None

    gain = (
        highest /
        entry
    ) - 1

    trail = None

    for minimum, distance in TRAILING_LEVELS:

        if gain >= minimum:
            trail = distance

    if trail is None:
        return None

    return highest * (
        1 - trail
    )


# ============================================================
# DYNAMIC EXIT ANALYSIS
# ============================================================

def deterioration_signal(d, old, trade):

    if not old:
        return False, ""

    entry = fnum(
        trade.get("entry_price")
    )

    price = d["price"]

    if entry <= 0:
        return False, ""

    multiple = price / entry

    old_bp = fnum(
        old.get("buy_pressure")
    )

    bp = d["buy_pressure"]

    old_volume = fnum(
        old.get("volume_m5")
    )

    volume = d["volume_m5"]

    old_m5 = fnum(
        old.get("change_m5")
    )

    m5 = d["change_m5"]

    # --------------------------------------------------------
    # Major deterioration only matters more once profitable
    # --------------------------------------------------------

    if multiple >= 1.15:

        if (
            bp < 45
            and bp < old_bp - 5
        ):

            return (
                True,
                "BUYING PRESSURE COLLAPSE"
            )

        if (
            old_volume > 0
            and volume < old_volume * 0.45
            and m5 < old_m5
        ):

            return (
                True,
                "MOMENTUM + VOLUME DETERIORATION"
            )

    return False, ""


# ============================================================
# OPEN TRADE
# ============================================================

def already_open(state, address):

    return any(
        x.get("address") == address
        for x in state["open_trades"]
    )


def open_trade(
    state,
    d,
    quality,
    entry_score,
    reason
):

    if len(
        state["open_trades"]
    ) >= MAX_OPEN_TRADES:

        return

    if state["balance"] < PAPER_TRADE_SIZE:

        return

    if already_open(
        state,
        d["address"]
    ):

        return

    trade = {

        "address": d["address"],

        "token_id": d["token_id"],

        "pair_id": d["pair_id"],

        "pair_url": d["pair_url"],

        "symbol": d["symbol"],

        "name": d["name"],

        "entry_price": d["price"],

        "highest_price": d["price"],

        "stake": PAPER_TRADE_SIZE,

        "entry_time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "quality_score": quality,

        "entry_score": entry_score,

        "entry_reason": reason,

        "entry_liquidity":
            d["liquidity"],

        "entry_volume":
            d["volume_m5"],

        "entry_buy_pressure":
            d["buy_pressure"],

        "entry_buys":
            d["m5_buys"],

        "entry_sells":
            d["m5_sells"],

        "milestones_hit": [],

        "max_multiple": 1.0
    }

    state["balance"] -= (
        PAPER_TRADE_SIZE
    )

    state["open_trades"].append(
        trade
    )

    message = (

        "\n"
        "============================================================\n"
        "PAPER ENTRY\n"
        "============================================================\n"

        f"Token: {d['symbol']}\n"

        f"Contract: {d['address']}\n"

        f"Pair ID: {d['pair_id']}\n"

        f"Pair URL: {d['pair_url']}\n"

        f"Price: ${d['price']:.12f}\n"

        f"Quality Score: {quality}/100\n"

        f"Entry Score: {entry_score}/100\n"

        f"Setup: {reason}\n"

        f"5M Buys: {d['m5_buys']}\n"

        f"5M Sells: {d['m5_sells']}\n"

        f"Buy Pressure: "
        f"{d['buy_pressure']:.2f}%\n"

        f"Liquidity: "
        f"${d['liquidity']:,.2f}\n"

        f"5M Volume: "
        f"${d['volume_m5']:,.2f}\n"

        f"Initial Stop: "
        f"{INITIAL_STOP * 100:.0f}%\n"

        f"Time: {now()}\n"

        "============================================================\n"
    )

    write_log(
        TRADES_FILE,
        message
    )


# ============================================================
# MILESTONES
# ============================================================

def milestones(
    state,
    trade,
    price
):

    entry = fnum(
        trade.get("entry_price")
    )

    if entry <= 0:
        return

    multiple = (
        price /
        entry
    )

    targets = [
        ("2X", 2),
        ("5X", 5),
        ("10X", 10),
        ("50X", 50),
        ("100X", 100)
    ]

    for name, target in targets:

        if (
            multiple >= target
            and name not in
            trade["milestones_hit"]
        ):

            trade[
                "milestones_hit"
            ].append(name)

            state[
                "milestones"
            ][name] += 1

            write_log(
                TRADES_FILE,

                (
                    "\n"
                    "🚀 "
                    f"{name} MILESTONE\n"

                    f"Token: "
                    f"{trade['symbol']}\n"

                    f"Contract: "
                    f"{trade['address']}\n"

                    f"Pair ID: "
                    f"{trade['pair_id']}\n"

                    f"Pair URL: "
                    f"{trade['pair_url']}\n"

                    f"Multiple: "
                    f"{multiple:.2f}X\n"

                    f"Time: "
                    f"{now()}\n"
                )
            )


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(
    state,
    trade,
    d,
    reason
):

    entry = fnum(
        trade.get("entry_price")
    )

    price = d["price"]

    if entry <= 0:
        return

    multiple = (
        price /
        entry
    )

    returned = (
        trade["stake"] *
        multiple
    )

    profit = (
        returned -
        trade["stake"]
    )

    state["balance"] += returned

    trade["exit_price"] = price

    trade["exit_time"] = now()

    trade["exit_reason"] = reason

    trade["profit"] = profit

    trade["final_multiple"] = multiple

    trade["return_value"] = returned

    state[
        "closed_trades"
    ].append(trade)

    state[
        "open_trades"
    ].remove(trade)

    write_log(
        TRADES_FILE,

        (
            "\n"
            "============================================================\n"
            "PAPER EXIT\n"
            "============================================================\n"

            f"Token: {trade['symbol']}\n"

            f"Contract: "
            f"{trade['address']}\n"

            f"Pair ID: "
            f"{trade['pair_id']}\n"

            f"Pair URL: "
            f"{trade['pair_url']}\n"

            f"Entry: "
            f"${entry:.12f}\n"

            f"Exit: "
            f"${price:.12f}\n"

            f"Highest: "
            f"${trade['highest_price']:.12f}\n"

            f"Maximum: "
            f"{trade['max_multiple']:.2f}X\n"

            f"Final: "
            f"{multiple:.2f}X\n"

            f"P/L: "
            f"${profit:.2f}\n"

            f"Reason: "
            f"{reason}\n"

            f"Time: "
            f"{now()}\n"

            "============================================================\n"
        )
    )


# ============================================================
# UPDATE OPEN TRADES
# ============================================================

def update_trades(
    state,
    market,
    previous_market
):

    for trade in list(
        state["open_trades"]
    ):

        address = trade[
            "address"
        ]

        d = market.get(
            address
        )

        if not d:
            continue

        price = d["price"]

        if price <= 0:
            continue

        if price > trade[
            "highest_price"
        ]:

            trade[
                "highest_price"
            ] = price

        entry = fnum(
            trade["entry_price"]
        )

        if entry <= 0:
            continue

        multiple = (
            price /
            entry
        )

        trade[
            "max_multiple"
        ] = max(
            trade["max_multiple"],
            trade["highest_price"] /
            entry
        )

        milestones(
            state,
            trade,
            price
        )

        reason = None

        gain = multiple - 1

        # ----------------------------------------------------
        # INITIAL STOP
        # ----------------------------------------------------

        if gain <= INITIAL_STOP:

            reason = "INITIAL STOP"

        # ----------------------------------------------------
        # TRAILING STOP
        # ----------------------------------------------------

        stop = trailing_stop(
            trade
        )

        if (
            stop is not None
            and price <= stop
        ):

            reason = "TRAILING STOP"

        # ----------------------------------------------------
        # MARKET DETERIORATION
        # ----------------------------------------------------

        old = previous_market.get(
            address
        )

        deteriorating, d_reason = (
            deterioration_signal(
                d,
                old,
                trade
            )
        )

        # Don't immediately override a protective
        # trailing stop with a weaker reason.

        if (
            deteriorating
            and gain > 0.15
        ):

            if reason is None:

                reason = d_reason

        # ----------------------------------------------------
        # MAX HOLD
        # ----------------------------------------------------

        try:

            opened = datetime.fromisoformat(
                trade["entry_time"]
            )

            hours = (
                datetime.now(timezone.utc)
                - opened
            ).total_seconds() / 3600

            if hours >= MAX_HOLD_HOURS:

                reason = "MAX HOLD TIME"

        except Exception:

            pass

        if reason:

            close_trade(
                state,
                trade,
                d,
                reason
            )


# ============================================================
# DISPLAY
# ============================================================

def live_terminal(
    state,
    market,
    candidates
):

    clear_screen()

    closed = state[
        "closed_trades"
    ]

    wins = sum(
        1
        for x in closed
        if x.get("profit", 0) > 0
    )

    losses = sum(
        1
        for x in closed
        if x.get("profit", 0) < 0
    )

    realized = sum(
        x.get("profit", 0)
        for x in closed
    )

    print(
        f"{MAGENTA}"
        "╔════════════════════════════════════════════════════════════════════════════╗\n"
        f"║                    {BOT_NAME:^42} ║\n"
        "║                         PAPER MODE                                      ║\n"
        "╚════════════════════════════════════════════════════════════════════════════╝"
        f"{RESET}"
    )

    print(
        f"{CYAN}"
        f"Last Scan : {now()}\n"
        f"Balance   : ${state['balance']:.2f}\n"
        f"Open      : {len(state['open_trades'])}/{MAX_OPEN_TRADES}\n"
        f"Closed    : {len(closed)}\n"
        f"Wins      : {wins}   Losses: {losses}\n"
        f"Realized  : ${realized:.2f}\n"
        f"Initial SL: {INITIAL_STOP * 100:.0f}%\n"
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )

    if state["open_trades"]:

        print(
            f"{GREEN}"
            "                         OPEN PAPER TRADES"
            f"{RESET}"
        )

        print(
            "┌────┬──────────┬──────────┬──────────┬──────────┬──────────┐"
        )

        print(
            "│ #  │ TOKEN    │ ENTRY    │ CURRENT  │ MULTIPLE │ P/L      │"
        )

        print(
            "├────┼──────────┼──────────┼──────────┼──────────┼──────────┤"
        )

        for i, trade in enumerate(
            state["open_trades"],
            1
        ):

            d = market.get(
                trade["address"]
            )

            price = (
                d["price"]
                if d
                else trade["entry_price"]
            )

            entry = trade[
                "entry_price"
            ]

            multiple = (
                price / entry
                if entry > 0
                else 1
            )

            pnl = (
                trade["stake"] *
                (multiple - 1)
            )

            print(
                f"│{i:>3} "
                f"│{trade['symbol'][:8]:<8} "
                f"│${entry:.6f} "
                f"│${price:.6f} "
                f"│{multiple:>7.2f}X "
                f"│${pnl:>7.2f} │"
            )

        print(
            "└────┴──────────┴──────────┴──────────┴──────────┴──────────┘"
        )

        print()

        for i, trade in enumerate(
            state["open_trades"],
            1
        ):

            d = market.get(
                trade["address"]
            )

            if not d:
                continue

            price = d["price"]

            entry = trade[
                "entry_price"
            ]

            multiple = (
                price / entry
                if entry > 0
                else 1
            )

            pnl = (
                trade["stake"] *
                (multiple - 1)
            )

            stop = trailing_stop(
                trade
            )

            pnl_color = (
                GREEN
                if pnl >= 0
                else RED
            )

            print(
                f"{BLUE}"
                f"┌─ TRADE #{i} "
                f"{trade['symbol']}"
                f"{RESET}"
            )

            print(
                f"│ Contract / Token ID:\n"
                f"│ {trade['address']}"
            )

            print(
                f"│ Pair ID:\n"
                f"│ {trade['pair_id']}"
            )

            print(
                f"│ Pair URL:\n"
                f"│ {trade['pair_url']}"
            )

            print(
                f"│ 5M Transactions: "
                f"{d['m5_total']} "
                f"(Buys {d['m5_buys']} / "
                f"Sells {d['m5_sells']})"
            )

            print(
                f"│ Buy Pressure: "
                f"{d['buy_pressure']:.2f}%"
            )

            print(
                f"│ Liquidity: "
                f"${d['liquidity']:,.0f}"
            )

            print(
                f"│ 5M Volume: "
                f"${d['volume_m5']:,.0f}"
            )

            print(
                f"│ 1H Volume: "
                f"${d['volume_h1']:,.0f}"
            )

            print(
                f"│ 5M Change: "
                f"{d['change_m5']:.2f}%"
            )

            print(
                f"│ 1H Change: "
                f"{d['change_h1']:.2f}%"
            )

            print(
                f"│ Quality Score: "
                f"{trade['quality_score']}/100"
            )

            print(
                f"│ Entry Score: "
                f"{trade['entry_score']}/100"
            )

            print(
                f"│ Entry Setup: "
                f"{trade['entry_reason']}"
            )

            print(
                f"│ Entry: "
                f"${entry:.12f}"
            )

            print(
                f"│ Current: "
                f"${price:.12f}"
            )

            print(
                f"│ Highest: "
                f"${trade['highest_price']:.12f}"
            )

            print(
                f"│ Multiple: "
                f"{multiple:.2f}X"
            )

            print(
                f"│ Maximum: "
                f"{trade['max_multiple']:.2f}X"
            )

            if stop:

                print(
                    f"│ Trailing Stop: "
                    f"${stop:.12f}"
                )

            else:

                print(
                    "│ Trailing Stop: "
                    "NOT ACTIVE"
                )

            print(
                f"│ P/L: "
                f"{pnl_color}"
                f"${pnl:.2f}"
                f"{RESET}"
            )

            print(
                f"{BLUE}"
                "└──────────────────────────────────────────────────────────────────────────"
                f"{RESET}"
            )

    else:

        print(
            f"{YELLOW}"
            "                    NO OPEN PAPER TRADES"
            f"{RESET}"
        )

    print()

    # ========================================================
    # TOP CURRENT CANDIDATES
    # ========================================================

    print(
        f"{MAGENTA}"
        "                    TOP CURRENT CANDIDATES"
        f"{RESET}"
    )

    if candidates:

        for rank, item in enumerate(
            candidates[:8],
            1
        ):

            d = item["data"]

            quality = item["quality"]

            entry_score = item[
                "entry_score"
            ]

            valid = item[
                "valid"
            ]

            reason = item[
                "reason"
            ]

            risk = item[
                "risk"
            ]

            status = (
                f"{GREEN}ENTRY{RESET}"
                if valid
                else f"{YELLOW}WATCH{RESET}"
            )

            print(
                f"{rank:>2}. "
                f"{d['symbol'][:12]:<12} "
                f"Q:{quality:>3} "
                f"E:{entry_score:>3} "
                f"Risk:{risk:>2} "
                f"{status} "
                f"{reason}"
            )

    else:

        print(
            f"{YELLOW}"
            "No strong candidates."
            f"{RESET}"
        )

    print()

    print(
        f"{YELLOW}"
        "Milestones: "
        f"2X={state['milestones']['2X']}  "
        f"5X={state['milestones']['5X']}  "
        f"10X={state['milestones']['10X']}  "
        f"50X={state['milestones']['50X']}  "
        f"100X={state['milestones']['100X']}"
        f"{RESET}"
    )

    print(
        f"\n{CYAN}"
        f"Next scan in {SCAN_INTERVAL} seconds..."
        f"{RESET}"
    )


# ============================================================
# STATS
# ============================================================

def save_stats(state):

    closed = state[
        "closed_trades"
    ]

    wins = [
        x for x in closed
        if x.get("profit", 0) > 0
    ]

    losses = [
        x for x in closed
        if x.get("profit", 0) < 0
    ]

    gross_profit = sum(
        x.get("profit", 0)
        for x in wins
    )

    gross_loss = sum(
        x.get("profit", 0)
        for x in losses
    )

    profit_factor = (
        gross_profit /
        abs(gross_loss)
        if gross_loss < 0
        else 0
    )

    win_rate = (
        len(wins) /
        len(closed) *
        100
        if closed
        else 0
    )

    realized = sum(
        x.get("profit", 0)
        for x in closed
    )

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{BOT_NAME}\n"
            f"Updated: {now()}\n\n"

            f"Balance: "
            f"${state['balance']:.2f}\n"

            f"Open: "
            f"{len(state['open_trades'])}\n"

            f"Closed: "
            f"{len(closed)}\n"

            f"Wins: "
            f"{len(wins)}\n"

            f"Losses: "
            f"{len(losses)}\n"

            f"Win Rate: "
            f"{win_rate:.2f}%\n"

            f"Realized P/L: "
            f"${realized:.2f}\n"

            f"Profit Factor: "
            f"{profit_factor:.2f}\n\n"

            f"2X: "
            f"{state['milestones']['2X']}\n"

            f"5X: "
            f"{state['milestones']['5X']}\n"

            f"10X: "
            f"{state['milestones']['10X']}\n"

            f"50X: "
            f"{state['milestones']['50X']}\n"

            f"100X: "
            f"{state['milestones']['100X']}\n"
        )


# ============================================================
# SCAN
# ============================================================

def scan(state):

    discovered = discover()

    market = {}

    candidates = []

    previous_market = {}

    # --------------------------------------------------------
    # Save previous observations before updating watchlist
    # --------------------------------------------------------

    for address, value in state[
        "watchlist"
    ].items():

        if isinstance(value, dict):

            previous_market[
                address
            ] = value.copy()

    # --------------------------------------------------------
    # DISCOVER + ANALYZE
    # --------------------------------------------------------

    for address, source in discovered.items():

        pair = get_pair(
            address
        )

        if not pair:
            continue

        d = normalize(
            pair,
            source
        )

        if not d:
            continue

        if d["price"] <= 0:
            continue

        old = previous_market.get(
            address
        )

        quality = quality_score(
            d,
            old
        )

        risk, risk_reasons = risk_score(
            d,
            old
        )

        entry_valid, entry_score, reason = (
            entry_signal(
                d,
                old,
                quality
            )
        )

        # Never enter a high-risk candidate
        if risk >= 40:

            entry_valid = False

            reason = (
                "HIGH RISK: "
                + (
                    ", ".join(
                        risk_reasons
                    )
                    if risk_reasons
                    else "WARNING"
                )
            )

        market[
            address
        ] = d

        candidates.append({

            "data": d,

            "quality": quality,

            "entry_score": entry_score,

            "valid": entry_valid,

            "reason": reason,

            "risk": risk,

            "risk_reasons":
                risk_reasons
        })

        # ----------------------------------------------------
        # Store observation
        # ----------------------------------------------------

        state[
            "watchlist"
        ][address] = d

    # --------------------------------------------------------
    # Sort candidates
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x["valid"],
            x["entry_score"],
            x["quality"],
            -x["risk"]
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # Update existing trades FIRST
    # --------------------------------------------------------

    update_trades(
        state,
        market,
        previous_market
    )

    # --------------------------------------------------------
    # New paper entries
    # --------------------------------------------------------

    for item in candidates:

        if not item["valid"]:
            continue

        if len(
            state["open_trades"]
        ) >= MAX_OPEN_TRADES:

            break

        d = item["data"]

        open_trade(
            state,

            d,

            item["quality"],

            item["entry_score"],

            item["reason"]
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    state["scans"] += 1

    save_state(state)

    save_stats(state)

    live_terminal(
        state,
        market,
        candidates
    )


# ============================================================
# MAIN
# ============================================================

def main():

    for filename in [

        TARGETS_FILE,

        TRADES_FILE,

        STATS_FILE

    ]:

        if not os.path.exists(
            filename
        ):

            open(
                filename,
                "w",
                encoding="utf-8"
            ).close()

    state = load_state()

    clear_screen()

    print(
        f"{MAGENTA}"

        """
╔══════════════════════════════════════════════════════════════════════╗
║                       ALVIN MEME GOD V7                             ║
║                    SMART RUNNER ENGINE                              ║
║                                                                      ║
║                         PAPER MODE                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

        f"{RESET}"
    )

    print(
        f"{CYAN}"
        "Strategy:\n"
        "  • Quality filtering\n"
        "  • Pullback recovery\n"
        "  • Momentum continuation\n"
        "  • Early breakout detection\n"
        "  • Volume acceleration\n"
        "  • Buy-pressure acceleration\n"
        "  • Anti-chasing filter\n"
        "  • Rug-risk warning layer\n"
        "  • Adaptive runner management\n"
        f"{RESET}"
    )

    time.sleep(3)

    while True:

        try:

            scan(
                state
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            save_state(
                state
            )

            save_stats(
                state
            )

            print(
                f"\n{YELLOW}"
                "V7 stopped."
                f"{RESET}"
            )

            break

        except Exception as e:

            print(
                f"\n{RED}"
                f"Scanner error: {e}"
                f"{RESET}"
            )

            time.sleep(10)


if __name__ == "__main__":

    main()
