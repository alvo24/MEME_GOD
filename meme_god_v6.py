#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime, timezone

import requests


# ============================================================
# ALVIN MEME GOD V6
# QUALITY ENTRY + RUNNER PAPER TRADER
# ============================================================

BOT_NAME = "ALVIN MEME GOD V6"

BASE_URL = "https://api.dexscreener.com"

SCAN_INTERVAL = 5

# ------------------------------------------------------------
# PAPER ACCOUNT
# ------------------------------------------------------------

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# ------------------------------------------------------------
# V6 QUALITY ENTRY SETTINGS
# ------------------------------------------------------------

ENTRY_SCORE = 82
WATCH_SCORE = 70

MIN_LIQUIDITY = 25000
MIN_VOLUME_5M = 5000
MIN_BUY_PRESSURE = 58

# Avoid buying an already-crazy 5m candle
MAX_ENTRY_SPIKE_5M = 20.0

# ------------------------------------------------------------
# RISK / RUNNER SETTINGS
# ------------------------------------------------------------

INITIAL_STOP = -0.10

# gain reached -> allowed drawdown from highest price
TRAILING_LEVELS = [
    (0.15, 0.08),    # +15%  -> 8% trail
    (0.30, 0.12),    # +30%  -> 12% trail
    (1.00, 0.18),    # +100% -> 18% trail
    (5.00, 0.22),    # +500% -> 22% trail
    (10.00, 0.25),   # +1000% -> 25% trail
    (50.00, 0.30),   # +5000% -> 30% trail
]

MAX_HOLD_HOURS = 6

# ------------------------------------------------------------
# FILES
# ------------------------------------------------------------

TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_V6_STATE.json"


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

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default


def pct(value):
    return f"{value * 100:.2f}%"


def money(value):
    return f"${value:.2f}"


def append_file(filename, text):
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception as e:
        print(f"{RED}File error {filename}: {e}{RESET}")


# ============================================================
# FILE INITIALIZATION
# ============================================================

def initialize_files():

    if not os.path.exists(TARGETS_FILE):
        append_file(
            TARGETS_FILE,
            "=" * 80
        )
        append_file(
            TARGETS_FILE,
            f"{BOT_NAME} TARGET LOG"
        )
        append_file(
            TARGETS_FILE,
            "=" * 80
        )

    if not os.path.exists(TRADES_FILE):
        append_file(
            TRADES_FILE,
            "=" * 80
        )
        append_file(
            TRADES_FILE,
            f"{BOT_NAME} PAPER TRADE LOG"
        )
        append_file(
            TRADES_FILE,
            "=" * 80
        )

    if not os.path.exists(STATS_FILE):
        append_file(
            STATS_FILE,
            f"{BOT_NAME} STATISTICS"
        )


# ============================================================
# STATE
# ============================================================

def default_state():

    return {
        "balance": STARTING_BALANCE,
        "open_trades": [],
        "closed_trades": [],
        "watchlist": {},
        "seen_tokens": {},
        "milestones": {
            "2X": 0,
            "5X": 0,
            "10X": 0,
            "50X": 0,
            "100X": 0
        },
        "peak_equity": STARTING_BALANCE,
        "max_drawdown": 0.0,
        "total_scans": 0
    }


def load_state():

    if not os.path.exists(STATE_FILE):
        return default_state()

    try:

        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        base = default_state()

        for key, value in base.items():

            if key not in state:
                state[key] = value

        return state

    except Exception as e:

        print(f"{YELLOW}Could not load state: {e}{RESET}")
        print("Starting fresh paper state.")

        return default_state()


def save_state(state):

    try:

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    except Exception as e:

        print(f"{RED}State save error: {e}{RESET}")


# ============================================================
# API
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD-V6-PAPER-BOT/1.0"
})


def api_get(endpoint):

    url = BASE_URL + endpoint

    try:

        response = session.get(
            url,
            timeout=20
        )

        if response.status_code == 429:

            print(
                f"{YELLOW}Rate limited. Waiting 20 seconds...{RESET}"
            )

            time.sleep(20)

            return []

        if response.status_code != 200:

            print(
                f"{YELLOW}API {response.status_code}: {endpoint}{RESET}"
            )

            return []

        return response.json()

    except Exception as e:

        print(
            f"{RED}API error: {e}{RESET}"
        )

        return []


# ============================================================
# DISCOVERY
# ============================================================

def discover_tokens():

    found = {}

    endpoints = [

        "/token-profiles/latest/v1",

        "/token-boosts/latest/v1",

        "/token-boosts/top/v1",

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

            address = item.get("tokenAddress")

            if not address:
                continue

            found[address] = {
                "address": address,
                "source": endpoint
            }

    return found


# ============================================================
# PAIR DATA
# ============================================================

def get_best_pair(address):

    data = api_get(
        f"/token-pairs/v1/solana/{address}"
    )

    if not isinstance(data, list):
        return None

    sol_pairs = []

    for pair in data:

        if str(pair.get("chainId", "")).lower() != "solana":
            continue

        liquidity = safe_float(
            pair.get("liquidity", {}).get("usd")
        )

        sol_pairs.append(
            (liquidity, pair)
        )

    if not sol_pairs:
        return None

    sol_pairs.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return sol_pairs[0][1]


# ============================================================
# NORMALIZE PAIR
# ============================================================

def normalize_pair(pair, source="unknown"):

    if not pair:
        return None

    base = pair.get("baseToken", {})
    quote = pair.get("quoteToken", {})

    address = base.get("address")

    if not address:
        return None

    pair_id = pair.get("pairAddress", "")

    pair_url = pair.get("url")

    if not pair_url and pair_id:
        pair_url = (
            f"https://dexscreener.com/solana/{pair_id}"
        )

    txns = pair.get("txns", {})

    m5 = txns.get("m5", {}) or {}
    h1 = txns.get("h1", {}) or {}

    m5_buys = int(
        safe_float(m5.get("buys"))
    )

    m5_sells = int(
        safe_float(m5.get("sells"))
    )

    h1_buys = int(
        safe_float(h1.get("buys"))
    )

    h1_sells = int(
        safe_float(h1.get("sells"))
    )

    m5_total = m5_buys + m5_sells

    h1_total = h1_buys + h1_sells

    buy_pressure = 0

    if m5_total > 0:
        buy_pressure = (
            m5_buys / m5_total
        ) * 100

    return {

        # IDs
        "address": address,
        "token_id": address,
        "pair_id": pair_id,
        "pair_url": pair_url or "",

        # Identity
        "symbol": base.get("symbol", "UNKNOWN"),
        "name": base.get("name", "UNKNOWN"),

        "quote_symbol": quote.get(
            "symbol",
            ""
        ),

        # Price
        "price": safe_float(
            pair.get("priceUsd")
        ),

        # Market
        "market_cap": safe_float(
            pair.get("marketCap")
        ),

        "fdv": safe_float(
            pair.get("fdv")
        ),

        "liquidity": safe_float(
            pair.get(
                "liquidity",
                {}
            ).get("usd")
        ),

        # Volume
        "volume_m5": safe_float(
            pair.get(
                "volume",
                {}
            ).get("m5")
        ),

        "volume_h1": safe_float(
            pair.get(
                "volume",
                {}
            ).get("h1")
        ),

        # Transactions
        "m5_buys": m5_buys,
        "m5_sells": m5_sells,
        "m5_total": m5_total,

        "h1_buys": h1_buys,
        "h1_sells": h1_sells,
        "h1_total": h1_total,

        "buy_pressure": buy_pressure,

        # Price change
        "change_m5": safe_float(
            pair.get(
                "priceChange",
                {}
            ).get("m5")
        ),

        "change_h1": safe_float(
            pair.get(
                "priceChange",
                {}
            ).get("h1")
        ),

        "change_h6": safe_float(
            pair.get(
                "priceChange",
                {}
            ).get("h6")
        ),

        "change_h24": safe_float(
            pair.get(
                "priceChange",
                {}
            ).get("h24")
        ),

        "pair_created": pair.get(
            "pairCreatedAt"
        ),

        "source": source
    }


# ============================================================
# SCORE
# ============================================================

def calculate_score(data, previous=None):

    score = 0

    liquidity = data["liquidity"]
    volume5 = data["volume_m5"]
    volume1h = data["volume_h1"]
    buys = data["buy_pressure"]

    m5 = data["change_m5"]
    h1 = data["change_h1"]
    h6 = data["change_h6"]

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 100000:
        score += 15

    elif liquidity >= 50000:
        score += 13

    elif liquidity >= 25000:
        score += 10

    elif liquidity >= 15000:
        score += 6

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if volume5 >= 50000:
        score += 20

    elif volume5 >= 20000:
        score += 17

    elif volume5 >= 10000:
        score += 14

    elif volume5 >= 5000:
        score += 10

    # --------------------------------------------------------
    # 1H VOLUME
    # --------------------------------------------------------

    if volume1h >= 500000:
        score += 10

    elif volume1h >= 200000:
        score += 8

    elif volume1h >= 50000:
        score += 6

    elif volume1h >= 20000:
        score += 4

    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    if buys >= 70:
        score += 20

    elif buys >= 65:
        score += 17

    elif buys >= 60:
        score += 14

    elif buys >= 58:
        score += 11

    # --------------------------------------------------------
    # 5M MOMENTUM
    # --------------------------------------------------------

    if 3 <= m5 <= 15:
        score += 15

    elif 0 < m5 < 3:
        score += 9

    elif m5 > 15:
        score += 5

    # --------------------------------------------------------
    # 1H TREND
    # --------------------------------------------------------

    if h1 >= 20:
        score += 12

    elif h1 >= 10:
        score += 10

    elif h1 > 0:
        score += 7

    # --------------------------------------------------------
    # 6H TREND
    # --------------------------------------------------------

    if h6 >= 50:
        score += 6

    elif h6 >= 20:
        score += 5

    elif h6 > 0:
        score += 3

    # --------------------------------------------------------
    # IMPROVEMENT
    # --------------------------------------------------------

    if previous:

        previous_m5 = previous.get(
            "change_m5",
            0
        )

        previous_buy = previous.get(
            "buy_pressure",
            0
        )

        previous_volume = previous.get(
            "volume_m5",
            0
        )

        if m5 > previous_m5:
            score += 6

        if buys > previous_buy:
            score += 5

        if volume5 > previous_volume:
            score += 5

    return max(
        0,
        min(100, score)
    )


# ============================================================
# ENTRY ANALYSIS
# ============================================================

def analyze_entry(data, previous, score):

    if data["liquidity"] < MIN_LIQUIDITY:
        return False, "liquidity too low"

    if data["volume_m5"] < MIN_VOLUME_5M:
        return False, "5m volume too low"

    if data["buy_pressure"] < MIN_BUY_PRESSURE:
        return False, "buy pressure too weak"

    if score < ENTRY_SCORE:
        return False, f"score {score} below {ENTRY_SCORE}"

    if data["change_h1"] <= 0:
        return False, "1h trend not positive"

    if data["change_m5"] > MAX_ENTRY_SPIKE_5M:
        return False, "5m spike too extended"

    if previous is None:
        return False, "waiting for confirmation"

    previous_m5 = previous.get(
        "change_m5",
        0
    )

    previous_buy = previous.get(
        "buy_pressure",
        0
    )

    previous_volume = previous.get(
        "volume_m5",
        0
    )

    momentum_improving = (
        data["change_m5"] >
        previous_m5
    )

    buying_improving = (
        data["buy_pressure"] >
        previous_buy
    )

    volume_improving = (
        data["volume_m5"] >
        previous_volume
    )

    recovery = (
        previous_m5 <= 0
        and data["change_m5"] > 0
        and buying_improving
    )

    continuation = (
        data["change_m5"] > 0
        and momentum_improving
        and (
            volume_improving
            or buying_improving
        )
    )

    strong_buying = (
        data["buy_pressure"] >= 65
        and data["change_m5"] >= 0
        and (
            buying_improving
            or volume_improving
        )
    )

    if recovery:
        return True, "PULLBACK RECOVERY"

    if continuation:
        return True, "MOMENTUM CONTINUATION"

    if strong_buying:
        return True, "STRONG BUY PRESSURE"

    return False, "confirmation conditions not met"


# ============================================================
# TRADE LOOKUP
# ============================================================

def find_open_trade(state, address):

    for trade in state["open_trades"]:

        if trade["address"] == address:
            return trade

    return None


# ============================================================
# MILESTONES
# ============================================================

def check_milestones(state, trade, current_price):

    entry = trade["entry_price"]

    if entry <= 0:
        return

    multiple = current_price / entry

    milestones = [

        ("2X", 2),
        ("5X", 5),
        ("10X", 10),
        ("50X", 50),
        ("100X", 100),

    ]

    for name, target in milestones:

        if (
            multiple >= target
            and name not in trade["milestones_hit"]
        ):

            trade["milestones_hit"].append(
                name
            )

            state["milestones"][name] += 1

            message = (
                f"\n"
                f"{'=' * 70}\n"
                f"🚀 {BOT_NAME} MILESTONE\n"
                f"Token: {trade['symbol']}\n"
                f"Token ID: {trade['address']}\n"
                f"Pair ID: {trade['pair_id']}\n"
                f"Pair URL: {trade['pair_url']}\n"
                f"MILESTONE: {name}\n"
                f"Multiple: {multiple:.2f}X\n"
                f"Entry: ${entry:.10f}\n"
                f"Current: ${current_price:.10f}\n"
                f"Time: {now()}\n"
                f"{'=' * 70}\n"
            )

            print(
                f"{MAGENTA}{message}{RESET}"
            )

            append_file(
                TRADES_FILE,
                message
            )


# ============================================================
# TRAILING STOP
# ============================================================

def get_trailing_stop(trade):

    entry = trade["entry_price"]
    highest = trade["highest_price"]

    if entry <= 0:
        return None

    gain = (
        highest / entry
    ) - 1

    applicable = None

    for minimum_gain, trail in TRAILING_LEVELS:

        if gain >= minimum_gain:
            applicable = trail

    if applicable is None:
        return None

    return highest * (
        1 - applicable
    )


# ============================================================
# UPDATE OPEN TRADES
# ============================================================

def update_open_trades(state, market_data):

    for trade in list(
        state["open_trades"]
    ):

        address = trade["address"]

        data = market_data.get(address)

        if not data:
            continue

        current_price = data["price"]

        if current_price <= 0:
            continue

        entry_price = trade["entry_price"]

        if entry_price <= 0:
            continue

        if current_price > trade["highest_price"]:

            trade["highest_price"] = current_price

        highest = trade["highest_price"]

        gain = (
            current_price / entry_price
        ) - 1

        max_multiple = (
            highest / entry_price
        )

        trade["max_multiple"] = max_multiple

        check_milestones(
            state,
            trade,
            current_price
        )

        # ----------------------------------------------------
        # EXIT DECISION
        # ----------------------------------------------------

        exit_reason = None

        # Initial protection
        if gain <= INITIAL_STOP:

            exit_reason = "INITIAL STOP"

        # Dynamic trailing
        trailing_stop = get_trailing_stop(
            trade
        )

        if (
            trailing_stop is not None
            and current_price <= trailing_stop
        ):

            exit_reason = (
                "TRAILING STOP"
            )

        # Maximum holding time
        try:

            entry_time = datetime.fromisoformat(
                trade["entry_time"]
            )

            hours = (
                datetime.now(timezone.utc)
                - entry_time
            ).total_seconds() / 3600

        except:

            hours = 0

        if hours >= MAX_HOLD_HOURS:

            exit_reason = "MAX HOLD TIME"

        if exit_reason:

            close_trade(
                state,
                trade,
                data,
                exit_reason
            )


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(
    state,
    trade,
    data,
    reason
):

    current_price = data["price"]

    entry_price = trade["entry_price"]

    if entry_price <= 0:
        return

    multiple = (
        current_price / entry_price
    )

    return_value = (
        trade["stake"] * multiple
    )

    profit = (
        return_value -
        trade["stake"]
    )

    state["balance"] += return_value

    trade["exit_price"] = current_price

    trade["exit_time"] = now()

    trade["exit_reason"] = reason

    trade["profit"] = profit

    trade["return_value"] = return_value

    trade["final_multiple"] = multiple

    state["closed_trades"].append(
        trade
    )

    state["open_trades"].remove(
        trade
    )

    if profit >= 0:

        result_color = GREEN

    else:

        result_color = RED

    message = (
        f"\n"
        f"{'=' * 75}\n"
        f"{'🟢 PAPER EXIT' if profit >= 0 else '🔴 PAPER EXIT'}\n"
        f"Token: {trade['symbol']}\n"
        f"Name: {trade['name']}\n"
        f"Token ID: {trade['address']}\n"
        f"Pair ID: {trade['pair_id']}\n"
        f"Pair URL: {trade['pair_url']}\n"
        f"Entry Price: ${entry_price:.10f}\n"
        f"Exit Price: ${current_price:.10f}\n"
        f"Highest Price: ${trade['highest_price']:.10f}\n"
        f"Maximum Multiple: {trade['max_multiple']:.2f}X\n"
        f"Final Multiple: {multiple:.2f}X\n"
        f"Stake: ${trade['stake']:.2f}\n"
        f"Return: ${return_value:.2f}\n"
        f"P/L: ${profit:.2f}\n"
        f"Reason: {reason}\n"
        f"Balance: ${state['balance']:.2f}\n"
        f"Time: {now()}\n"
        f"{'=' * 75}\n"
    )

    print(
        f"{result_color}{message}{RESET}"
    )

    append_file(
        TRADES_FILE,
        message
    )


# ============================================================
# OPEN PAPER TRADE
# ============================================================

def open_trade(
    state,
    data,
    score,
    reason
):

    if len(
        state["open_trades"]
    ) >= MAX_OPEN_TRADES:

        return False

    if state["balance"] < PAPER_TRADE_SIZE:

        return False

    if find_open_trade(
        state,
        data["address"]
    ):

        return False

    trade = {

        "address": data["address"],

        "token_id": data["token_id"],

        "pair_id": data["pair_id"],

        "pair_url": data["pair_url"],

        "symbol": data["symbol"],

        "name": data["name"],

        "entry_price": data["price"],

        "highest_price": data["price"],

        "stake": PAPER_TRADE_SIZE,

        "entry_time": datetime.now(
            timezone.utc
        ).isoformat(),

        "source": data["source"],

        "entry_score": score,

        "entry_reason": reason,

        "entry_liquidity": data["liquidity"],

        "entry_volume_5m": data["volume_m5"],

        "entry_buy_pressure": data[
            "buy_pressure"
        ],

        "entry_m5_buys": data[
            "m5_buys"
        ],

        "entry_m5_sells": data[
            "m5_sells"
        ],

        "milestones_hit": [],

        "max_multiple": 1.0

    }

    state["balance"] -= PAPER_TRADE_SIZE

    state["open_trades"].append(
        trade
    )

    message = (
        f"\n"
        f"{'=' * 75}\n"
        f"🟢 PAPER ENTRY\n"
        f"Token: {data['symbol']}\n"
        f"Name: {data['name']}\n"
        f"Token ID: {data['address']}\n"
        f"Pair ID: {data['pair_id']}\n"
        f"Pair URL: {data['pair_url']}\n"
        f"Entry Price: ${data['price']:.10f}\n"
        f"Score: {score}/100\n"
        f"Reason: {reason}\n"
        f"Liquidity: ${data['liquidity']:,.2f}\n"
        f"5M Volume: ${data['volume_m5']:,.2f}\n"
        f"5M Buys: {data['m5_buys']}\n"
        f"5M Sells: {data['m5_sells']}\n"
        f"5M Transactions: {data['m5_total']}\n"
        f"Buy Pressure: {data['buy_pressure']:.2f}%\n"
        f"5M Change: {data['change_m5']:.2f}%\n"
        f"1H Change: {data['change_h1']:.2f}%\n"
        f"6H Change: {data['change_h6']:.2f}%\n"
        f"Stake: ${PAPER_TRADE_SIZE:.2f}\n"
        f"Balance: ${state['balance']:.2f}\n"
        f"Time: {now()}\n"
        f"{'=' * 75}\n"
    )

    print(
        f"{GREEN}{message}{RESET}"
    )

    append_file(
        TRADES_FILE,
        message
    )

    return True


# ============================================================
# TARGET LOG
# ============================================================

def log_target(
    data,
    score,
    reason
):

    text = (
        f"\n"
        f"[{now()}]\n"
        f"TARGET\n"
        f"Symbol: {data['symbol']}\n"
        f"Name: {data['name']}\n"
        f"Token ID: {data['address']}\n"
        f"Pair ID: {data['pair_id']}\n"
        f"Pair URL: {data['pair_url']}\n"
        f"Score: {score}/100\n"
        f"Reason: {reason}\n"
        f"Price: ${data['price']:.10f}\n"
        f"Liquidity: ${data['liquidity']:,.2f}\n"
        f"5M Volume: ${data['volume_m5']:,.2f}\n"
        f"5M Buys: {data['m5_buys']}\n"
        f"5M Sells: {data['m5_sells']}\n"
        f"5M Transactions: {data['m5_total']}\n"
        f"Buy Pressure: {data['buy_pressure']:.2f}%\n"
        f"5M Change: {data['change_m5']:.2f}%\n"
        f"1H Change: {data['change_h1']:.2f}%\n"
    )

    append_file(
        TARGETS_FILE,
        text
    )


# ============================================================
# EQUITY / DRAWDOWN
# ============================================================

def update_equity_stats(state, market_data):

    equity = state["balance"]

    for trade in state["open_trades"]:

        data = market_data.get(
            trade["address"]
        )

        if not data:
            continue

        entry = trade["entry_price"]

        price = data["price"]

        if entry <= 0:
            continue

        marked_value = (
            trade["stake"]
            * (price / entry)
        )

        equity += marked_value

    if equity > state["peak_equity"]:

        state["peak_equity"] = equity

    peak = state["peak_equity"]

    if peak > 0:

        drawdown = (
            peak - equity
        ) / peak

        if drawdown > state["max_drawdown"]:

            state["max_drawdown"] = drawdown


# ============================================================
# STATS
# ============================================================

def calculate_stats(state):

    closed = state["closed_trades"]

    wins = [
        t for t in closed
        if t.get("profit", 0) > 0
    ]

    losses = [
        t for t in closed
        if t.get("profit", 0) < 0
    ]

    gross_profit = sum(
        t.get("profit", 0)
        for t in wins
    )

    gross_loss = sum(
        t.get("profit", 0)
        for t in losses
    )

    total_profit = sum(
        t.get("profit", 0)
        for t in closed
    )

    total = len(closed)

    win_rate = (
        len(wins) / total * 100
        if total
        else 0
    )

    if gross_loss < 0:

        profit_factor = (
            gross_profit /
            abs(gross_loss)
        )

    else:

        profit_factor = 0

    best = max(
        (
            t.get("profit", 0)
            for t in closed
        ),
        default=0
    )

    worst = min(
        (
            t.get("profit", 0)
            for t in closed
        ),
        default=0
    )

    return {

        "closed": total,

        "wins": len(wins),

        "losses": len(losses),

        "win_rate": win_rate,

        "gross_profit": gross_profit,

        "gross_loss": gross_loss,

        "total_profit": total_profit,

        "profit_factor": profit_factor,

        "best": best,

        "worst": worst

    }


def write_stats(state):

    stats = calculate_stats(
        state
    )

    text = (
        f"{'=' * 75}\n"
        f"{BOT_NAME} STATISTICS\n"
        f"Updated: {now()}\n"
        f"{'=' * 75}\n\n"

        f"Balance: ${state['balance']:.2f}\n"
        f"Peak Equity: ${state['peak_equity']:.2f}\n"
        f"Max Drawdown: "
        f"{state['max_drawdown'] * 100:.2f}%\n\n"

        f"Open Trades: "
        f"{len(state['open_trades'])}\n"

        f"Closed Trades: "
        f"{stats['closed']}\n"

        f"Wins: "
        f"{stats['wins']}\n"

        f"Losses: "
        f"{stats['losses']}\n"

        f"Win Rate: "
        f"{stats['win_rate']:.2f}%\n\n"

        f"Gross Profit: "
        f"${stats['gross_profit']:.2f}\n"

        f"Gross Loss: "
        f"${stats['gross_loss']:.2f}\n"

        f"Realized P/L: "
        f"${stats['total_profit']:.2f}\n"

        f"Profit Factor: "
        f"{stats['profit_factor']:.2f}\n"

        f"Best Trade: "
        f"${stats['best']:.2f}\n"

        f"Worst Trade: "
        f"${stats['worst']:.2f}\n\n"

        f"2X Hits: "
        f"{state['milestones']['2X']}\n"

        f"5X Hits: "
        f"{state['milestones']['5X']}\n"

        f"10X Hits: "
        f"{state['milestones']['10X']}\n"

        f"50X Hits: "
        f"{state['milestones']['50X']}\n"

        f"100X Hits: "
        f"{state['milestones']['100X']}\n\n"

        f"ENTRY SETTINGS\n"

        f"Entry Score: "
        f"{ENTRY_SCORE}\n"

        f"Min Liquidity: "
        f"${MIN_LIQUIDITY:,.0f}\n"

        f"Min 5M Volume: "
        f"${MIN_VOLUME_5M:,.0f}\n"

        f"Min Buy Pressure: "
        f"{MIN_BUY_PRESSURE}%\n"

        f"Max Entry Spike: "
        f"{MAX_ENTRY_SPIKE_5M}%\n\n"

        f"RISK SETTINGS\n"

        f"Initial Stop: "
        f"{INITIAL_STOP * 100:.0f}%\n"

        f"Max Hold: "
        f"{MAX_HOLD_HOURS} hours\n"

        f"{'=' * 75}\n"
    )

    try:

        with open(
            STATS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(text)

    except Exception as e:

        print(
            f"{RED}Stats error: {e}{RESET}"
        )


# ============================================================
# DISPLAY
# ============================================================

def display_market(data, score):

    print(
        f"{CYAN}"
        f"{data['symbol']:<12}"
        f" Score:{score:>3}"
        f" 5M:{data['change_m5']:>7.2f}%"
        f" 1H:{data['change_h1']:>7.2f}%"
        f" Buy:{data['buy_pressure']:>6.1f}%"
        f" Liq:${data['liquidity']:>10,.0f}"
        f" Vol5:${data['volume_m5']:>10,.0f}"
        f"{RESET}"
    )


def display_open_trades(state, market_data):

    if not state["open_trades"]:
        return

    print(
        f"\n{WHITE}"
        f"OPEN PAPER TRADES"
        f"{RESET}"
    )

    for trade in state["open_trades"]:

        data = market_data.get(
            trade["address"]
        )

        if not data:
            continue

        entry = trade["entry_price"]

        price = data["price"]

        if entry <= 0:
            continue

        gain = (
            price / entry
            - 1
        ) * 100

        multiple = (
            price / entry
        )

        color = (
            GREEN
            if gain >= 0
            else RED
        )

        print(
            f"{color}"
            f"{trade['symbol']:<10}"
            f" {gain:>8.2f}%"
            f" {multiple:>7.2f}X"
            f" High:{trade['max_multiple']:>7.2f}X"
            f"{RESET}"
        )


# ============================================================
# MAIN SCAN
# ============================================================

def scan(state):

    print(
        f"\n{BLUE}"
        f"{'=' * 80}\n"
        f"{BOT_NAME}\n"
        f"Paper scan: {now()}\n"
        f"Balance: ${state['balance']:.2f}\n"
        f"Open: {len(state['open_trades'])}/{MAX_OPEN_TRADES}\n"
        f"{'=' * 80}"
        f"{RESET}"
    )

    discovered = discover_tokens()

    print(
        f"{WHITE}"
        f"Discovered: {len(discovered)} Solana tokens"
        f"{RESET}"
    )

    market_data = {}

    candidates = []

    for address, info in discovered.items():

        pair = get_best_pair(
            address
        )

        if not pair:
            continue

        data = normalize_pair(
            pair,
            info["source"]
        )

        if not data:
            continue

        if data["price"] <= 0:
            continue

        market_data[address] = data

        previous = state["watchlist"].get(
            address
        )

        score = calculate_score(
            data,
            previous
        )

        state["watchlist"][address] = data

        if score >= WATCH_SCORE:

            candidates.append(
                (
                    score,
                    data,
                    previous
                )
            )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    print(
        f"{YELLOW}"
        f"Quality candidates: {len(candidates)}"
        f"{RESET}"
    )

    for score, data, previous in candidates[:15]:

        display_market(
            data,
            score
        )

        valid, reason = analyze_entry(
            data,
            previous,
            score
        )

        if valid:

            log_target(
                data,
                score,
                reason
            )

            print(
                f"{GREEN}"
                f"  >>> ENTRY SIGNAL: "
                f"{reason}"
                f"{RESET}"
            )

            if len(
                state["open_trades"]
            ) < MAX_OPEN_TRADES:

                open_trade(
                    state,
                    data,
                    score,
                    reason
                )

        else:

            if score >= ENTRY_SCORE - 3:

                print(
                    f"{YELLOW}"
                    f"  Near-entry: {reason}"
                    f"{RESET}"
                )

    # --------------------------------------------------------
    # Update trades AFTER new market data
    # --------------------------------------------------------

    update_open_trades(
        state,
        market_data
    )

    update_equity_stats(
        state,
        market_data
    )

    display_open_trades(
        state,
        market_data
    )

    state["total_scans"] += 1

    save_state(
        state
    )

    write_stats(
        state
    )


# ============================================================
# STARTUP
# ============================================================

def print_banner():

    print(
        f"{MAGENTA}"
        f"""
╔══════════════════════════════════════════════════════════════════════╗
║                       ALVIN MEME GOD V6                             ║
║                 QUALITY ENTRY + RUNNER ENGINE                       ║
║                                                                      ║
║                     PAPER TRADING ONLY                              ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        f"{RESET}"
    )

    print(
        f"{CYAN}"
        f"Entry Score       : {ENTRY_SCORE}\n"
        f"Minimum Liquidity: ${MIN_LIQUIDITY:,.0f}\n"
        f"Minimum 5M Volume: ${MIN_VOLUME_5M:,.0f}\n"
        f"Buy Pressure     : {MIN_BUY_PRESSURE}%\n"
        f"Initial Stop     : {INITIAL_STOP * 100:.0f}%\n"
        f"Take Profit      : NONE — runners allowed\n"
        f"Max Hold         : {MAX_HOLD_HOURS} hours\n"
        f"Trade Size       : ${PAPER_TRADE_SIZE:.2f}\n"
        f"Max Open Trades  : {MAX_OPEN_TRADES}\n"
        f"{RESET}"
    )


def main():

    initialize_files()

    state = load_state()

    print_banner()

    print(
        f"{WHITE}"
        f"State loaded."
        f" Balance: ${state['balance']:.2f}"
        f" | Open trades: {len(state['open_trades'])}"
        f"{RESET}"
    )

    while True:

        try:

            scan(state)

            print(
                f"\n{YELLOW}"
                f"Next scan in {SCAN_INTERVAL} seconds..."
                f"{RESET}"
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                f"\n{YELLOW}"
                f"Stopping ALVIN MEME GOD V6..."
                f"{RESET}"
            )

            save_state(
                state
            )

            write_stats(
                state
            )

            break

        except Exception as e:

            print(
                f"\n{RED}"
                f"MAIN LOOP ERROR: {e}"
                f"{RESET}"
            )

            time.sleep(10)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
