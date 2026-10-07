import os
import time
import json
import math
import requests
from datetime import datetime, timezone

# ============================================================
# ALVIN MEME GOD V6.1
# QUALITY ENTRY + RUNNER STRATEGY
# 1 SECOND TERMINAL / 30 SECOND ANALYSIS
# PAPER TRADING ONLY
# ============================================================

BOT_NAME = "ALVIN MEME GOD V6.1"

BASE_URL = "https://api.dexscreener.com"

# ============================================================
# CORE SETTINGS
# ============================================================

SCAN_INTERVAL = 30
TERMINAL_REFRESH = 1

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# ============================================================
# ENTRY SETTINGS
# ============================================================

ENTRY_SCORE = 82
WATCH_SCORE = 70

MIN_LIQUIDITY = 25000
MIN_VOLUME_5M = 5000
MIN_BUY_PRESSURE = 58

MAX_ENTRY_SPIKE_5M = 20.0

# ============================================================
# RISK MANAGEMENT
# ============================================================

INITIAL_STOP = -0.10

MAX_HOLD_HOURS = 6

# gain from entry -> allowed pullback from highest price

TRAILING_LEVELS = [
    (0.15, 0.08),   # +15%  -> 8% trail
    (0.30, 0.12),   # +30%  -> 12% trail
    (1.00, 0.18),   # 2X    -> 18% trail
    (5.00, 0.22),   # 6X    -> 22% trail
    (10.00, 0.25),  # 11X   -> 25% trail
    (50.00, 0.30),  # 51X   -> 30% trail
]

# ============================================================
# FILES
# ============================================================

TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_V6_1_STATE.json"

# ============================================================
# API SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD/6.1"
})


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def now_utc():
    return datetime.now(timezone.utc)


def timestamp():
    return now_utc().strftime("%Y-%m-%d %H:%M:%S UTC")


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except Exception:
        return default


def pct(value):
    return f"{safe_float(value) * 100:.2f}%"


def money(value):
    return f"${safe_float(value):,.2f}"


def price(value):
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


def clear_terminal():
    os.system("clear")


# ============================================================
# FILE INITIALIZATION
# ============================================================

def initialize_files():

    if not os.path.exists(TARGETS_FILE):
        with open(TARGETS_FILE, "w", encoding="utf-8") as f:
            f.write(
                "ALVIN MEME GOD V6.1 TARGET LOG\n"
                "========================================\n\n"
            )

    if not os.path.exists(TRADES_FILE):
        with open(TRADES_FILE, "w", encoding="utf-8") as f:
            f.write(
                "ALVIN MEME GOD V6.1 TRADE LOG\n"
                "========================================\n\n"
            )

    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            f.write(
                "ALVIN MEME GOD V6.1 STATISTICS\n"
                "========================================\n\n"
            )


# ============================================================
# STATE
# ============================================================

def default_state():

    return {
        "balance": STARTING_BALANCE,
        "open_trades": {},
        "closed_trades": [],
        "watchlist": {},
        "seen_tokens": [],
        "milestones": {
            "2X": 0,
            "5X": 0,
            "10X": 0,
            "50X": 0,
            "100X": 0
        },
        "peak_balance": STARTING_BALANCE,
        "max_drawdown": 0.0,
        "total_entries": 0,
        "total_exits": 0
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

        print("State load error:", e)

        return default_state()


def save_state(state):

    try:

        temp_file = STATE_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        os.replace(temp_file, STATE_FILE)

    except Exception as e:

        print("State save error:", e)


# ============================================================
# HTTP GET
# ============================================================

def api_get(endpoint):

    url = BASE_URL + endpoint

    try:

        response = session.get(
            url,
            timeout=15
        )

        if response.status_code == 429:

            time.sleep(20)

            response = session.get(
                url,
                timeout=15
            )

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


# ============================================================
# DISCOVERY
# ============================================================

def discover_tokens():

    candidates = {}

    endpoints = [
        "/token-profiles/latest/v1",
        "/token-boosts/latest/v1",
        "/token-boosts/top/v1"
    ]

    for endpoint in endpoints:

        data = api_get(endpoint)

        if not data:
            continue

        if isinstance(data, dict):
            items = data.get("pairs", [])
        else:
            items = data

        if not isinstance(items, list):
            continue

        for item in items:

            if not isinstance(item, dict):
                continue

            address = item.get("tokenAddress")

            if not address:
                address = item.get("address")

            if not address:
                continue

            candidates[address] = {
                "address": address,
                "source": endpoint
            }

    return list(candidates.values())


# ============================================================
# GET TOKEN PAIRS
# ============================================================

def get_pairs(token_address):

    endpoint = f"/token-pairs/v1/solana/{token_address}"

    data = api_get(endpoint)

    if not data:
        return []

    if isinstance(data, dict):
        pairs = data.get("pairs", [])
    else:
        pairs = data

    if not isinstance(pairs, list):
        return []

    return pairs


# ============================================================
# NORMALIZE PAIR
# ============================================================

def normalize_pair(pair, source="unknown"):

    if not isinstance(pair, dict):
        return None

    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}

    address = base.get("address")

    if not address:
        return None

    symbol = base.get("symbol") or "UNKNOWN"
    name = base.get("name") or symbol

    pair_id = pair.get("pairAddress") or ""

    pair_url = pair.get("url")

    if not pair_url and pair_id:
        pair_url = f"https://dexscreener.com/solana/{pair_id}"

    liquidity = pair.get("liquidity") or {}

    volume = pair.get("volume") or {}

    txns = pair.get("txns") or {}

    m5 = txns.get("m5") or {}
    h1 = txns.get("h1") or {}

    m5_buys = int(safe_float(m5.get("buys")))
    m5_sells = int(safe_float(m5.get("sells")))

    h1_buys = int(safe_float(h1.get("buys")))
    h1_sells = int(safe_float(h1.get("sells")))

    m5_total = m5_buys + m5_sells
    h1_total = h1_buys + h1_sells

    if m5_total > 0:
        buy_pressure = (
            m5_buys / m5_total
        ) * 100
    else:
        buy_pressure = 0

    price_usd = safe_float(pair.get("priceUsd"))

    market_cap = safe_float(pair.get("marketCap"))

    fdv = safe_float(pair.get("fdv"))

    liquidity_usd = safe_float(
        liquidity.get("usd")
    )

    volume_m5 = safe_float(
        volume.get("m5")
    )

    volume_h1 = safe_float(
        volume.get("h1")
    )

    price_change = pair.get("priceChange") or {}

    m5_change = safe_float(
        price_change.get("m5")
    )

    h1_change = safe_float(
        price_change.get("h1")
    )

    h6_change = safe_float(
        price_change.get("h6")
    )

    h24_change = safe_float(
        price_change.get("h24")
    )

    pair_created = pair.get(
        "pairCreatedAt"
    )

    return {

        "address": address,

        "symbol": symbol,
        "name": name,

        "pair_id": pair_id,
        "pair_url": pair_url,

        "price": price_usd,

        "market_cap": market_cap,
        "fdv": fdv,

        "liquidity": liquidity_usd,

        "volume_m5": volume_m5,
        "volume_h1": volume_h1,

        "m5_buys": m5_buys,
        "m5_sells": m5_sells,
        "m5_total": m5_total,

        "h1_buys": h1_buys,
        "h1_sells": h1_sells,
        "h1_total": h1_total,

        "buy_pressure": buy_pressure,

        "m5": m5_change,
        "h1": h1_change,
        "h6": h6_change,
        "h24": h24_change,

        "pair_created_at": pair_created,

        "source": source
    }


# ============================================================
# SCORE TOKEN
# ============================================================

def score_token(data, previous=None):

    score = 0

    liquidity = data["liquidity"]
    volume_m5 = data["volume_m5"]
    volume_h1 = data["volume_h1"]
    buy_pressure = data["buy_pressure"]

    m5 = data["m5"]
    h1 = data["h1"]
    h6 = data["h6"]

    market_cap = data["market_cap"]

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 25000:
        score += 15

    elif liquidity >= 15000:
        score += 10

    elif liquidity >= 7500:
        score += 5

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if volume_m5 >= 50000:
        score += 20

    elif volume_m5 >= 20000:
        score += 16

    elif volume_m5 >= 10000:
        score += 12

    elif volume_m5 >= 5000:
        score += 8

    # --------------------------------------------------------
    # 1H VOLUME
    # --------------------------------------------------------

    if volume_h1 >= 250000:
        score += 10

    elif volume_h1 >= 100000:
        score += 8

    elif volume_h1 >= 50000:
        score += 6

    elif volume_h1 >= 20000:
        score += 4

    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    if buy_pressure >= 70:
        score += 20

    elif buy_pressure >= 65:
        score += 17

    elif buy_pressure >= 60:
        score += 14

    elif buy_pressure >= 58:
        score += 10

    elif buy_pressure >= 53:
        score += 5

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    if m5 >= 10:
        score += 15

    elif m5 >= 5:
        score += 12

    elif m5 >= 2:
        score += 9

    elif m5 > 0:
        score += 5

    # --------------------------------------------------------
    # 1H TREND
    # --------------------------------------------------------

    if h1 >= 30:
        score += 12

    elif h1 >= 15:
        score += 10

    elif h1 >= 5:
        score += 7

    elif h1 > 0:
        score += 4

    # --------------------------------------------------------
    # 6H TREND
    # --------------------------------------------------------

    if h6 >= 50:
        score += 6

    elif h6 >= 20:
        score += 4

    elif h6 > 0:
        score += 2

    # --------------------------------------------------------
    # LIQUIDITY / MARKET CAP
    # --------------------------------------------------------

    if market_cap > 0:

        ratio = liquidity / market_cap

        if ratio >= 0.20:
            score += 6

        elif ratio >= 0.10:
            score += 4

        elif ratio >= 0.05:
            score += 2

    # --------------------------------------------------------
    # IMPROVEMENT
    # --------------------------------------------------------

    if previous:

        if data["m5"] > previous.get("m5", 0):
            score += 6

        if data["buy_pressure"] > previous.get(
            "buy_pressure", 0
        ):
            score += 5

        if data["volume_m5"] > previous.get(
            "volume_m5", 0
        ):
            score += 5

    return max(0, min(100, score))


# ============================================================
# ENTRY SIGNAL
# ============================================================

def entry_signal(data, previous, score):

    if not previous:
        return False, "No previous confirmation"

    if data["liquidity"] < MIN_LIQUIDITY:
        return False, "Liquidity too low"

    if data["volume_m5"] < MIN_VOLUME_5M:
        return False, "5M volume too low"

    if data["buy_pressure"] < MIN_BUY_PRESSURE:
        return False, "Buy pressure too low"

    if data["h1"] <= 0:
        return False, "1H trend not positive"

    if score < ENTRY_SCORE:
        return False, "Score below entry threshold"

    # --------------------------------------------------------
    # Avoid buying a vertical candle
    # --------------------------------------------------------

    if data["m5"] > MAX_ENTRY_SPIKE_5M:
        return False, "5M spike too large"

    previous_m5 = previous.get(
        "m5",
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
        data["m5"] > previous_m5
    )

    buyers_improving = (
        data["buy_pressure"] > previous_buy
    )

    volume_improving = (
        data["volume_m5"] > previous_volume
    )

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    recovery = (
        previous_m5 <= 0
        and data["m5"] > 0
        and buyers_improving
    )

    if recovery:
        return True, "PULLBACK RECOVERY"

    # --------------------------------------------------------
    # CONTINUATION
    # --------------------------------------------------------

    continuation = (
        data["m5"] > 0
        and momentum_improving
        and (
            volume_improving
            or buyers_improving
        )
    )

    if continuation:
        return True, "MOMENTUM CONTINUATION"

    # --------------------------------------------------------
    # STRONG BUYING
    # --------------------------------------------------------

    strong_buying = (
        data["buy_pressure"] >= 65
        and data["m5"] >= 0
        and momentum_improving
    )

    if strong_buying:
        return True, "STRONG BUY PRESSURE"

    return False, "No confirmation"


# ============================================================
# WRITE TARGET
# ============================================================

def log_target(data, score, reason):

    try:

        with open(
            TARGETS_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                f"\n[{timestamp()}]\n"
            )

            f.write(
                f"Symbol: {data['symbol']}\n"
            )

            f.write(
                f"Name: {data['name']}\n"
            )

            f.write(
                f"Token ID: {data['address']}\n"
            )

            f.write(
                f"Pair ID: {data['pair_id']}\n"
            )

            f.write(
                f"Pair URL: {data['pair_url']}\n"
            )

            f.write(
                f"Price: {price(data['price'])}\n"
            )

            f.write(
                f"Score: {score}/100\n"
            )

            f.write(
                f"Reason: {reason}\n"
            )

            f.write(
                f"Liquidity: {money(data['liquidity'])}\n"
            )

            f.write(
                f"5M Volume: {money(data['volume_m5'])}\n"
            )

            f.write(
                f"5M Buys: {data['m5_buys']}\n"
            )

            f.write(
                f"5M Sells: {data['m5_sells']}\n"
            )

            f.write(
                f"Buy Pressure: {data['buy_pressure']:.2f}%\n"
            )

            f.write(
                f"5M Change: {data['m5']:.2f}%\n"
            )

            f.write(
                f"1H Change: {data['h1']:.2f}%\n"
            )

            f.write(
                "-" * 70 + "\n"
            )

    except Exception:
        pass


# ============================================================
# OPEN PAPER TRADE
# ============================================================

def open_trade(state, data, score, reason):

    if len(state["open_trades"]) >= MAX_OPEN_TRADES:
        return False

    address = data["address"]

    if address in state["open_trades"]:
        return False

    if state["balance"] < PAPER_TRADE_SIZE:
        return False

    entry_price = data["price"]

    if entry_price <= 0:
        return False

    trade = {

        "address": address,

        "symbol": data["symbol"],
        "name": data["name"],

        "token_id": data["address"],
        "pair_id": data["pair_id"],
        "pair_url": data["pair_url"],

        "entry_price": entry_price,
        "highest_price": entry_price,

        "stake": PAPER_TRADE_SIZE,

        "entry_time": timestamp(),
        "entry_timestamp": time.time(),

        "entry_score": score,
        "entry_reason": reason,

        "source": data["source"],

        "m5_buys": data["m5_buys"],
        "m5_sells": data["m5_sells"],
        "buy_pressure": data["buy_pressure"],

        "liquidity": data["liquidity"],
        "volume_m5": data["volume_m5"],

        "milestones": []
    }

    state["open_trades"][address] = trade

    state["balance"] -= PAPER_TRADE_SIZE

    state["total_entries"] += 1

    log_trade_entry(trade)

    return True


# ============================================================
# LOG ENTRY
# ============================================================

def log_trade_entry(trade):

    try:

        with open(
            TRADES_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n"
                + "=" * 80
                + "\n"
            )

            f.write(
                f"ENTRY [{trade['entry_time']}]\n"
            )

            f.write(
                f"Symbol: {trade['symbol']}\n"
            )

            f.write(
                f"Name: {trade['name']}\n"
            )

            f.write(
                f"Token ID: {trade['token_id']}\n"
            )

            f.write(
                f"Pair ID: {trade['pair_id']}\n"
            )

            f.write(
                f"Pair URL: {trade['pair_url']}\n"
            )

            f.write(
                f"Entry Price: {price(trade['entry_price'])}\n"
            )

            f.write(
                f"Stake: {money(trade['stake'])}\n"
            )

            f.write(
                f"Entry Score: {trade['entry_score']}/100\n"
            )

            f.write(
                f"Entry Reason: {trade['entry_reason']}\n"
            )

            f.write(
                f"5M Buys: {trade['m5_buys']}\n"
            )

            f.write(
                f"5M Sells: {trade['m5_sells']}\n"
            )

            f.write(
                f"Buy Pressure: {trade['buy_pressure']:.2f}%\n"
            )

            f.write(
                f"Liquidity: {money(trade['liquidity'])}\n"
            )

            f.write(
                f"5M Volume: {money(trade['volume_m5'])}\n"
            )

    except Exception:
        pass


# ============================================================
# MILESTONE
# ============================================================

def check_milestones(state, trade, multiple):

    milestones = [

        (2, "2X"),
        (5, "5X"),
        (10, "10X"),
        (50, "50X"),
        (100, "100X")

    ]

    for threshold, label in milestones:

        if multiple >= threshold:

            if label not in trade["milestones"]:

                trade["milestones"].append(
                    label
                )

                state["milestones"][label] += 1

                try:

                    with open(
                        TRADES_FILE,
                        "a",
                        encoding="utf-8"
                    ) as f:

                        f.write(
                            f"\n"
                            f"[{timestamp()}] "
                            f"MILESTONE {label}\n"
                            f"Token: {trade['symbol']}\n"
                            f"Token ID: {trade['token_id']}\n"
                            f"Pair ID: {trade['pair_id']}\n"
                            f"Price: {price(trade.get('current_price', 0))}\n"
                            f"Multiple: {multiple:.2f}X\n"
                            f"URL: {trade['pair_url']}\n"
                        )

                except Exception:
                    pass


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

    selected_trail = None

    for activation, trail in TRAILING_LEVELS:

        if gain >= activation:
            selected_trail = trail

    if selected_trail is None:
        return None

    return highest * (
        1 - selected_trail
    )


# ============================================================
# UPDATE TRADE
# ============================================================

def update_trade(state, trade, data):

    current_price = data["price"]

    if current_price <= 0:
        return None

    trade["current_price"] = current_price

    if current_price > trade["highest_price"]:

        trade["highest_price"] = current_price

    entry = trade["entry_price"]

    highest = trade["highest_price"]

    multiple = current_price / entry

    gain = multiple - 1

    trade["current_multiple"] = multiple

    trade["current_gain"] = gain

    trade["current_liquidity"] = data[
        "liquidity"
    ]

    trade["current_volume_m5"] = data[
        "volume_m5"
    ]

    trade["current_buy_pressure"] = data[
        "buy_pressure"
    ]

    check_milestones(
        state,
        trade,
        multiple
    )

    # --------------------------------------------------------
    # INITIAL STOP
    # --------------------------------------------------------

    if gain <= INITIAL_STOP:

        return (
            "INITIAL STOP"
        )

    # --------------------------------------------------------
    # TRAILING STOP
    # --------------------------------------------------------

    trailing_stop = get_trailing_stop(
        trade
    )

    if trailing_stop is not None:

        if current_price <= trailing_stop:

            return (
                "TRAILING STOP"
            )

    # --------------------------------------------------------
    # MAX HOLD
    # --------------------------------------------------------

    held_seconds = (
        time.time()
        - trade["entry_timestamp"]
    )

    held_hours = (
        held_seconds / 3600
    )

    if held_hours >= MAX_HOLD_HOURS:

        return (
            "MAX HOLD TIME"
        )

    return None


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(state, address, data, reason):

    trade = state["open_trades"].get(
        address
    )

    if not trade:
        return

    current_price = data["price"]

    entry_price = trade["entry_price"]

    if entry_price <= 0:
        return

    multiple = (
        current_price / entry_price
    )

    final_value = (
        trade["stake"]
        * multiple
    )

    pnl = (
        final_value
        - trade["stake"]
    )

    state["balance"] += final_value

    trade["exit_price"] = current_price
    trade["exit_time"] = timestamp()
    trade["exit_reason"] = reason
    trade["final_multiple"] = multiple
    trade["pnl"] = pnl
    trade["final_value"] = final_value

    held_seconds = (
        time.time()
        - trade["entry_timestamp"]
    )

    trade["holding_hours"] = (
        held_seconds / 3600
    )

    state["closed_trades"].append(
        trade
    )

    del state["open_trades"][address]

    state["total_exits"] += 1

    log_trade_exit(trade)


# ============================================================
# LOG EXIT
# ============================================================

def log_trade_exit(trade):

    try:

        with open(
            TRADES_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n"
                + "=" * 80
                + "\n"
            )

            f.write(
                f"EXIT [{trade['exit_time']}]\n"
            )

            f.write(
                f"Symbol: {trade['symbol']}\n"
            )

            f.write(
                f"Token ID: {trade['token_id']}\n"
            )

            f.write(
                f"Pair ID: {trade['pair_id']}\n"
            )

            f.write(
                f"Pair URL: {trade['pair_url']}\n"
            )

            f.write(
                f"Entry: {price(trade['entry_price'])}\n"
            )

            f.write(
                f"Highest: {price(trade['highest_price'])}\n"
            )

            f.write(
                f"Exit: {price(trade['exit_price'])}\n"
            )

            f.write(
                f"Multiple: {trade['final_multiple']:.2f}X\n"
            )

            f.write(
                f"P/L: {money(trade['pnl'])}\n"
            )

            f.write(
                f"Exit Reason: {trade['exit_reason']}\n"
            )

            f.write(
                f"Holding Hours: "
                f"{trade['holding_hours']:.2f}\n"
            )

            f.write(
                f"Milestones: "
                f"{', '.join(trade['milestones'])}\n"
            )

    except Exception:
        pass


# ============================================================
# UPDATE STATISTICS
# ============================================================

def update_statistics(state):

    balance = state["balance"]

    if balance > state["peak_balance"]:
        state["peak_balance"] = balance

    if state["peak_balance"] > 0:

        drawdown = (
            state["peak_balance"]
            - balance
        ) / state["peak_balance"]

        if drawdown > state["max_drawdown"]:
            state["max_drawdown"] = drawdown


def write_stats(state):

    closed = state["closed_trades"]

    wins = [
        x for x in closed
        if safe_float(x.get("pnl")) > 0
    ]

    losses = [
        x for x in closed
        if safe_float(x.get("pnl")) <= 0
    ]

    realized_pnl = sum(
        safe_float(x.get("pnl"))
        for x in closed
    )

    best = max(
        [safe_float(x.get("pnl")) for x in closed],
        default=0
    )

    worst = min(
        [safe_float(x.get("pnl")) for x in closed],
        default=0
    )

    if closed:
        win_rate = (
            len(wins) / len(closed)
        ) * 100
    else:
        win_rate = 0

    try:

        with open(
            STATS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ALVIN MEME GOD V6.1\n"
            )

            f.write(
                "=" * 60 + "\n\n"
            )

            f.write(
                f"Updated: {timestamp()}\n\n"
            )

            f.write(
                f"Balance: {money(state['balance'])}\n"
            )

            f.write(
                f"Open Trades: "
                f"{len(state['open_trades'])}\n"
            )

            f.write(
                f"Closed Trades: "
                f"{len(closed)}\n"
            )

            f.write(
                f"Wins: {len(wins)}\n"
            )

            f.write(
                f"Losses: {len(losses)}\n"
            )

            f.write(
                f"Win Rate: {win_rate:.2f}%\n"
            )

            f.write(
                f"Realized P/L: "
                f"{money(realized_pnl)}\n"
            )

            f.write(
                f"Best Trade: "
                f"{money(best)}\n"
            )

            f.write(
                f"Worst Trade: "
                f"{money(worst)}\n"
            )

            f.write(
                f"Peak Balance: "
                f"{money(state['peak_balance'])}\n"
            )

            f.write(
                f"Max Drawdown: "
                f"{pct(state['max_drawdown'])}\n"
            )

            f.write(
                f"Total Entries: "
                f"{state['total_entries']}\n"
            )

            f.write(
                f"Total Exits: "
                f"{state['total_exits']}\n\n"
            )

            f.write(
                "MILESTONES\n"
            )

            f.write(
                "-" * 40 + "\n"
            )

            for key in [
                "2X",
                "5X",
                "10X",
                "50X",
                "100X"
            ]:

                f.write(
                    f"{key}: "
                    f"{state['milestones'][key]}\n"
                )

            f.write(
                "\nSTRATEGY SETTINGS\n"
            )

            f.write(
                "-" * 40 + "\n"
            )

            f.write(
                f"Entry Score: {ENTRY_SCORE}\n"
            )

            f.write(
                f"Watch Score: {WATCH_SCORE}\n"
            )

            f.write(
                f"Min Liquidity: "
                f"{money(MIN_LIQUIDITY)}\n"
            )

            f.write(
                f"Min 5M Volume: "
                f"{money(MIN_VOLUME_5M)}\n"
            )

            f.write(
                f"Min Buy Pressure: "
                f"{MIN_BUY_PRESSURE}%\n"
            )

            f.write(
                f"Initial Stop: "
                f"{INITIAL_STOP * 100:.0f}%\n"
            )

            f.write(
                f"Max Hold: "
                f"{MAX_HOLD_HOURS} hours\n"
            )

    except Exception:
        pass


# ============================================================
# FORMAT MULTIPLE
# ============================================================

def multiple_text(multiple):

    if multiple >= 100:
        return f"{multiple:.1f}X 🚀🚀🚀"

    if multiple >= 50:
        return f"{multiple:.1f}X 🚀🚀"

    if multiple >= 10:
        return f"{multiple:.1f}X 🚀"

    if multiple >= 2:
        return f"{multiple:.2f}X"

    return f"{multiple:.2f}X"


# ============================================================
# LIVE TERMINAL
# ============================================================

def live_terminal(state, market, last_analysis):

    clear_terminal()

    closed = state["closed_trades"]

    wins = [
        x for x in closed
        if safe_float(x.get("pnl")) > 0
    ]

    losses = [
        x for x in closed
        if safe_float(x.get("pnl")) <= 0
    ]

    realized_pnl = sum(
        safe_float(x.get("pnl"))
        for x in closed
    )

    elapsed = time.time() - last_analysis

    next_scan = max(
        0,
        SCAN_INTERVAL - elapsed
    )

    print("=" * 100)

    print(
        f"🔥 {BOT_NAME}"
    )

    print(
        "📄 PAPER TRADING | "
        "⚡ TERMINAL 1s | "
        "🧠 STRATEGY 30s"
    )

    print("=" * 100)

    print(
        f"Balance: {money(state['balance'])}    "
        f"Open: {len(state['open_trades'])}/{MAX_OPEN_TRADES}    "
        f"Closed: {len(closed)}    "
        f"Wins: {len(wins)}    "
        f"Losses: {len(losses)}"
    )

    print(
        f"Realized P/L: {money(realized_pnl)}    "
        f"Peak: {money(state['peak_balance'])}    "
        f"Max DD: {pct(state['max_drawdown'])}"
    )

    print(
        f"Next strategy analysis: "
        f"{next_scan:.0f}s"
    )

    print()

    # ========================================================
    # OPEN TRADE TABLE
    # ========================================================

    print(
        "LIVE OPEN PAPER TRADES"
    )

    print("-" * 100)

    if not state["open_trades"]:

        print(
            "No open paper trades."
        )

    else:

        print(
            f"{'#':<3}"
            f"{'TOKEN':<15}"
            f"{'ENTRY':<15}"
            f"{'CURRENT':<15}"
            f"{'MULTIPLE':<12}"
            f"{'P/L':<15}"
        )

        print("-" * 100)

        for index, (
            address,
            trade
        ) in enumerate(
            state["open_trades"].items(),
            1
        ):

            data = market.get(
                address,
                {}
            )

            current_price = safe_float(
                data.get(
                    "price",
                    trade.get(
                        "current_price",
                        trade["entry_price"]
                    )
                )
            )

            entry_price = trade[
                "entry_price"
            ]

            if entry_price > 0:

                multiple = (
                    current_price
                    / entry_price
                )

            else:

                multiple = 0

            pnl = (
                trade["stake"]
                * (multiple - 1)
            )

            print(
                f"{index:<3}"
                f"{trade['symbol'][:14]:<15}"
                f"{price(entry_price):<15}"
                f"{price(current_price):<15}"
                f"{multiple_text(multiple):<12}"
                f"{money(pnl):<15}"
            )

    print()

    print(
        "=" * 100
    )

    # ========================================================
    # DETAILED OPEN TRADES
    # ========================================================

    if state["open_trades"]:

        print(
            "OPEN TRADE DETAILS"
        )

        print(
            "=" * 100
        )

        for index, (
            address,
            trade
        ) in enumerate(
            state["open_trades"].items(),
            1
        ):

            data = market.get(
                address,
                {}
            )

            current_price = safe_float(
                data.get(
                    "price",
                    trade.get(
                        "current_price",
                        trade["entry_price"]
                    )
                )
            )

            entry_price = trade[
                "entry_price"
            ]

            highest_price = max(
                trade.get(
                    "highest_price",
                    entry_price
                ),
                current_price
            )

            if entry_price > 0:

                multiple = (
                    current_price
                    / entry_price
                )

                max_multiple = (
                    highest_price
                    / entry_price
                )

            else:

                multiple = 0
                max_multiple = 0

            pnl = (
                trade["stake"]
                * (multiple - 1)
            )

            trailing = get_trailing_stop(
                {
                    **trade,
                    "highest_price":
                        highest_price
                }
            )

            print(
                f"\n[{index}] "
                f"{trade['symbol']} - "
                f"{trade['name']}"
            )

            print(
                f"Contract / Token ID:\n"
                f"{trade['token_id']}"
            )

            print(
                f"Pair ID:\n"
                f"{trade['pair_id']}"
            )

            print(
                f"Pair URL:\n"
                f"{trade['pair_url']}"
            )

            print()

            print(
                f"Entry Price:    "
                f"{price(entry_price)}"
            )

            print(
                f"Current Price:  "
                f"{price(current_price)}"
            )

            print(
                f"Highest Price:  "
                f"{price(highest_price)}"
            )

            print(
                f"Current Multiple:"
                f" {multiple_text(multiple)}"
            )

            print(
                f"Maximum Multiple:"
                f" {max_multiple:.2f}X"
            )

            print(
                f"Paper P/L:      "
                f"{money(pnl)}"
            )

            print()

            print(
                f"Entry Score:    "
                f"{trade['entry_score']}/100"
            )

            print(
                f"Entry Reason:   "
                f"{trade['entry_reason']}"
            )

            print()

            print(
                f"5M Buys:        "
                f"{data.get('m5_buys', trade.get('m5_buys', 0))}"
            )

            print(
                f"5M Sells:       "
                f"{data.get('m5_sells', trade.get('m5_sells', 0))}"
            )

            print(
                f"Buy Pressure:   "
                f"{data.get('buy_pressure', trade.get('buy_pressure', 0)):.2f}%"
            )

            print(
                f"Liquidity:      "
                f"{money(data.get('liquidity', trade.get('liquidity', 0)))}"
            )

            print(
                f"5M Volume:      "
                f"{money(data.get('volume_m5', trade.get('volume_m5', 0)))}"
            )

            print()

            if trailing is not None:

                print(
                    f"Trailing Stop:  "
                    f"{price(trailing)}"
                )

            else:

                print(
                    "Trailing Stop:  NOT ACTIVE"
                )

            print(
                f"Milestones:     "
                f"{', '.join(trade['milestones']) if trade['milestones'] else 'None'}"
            )

            print(
                "-" * 100
            )


# ============================================================
# MAIN STRATEGY ANALYSIS
# ============================================================

def strategy_cycle(state, market):

    print(
        f"[{timestamp()}] "
        "Running market analysis..."
    )

    discoveries = discover_tokens()

    unique_addresses = set()

    for item in discoveries:

        address = item.get(
            "address"
        )

        if address:
            unique_addresses.add(
                address
            )

    analyzed = 0

    for address in unique_addresses:

        pairs = get_pairs(
            address
        )

        if not pairs:
            continue

        # ----------------------------------------------------
        # Choose strongest pair by liquidity
        # ----------------------------------------------------

        valid_pairs = []

        for pair in pairs:

            normalized = normalize_pair(
                pair,
                "discovery"
            )

            if not normalized:
                continue

            if normalized["liquidity"] <= 0:
                continue

            valid_pairs.append(
                normalized
            )

        if not valid_pairs:
            continue

        valid_pairs.sort(
            key=lambda x: (
                x["liquidity"],
                x["volume_m5"]
            ),
            reverse=True
        )

        data = valid_pairs[0]

        token = data["address"]

        previous = state[
            "watchlist"
        ].get(token)

        score = score_token(
            data,
            previous
        )

        market[token] = data

        # ----------------------------------------------------
        # Store latest observation
        # ----------------------------------------------------

        state["watchlist"][token] = {
            "m5": data["m5"],
            "h1": data["h1"],
            "h6": data["h6"],
            "volume_m5": data["volume_m5"],
            "buy_pressure": data["buy_pressure"],
            "liquidity": data["liquidity"],
            "score": score,
            "last_price": data["price"],
            "timestamp": time.time()
        }

        # ----------------------------------------------------
        # Log quality targets
        # ----------------------------------------------------

        if score >= WATCH_SCORE:

            log_target(
                data,
                score,
                "WATCH / QUALITY CANDIDATE"
            )

        # ----------------------------------------------------
        # Existing trade update
        # ----------------------------------------------------

        if token in state["open_trades"]:

            trade = state[
                "open_trades"
            ][token]

            exit_reason = update_trade(
                state,
                trade,
                data
            )

            if exit_reason:

                close_trade(
                    state,
                    token,
                    data,
                    exit_reason
                )

            analyzed += 1

            continue

        # ----------------------------------------------------
        # New entry
        # ----------------------------------------------------

        signal, reason = entry_signal(
            data,
            previous,
            score
        )

        if signal:

            opened = open_trade(
                state,
                data,
                score,
                reason
            )

            if opened:

                print(
                    f"[{timestamp()}] "
                    f"ENTRY {data['symbol']} "
                    f"Score={score} "
                    f"Reason={reason}"
                )

        analyzed += 1

    # ========================================================
    # UPDATE ALL OPEN TRADES
    # ========================================================

    for address in list(
        state["open_trades"].keys()
    ):

        if address not in market:
            continue

        trade = state[
            "open_trades"
        ][address]

        data = market[address]

        exit_reason = update_trade(
            state,
            trade,
            data
        )

        if exit_reason:

            close_trade(
                state,
                address,
                data,
                exit_reason
            )

    update_statistics(
        state
    )

    write_stats(
        state
    )

    save_state(
        state
    )

    print(
        f"[{timestamp()}] "
        f"Analysis complete. "
        f"Tokens analyzed: {analyzed}"
    )


# ============================================================
# MAIN LOOP
# ============================================================

def main():

    initialize_files()

    state = load_state()

    market = {}

    last_analysis = 0

    print()
    print(
        "=" * 80
    )

    print(
        "🔥 ALVIN MEME GOD V6.1"
    )

    print(
        "Paper Trading Engine"
    )

    print(
        "Terminal refresh: 1 second"
    )

    print(
        "Strategy analysis: 30 seconds"
    )

    print(
        "No real trades are executed."
    )

    print(
        "=" * 80
    )

    time.sleep(2)

    while True:

        try:

            current_time = time.time()

            # =================================================
            # STRATEGY ONLY RUNS EVERY 30 SECONDS
            # =================================================

            if (
                current_time
                - last_analysis
                >= SCAN_INTERVAL
            ):

                strategy_cycle(
                    state,
                    market
                )

                last_analysis = time.time()

            # =================================================
            # TERMINAL REFRESHES EVERY SECOND
            # =================================================

            live_terminal(
                state,
                market,
                last_analysis
            )

            time.sleep(
                TERMINAL_REFRESH
            )

        except KeyboardInterrupt:

            print()
            print(
                "Stopping ALVIN MEME GOD..."
            )

            save_state(
                state
            )

            write_stats(
                state
            )

            print(
                "State saved."
            )

            break

        except Exception as e:

            print()
            print(
                "MAIN LOOP ERROR:",
                e
            )

            time.sleep(2)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
