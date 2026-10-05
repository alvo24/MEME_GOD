import os
import time
import json
import math
import requests
from datetime import datetime, timezone

# ============================================================
# ALVIN MEME GOD V6.1
# QUALITY ENTRY + RUNNER STRATEGY
# COLORED LIVE TERMINAL
# PAPER TRADING ONLY
# ============================================================

BOT_NAME = "ALVIN MEME GOD V6.1"

BASE_URL = "https://api.dexscreener.com"

# ============================================================
# TIMING
# ============================================================

SCAN_INTERVAL = 5
TERMINAL_REFRESH = 1

# ============================================================
# PAPER ACCOUNT
# ============================================================

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# ============================================================
# ENTRY STRATEGY
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

TRAILING_LEVELS = [
    (0.15, 0.08),
    (0.30, 0.12),
    (1.00, 0.18),
    (5.00, 0.22),
    (10.00, 0.25),
    (50.00, 0.30),
]

# ============================================================
# FILES
# ============================================================

TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_V6_1_STATE.json"

# ============================================================
# ANSI COLORS
# ============================================================

RESET = "\033[0m"

BOLD = "\033[1m"

BLACK = "\033[30m"
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


def color(text, colour):
    return f"{colour}{text}{RESET}"


def bold(text):
    return f"{BOLD}{text}{RESET}"


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD/6.1"
})


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def now_utc():
    return datetime.now(timezone.utc)


def timestamp():
    return now_utc().strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if math.isnan(value):
            return default

        if math.isinf(value):
            return default

        return value

    except Exception:

        return default


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


def pct(value):

    return f"{safe_float(value) * 100:.2f}%"


def clear_terminal():

    print("\033[2J\033[H", end="")


# ============================================================
# FILE INITIALIZATION
# ============================================================

def initialize_files():

    if not os.path.exists(TARGETS_FILE):

        with open(
            TARGETS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ALVIN MEME GOD V6.1 TARGET LOG\n"
                "========================================\n\n"
            )

    if not os.path.exists(TRADES_FILE):

        with open(
            TRADES_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ALVIN MEME GOD V6.1 TRADE LOG\n"
                "========================================\n\n"
            )

    if not os.path.exists(STATS_FILE):

        with open(
            STATS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ALVIN MEME GOD V6.1 STATISTICS\n"
                "========================================\n\n"
            )


# ============================================================
# DEFAULT STATE
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


# ============================================================
# REPAIR STATE
# ============================================================

def repair_state(state):

    base = default_state()

    if not isinstance(state, dict):

        return base

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    for key, value in base.items():

        if key not in state:
            state[key] = value

    # --------------------------------------------------------
    # Correct container types
    # --------------------------------------------------------

    if not isinstance(
        state.get("open_trades"),
        dict
    ):

        state["open_trades"] = {}

    if not isinstance(
        state.get("watchlist"),
        dict
    ):

        state["watchlist"] = {}

    if not isinstance(
        state.get("closed_trades"),
        list
    ):

        state["closed_trades"] = []

    if not isinstance(
        state.get("seen_tokens"),
        list
    ):

        state["seen_tokens"] = []

    if not isinstance(
        state.get("milestones"),
        dict
    ):

        state["milestones"] = {}

    # --------------------------------------------------------
    # Milestones
    # --------------------------------------------------------

    for milestone in [
        "2X",
        "5X",
        "10X",
        "50X",
        "100X"
    ]:

        if milestone not in state["milestones"]:

            state["milestones"][milestone] = 0

        state["milestones"][milestone] = int(
            safe_float(
                state["milestones"][milestone],
                0
            )
        )

    # --------------------------------------------------------
    # Numbers
    # --------------------------------------------------------

    state["balance"] = safe_float(
        state.get("balance"),
        STARTING_BALANCE
    )

    state["peak_balance"] = safe_float(
        state.get("peak_balance"),
        state["balance"]
    )

    state["max_drawdown"] = safe_float(
        state.get("max_drawdown"),
        0
    )

    state["total_entries"] = int(
        safe_float(
            state.get("total_entries"),
            0
        )
    )

    state["total_exits"] = int(
        safe_float(
            state.get("total_exits"),
            0
        )
    )

    # --------------------------------------------------------
    # Repair individual watchlist entries
    # --------------------------------------------------------

    repaired_watchlist = {}

    for token, item in state[
        "watchlist"
    ].items():

        if not isinstance(item, dict):
            continue

        repaired_watchlist[str(token)] = item

    state["watchlist"] = repaired_watchlist

    # --------------------------------------------------------
    # Repair open trades
    # --------------------------------------------------------

    repaired_trades = {}

    for token, trade in state[
        "open_trades"
    ].items():

        if not isinstance(trade, dict):
            continue

        token = str(token)

        if "address" not in trade:
            trade["address"] = token

        if "token_id" not in trade:
            trade["token_id"] = token

        if "milestones" not in trade:
            trade["milestones"] = []

        if not isinstance(
            trade["milestones"],
            list
        ):
            trade["milestones"] = []

        repaired_trades[token] = trade

    state["open_trades"] = repaired_trades

    return state


# ============================================================
# LOAD STATE
# ============================================================

def load_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return default_state()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            state = json.load(f)

        return repair_state(
            state
        )

    except Exception as e:

        print(
            color(
                f"State repair error: {e}",
                BRIGHT_YELLOW
            )
        )

        print(
            color(
                "Starting with clean paper state.",
                BRIGHT_YELLOW
            )
        )

        return default_state()


# ============================================================
# SAVE STATE
# ============================================================

def save_state(state):

    try:

        temp = (
            STATE_FILE
            + ".tmp"
        )

        with open(
            temp,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                indent=2
            )

        os.replace(
            temp,
            STATE_FILE
        )

    except Exception as e:

        print(
            color(
                f"State save error: {e}",
                BRIGHT_RED
            )
        )


# ============================================================
# API REQUEST
# ============================================================

def api_get(endpoint):

    url = BASE_URL + endpoint

    try:

        response = session.get(
            url,
            timeout=15
        )

        if response.status_code == 429:

            return None

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

        data = api_get(
            endpoint
        )

        if not data:
            continue

        if isinstance(data, list):

            items = data

        elif isinstance(data, dict):

            items = data.get(
                "pairs",
                data.get(
                    "tokens",
                    []
                )
            )

        else:

            continue

        if not isinstance(
            items,
            list
        ):

            continue

        for item in items:

            if not isinstance(
                item,
                dict
            ):

                continue

            address = (
                item.get(
                    "tokenAddress"
                )
                or item.get(
                    "address"
                )
            )

            if not address:
                continue

            candidates[address] = {
                "address": address,
                "source": endpoint
            }

    return list(
        candidates.values()
    )


# ============================================================
# PAIRS
# ============================================================

def get_pairs(
    token_address
):

    endpoint = (
        "/token-pairs/v1/solana/"
        + token_address
    )

    data = api_get(
        endpoint
    )

    if not data:
        return []

    if isinstance(
        data,
        dict
    ):

        pairs = data.get(
            "pairs",
            []
        )

    else:

        pairs = data

    if not isinstance(
        pairs,
        list
    ):

        return []

    return pairs


# ============================================================
# NORMALIZE PAIR
# ============================================================

def normalize_pair(
    pair,
    source="unknown"
):

    if not isinstance(
        pair,
        dict
    ):

        return None

    base = pair.get(
        "baseToken"
    ) or {}

    address = base.get(
        "address"
    )

    if not address:
        return None

    symbol = (
        base.get("symbol")
        or "UNKNOWN"
    )

    name = (
        base.get("name")
        or symbol
    )

    pair_id = (
        pair.get("pairAddress")
        or ""
    )

    pair_url = pair.get(
        "url"
    )

    if not pair_url and pair_id:

        pair_url = (
            "https://dexscreener.com/"
            f"solana/{pair_id}"
        )

    liquidity = (
        pair.get("liquidity")
        or {}
    )

    volume = (
        pair.get("volume")
        or {}
    )

    txns = (
        pair.get("txns")
        or {}
    )

    m5 = (
        txns.get("m5")
        or {}
    )

    h1 = (
        txns.get("h1")
        or {}
    )

    m5_buys = int(
        safe_float(
            m5.get("buys")
        )
    )

    m5_sells = int(
        safe_float(
            m5.get("sells")
        )
    )

    h1_buys = int(
        safe_float(
            h1.get("buys")
        )
    )

    h1_sells = int(
        safe_float(
            h1.get("sells")
        )
    )

    m5_total = (
        m5_buys
        + m5_sells
    )

    h1_total = (
        h1_buys
        + h1_sells
    )

    if m5_total > 0:

        buy_pressure = (
            m5_buys
            / m5_total
        ) * 100

    else:

        buy_pressure = 0

    price_usd = safe_float(
        pair.get(
            "priceUsd"
        )
    )

    market_cap = safe_float(
        pair.get(
            "marketCap"
        )
    )

    fdv = safe_float(
        pair.get(
            "fdv"
        )
    )

    liquidity_usd = safe_float(
        liquidity.get(
            "usd"
        )
    )

    volume_m5 = safe_float(
        volume.get(
            "m5"
        )
    )

    volume_h1 = safe_float(
        volume.get(
            "h1"
        )
    )

    price_change = (
        pair.get(
            "priceChange"
        )
        or {}
    )

    m5_change = safe_float(
        price_change.get(
            "m5"
        )
    )

    h1_change = safe_float(
        price_change.get(
            "h1"
        )
    )

    h6_change = safe_float(
        price_change.get(
            "h6"
        )
    )

    h24_change = safe_float(
        price_change.get(
            "h24"
        )
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

        "source": source
    }


# ============================================================
# SCORE
# ============================================================

def score_token(
    data,
    previous=None
):

    score = 0

    liquidity = data[
        "liquidity"
    ]

    volume_m5 = data[
        "volume_m5"
    ]

    volume_h1 = data[
        "volume_h1"
    ]

    buy_pressure = data[
        "buy_pressure"
    ]

    m5 = data["m5"]
    h1 = data["h1"]
    h6 = data["h6"]

    market_cap = data[
        "market_cap"
    ]

    # Liquidity

    if liquidity >= 25000:
        score += 15

    elif liquidity >= 15000:
        score += 10

    elif liquidity >= 7500:
        score += 5

    # 5M volume

    if volume_m5 >= 50000:
        score += 20

    elif volume_m5 >= 20000:
        score += 16

    elif volume_m5 >= 10000:
        score += 12

    elif volume_m5 >= 5000:
        score += 8

    # 1H volume

    if volume_h1 >= 250000:
        score += 10

    elif volume_h1 >= 100000:
        score += 8

    elif volume_h1 >= 50000:
        score += 6

    elif volume_h1 >= 20000:
        score += 4

    # Buy pressure

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

    # Momentum

    if m5 >= 10:
        score += 15

    elif m5 >= 5:
        score += 12

    elif m5 >= 2:
        score += 9

    elif m5 > 0:
        score += 5

    # 1H trend

    if h1 >= 30:
        score += 12

    elif h1 >= 15:
        score += 10

    elif h1 >= 5:
        score += 7

    elif h1 > 0:
        score += 4

    # 6H trend

    if h6 >= 50:
        score += 6

    elif h6 >= 20:
        score += 4

    elif h6 > 0:
        score += 2

    # Liquidity / MC

    if market_cap > 0:

        ratio = (
            liquidity
            / market_cap
        )

        if ratio >= 0.20:
            score += 6

        elif ratio >= 0.10:
            score += 4

        elif ratio >= 0.05:
            score += 2

    # Improvement

    if isinstance(
        previous,
        dict
    ):

        if data["m5"] > safe_float(
            previous.get("m5")
        ):

            score += 6

        if data["buy_pressure"] > safe_float(
            previous.get(
                "buy_pressure"
            )
        ):

            score += 5

        if data["volume_m5"] > safe_float(
            previous.get(
                "volume_m5"
            )
        ):

            score += 5

    return max(
        0,
        min(
            100,
            score
        )
    )


# ============================================================
# ENTRY SIGNAL
# ============================================================

def entry_signal(
    data,
    previous,
    score
):

    if not isinstance(
        previous,
        dict
    ):

        return (
            False,
            "Waiting for confirmation"
        )

    if data[
        "liquidity"
    ] < MIN_LIQUIDITY:

        return (
            False,
            "Liquidity too low"
        )

    if data[
        "volume_m5"
    ] < MIN_VOLUME_5M:

        return (
            False,
            "5M volume too low"
        )

    if data[
        "buy_pressure"
    ] < MIN_BUY_PRESSURE:

        return (
            False,
            "Buy pressure too low"
        )

    if data["h1"] <= 0:

        return (
            False,
            "1H trend not positive"
        )

    if score < ENTRY_SCORE:

        return (
            False,
            "Score below threshold"
        )

    if data["m5"] > MAX_ENTRY_SPIKE_5M:

        return (
            False,
            "5M spike too large"
        )

    previous_m5 = safe_float(
        previous.get("m5")
    )

    previous_buy = safe_float(
        previous.get(
            "buy_pressure"
        )
    )

    previous_volume = safe_float(
        previous.get(
            "volume_m5"
        )
    )

    momentum_improving = (
        data["m5"]
        > previous_m5
    )

    buyers_improving = (
        data["buy_pressure"]
        > previous_buy
    )

    volume_improving = (
        data["volume_m5"]
        > previous_volume
    )

    # Recovery

    recovery = (
        previous_m5 <= 0
        and data["m5"] > 0
        and buyers_improving
    )

    if recovery:

        return (
            True,
            "PULLBACK RECOVERY"
        )

    # Continuation

    continuation = (
        data["m5"] > 0
        and momentum_improving
        and (
            volume_improving
            or buyers_improving
        )
    )

    if continuation:

        return (
            True,
            "MOMENTUM CONTINUATION"
        )

    # Strong buying

    strong_buying = (
        data[
            "buy_pressure"
        ] >= 65

        and data["m5"] >= 0

        and momentum_improving
    )

    if strong_buying:

        return (
            True,
            "STRONG BUY PRESSURE"
        )

    return (
        False,
        "No confirmation"
    )


# ============================================================
# LOG TARGET
# ============================================================

def log_target(
    data,
    score,
    reason
):

    try:

        with open(
            TARGETS_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n"
                + "=" * 80
                + "\n"
            )

            f.write(
                f"[{timestamp()}]\n"
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
                f"Liquidity: "
                f"{money(data['liquidity'])}\n"
            )

            f.write(
                f"5M Volume: "
                f"{money(data['volume_m5'])}\n"
            )

            f.write(
                f"5M Buys: "
                f"{data['m5_buys']}\n"
            )

            f.write(
                f"5M Sells: "
                f"{data['m5_sells']}\n"
            )

            f.write(
                f"Buy Pressure: "
                f"{data['buy_pressure']:.2f}%\n"
            )

    except Exception:
        pass


# ============================================================
# OPEN TRADE
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

    address = data[
        "address"
    ]

    if address in state[
        "open_trades"
    ]:

        return False

    if state[
        "balance"
    ] < PAPER_TRADE_SIZE:

        return False

    entry_price = data[
        "price"
    ]

    if entry_price <= 0:

        return False

    trade = {

        "address": address,

        "symbol": data[
            "symbol"
        ],

        "name": data[
            "name"
        ],

        "token_id": address,

        "pair_id": data[
            "pair_id"
        ],

        "pair_url": data[
            "pair_url"
        ],

        "entry_price":
            entry_price,

        "highest_price":
            entry_price,

        "stake":
            PAPER_TRADE_SIZE,

        "entry_time":
            timestamp(),

        "entry_timestamp":
            time.time(),

        "entry_score":
            score,

        "entry_reason":
            reason,

        "source":
            data["source"],

        "m5_buys":
            data["m5_buys"],

        "m5_sells":
            data["m5_sells"],

        "buy_pressure":
            data["buy_pressure"],

        "liquidity":
            data["liquidity"],

        "volume_m5":
            data["volume_m5"],

        "milestones": []
    }

    state[
        "open_trades"
    ][address] = trade

    state[
        "balance"
    ] -= PAPER_TRADE_SIZE

    state[
        "total_entries"
    ] += 1

    log_trade_entry(
        trade
    )

    return True


# ============================================================
# ENTRY LOG
# ============================================================

def log_trade_entry(
    trade
):

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
                f"Token ID: {trade['token_id']}\n"
            )

            f.write(
                f"Pair ID: {trade['pair_id']}\n"
            )

            f.write(
                f"Pair URL: {trade['pair_url']}\n"
            )

            f.write(
                f"Entry Price: "
                f"{price(trade['entry_price'])}\n"
            )

            f.write(
                f"Stake: "
                f"{money(trade['stake'])}\n"
            )

            f.write(
                f"Entry Score: "
                f"{trade['entry_score']}/100\n"
            )

            f.write(
                f"Entry Reason: "
                f"{trade['entry_reason']}\n"
            )

            f.write(
                f"5M Buys: "
                f"{trade['m5_buys']}\n"
            )

            f.write(
                f"5M Sells: "
                f"{trade['m5_sells']}\n"
            )

            f.write(
                f"Buy Pressure: "
                f"{trade['buy_pressure']:.2f}%\n"
            )

    except Exception:
        pass


# ============================================================
# MILESTONES
# ============================================================

def check_milestones(
    state,
    trade,
    multiple
):

    levels = [
        (2, "2X"),
        (5, "5X"),
        (10, "10X"),
        (50, "50X"),
        (100, "100X")
    ]

    for threshold, label in levels:

        if multiple < threshold:
            continue

        if label in trade[
            "milestones"
        ]:

            continue

        trade[
            "milestones"
        ].append(label)

        state[
            "milestones"
        ][label] += 1

        try:

            with open(
                TRADES_FILE,
                "a",
                encoding="utf-8"
            ) as f:

                f.write(
                    "\n"
                    + "🚀 MILESTONE "
                    + label
                    + "\n"
                )

                f.write(
                    f"Time: {timestamp()}\n"
                )

                f.write(
                    f"Token: {trade['symbol']}\n"
                )

                f.write(
                    f"Token ID: "
                    f"{trade['token_id']}\n"
                )

                f.write(
                    f"Pair ID: "
                    f"{trade['pair_id']}\n"
                )

                f.write(
                    f"Multiple: "
                    f"{multiple:.2f}X\n"
                )

        except Exception:
            pass


# ============================================================
# TRAILING STOP
# ============================================================

def get_trailing_stop(
    trade
):

    entry = safe_float(
        trade.get(
            "entry_price"
        )
    )

    highest = safe_float(
        trade.get(
            "highest_price"
        )
    )

    if entry <= 0:
        return None

    gain = (
        highest / entry
    ) - 1

    selected = None

    for activation, trail in TRAILING_LEVELS:

        if gain >= activation:
            selected = trail

    if selected is None:
        return None

    return highest * (
        1 - selected
    )


# ============================================================
# UPDATE TRADE
# ============================================================

def update_trade(
    state,
    trade,
    data
):

    current_price = safe_float(
        data.get(
            "price"
        )
    )

    if current_price <= 0:
        return None

    trade[
        "current_price"
    ] = current_price

    if current_price > safe_float(
        trade.get(
            "highest_price"
        )
    ):

        trade[
            "highest_price"
        ] = current_price

    entry = safe_float(
        trade.get(
            "entry_price"
        )
    )

    if entry <= 0:
        return None

    multiple = (
        current_price
        / entry
    )

    gain = multiple - 1

    trade[
        "current_multiple"
    ] = multiple

    trade[
        "current_gain"
    ] = gain

    check_milestones(
        state,
        trade,
        multiple
    )

    # Initial stop

    if gain <= INITIAL_STOP:

        return "INITIAL STOP"

    # Trailing stop

    trailing = get_trailing_stop(
        trade
    )

    if (
        trailing is not None
        and current_price <= trailing
    ):

        return "TRAILING STOP"

    # Maximum hold

    held_seconds = (
        time.time()
        - safe_float(
            trade.get(
                "entry_timestamp"
            ),
            time.time()
        )
    )

    if (
        held_seconds / 3600
        >= MAX_HOLD_HOURS
    ):

        return "MAX HOLD TIME"

    return None


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(
    state,
    address,
    data,
    reason
):

    trade = state[
        "open_trades"
    ].get(address)

    if not trade:
        return

    current_price = safe_float(
        data.get(
            "price"
        )
    )

    entry_price = safe_float(
        trade.get(
            "entry_price"
        )
    )

    if (
        current_price <= 0
        or entry_price <= 0
    ):

        return

    multiple = (
        current_price
        / entry_price
    )

    final_value = (
        trade["stake"]
        * multiple
    )

    pnl = (
        final_value
        - trade["stake"]
    )

    state[
        "balance"
    ] += final_value

    trade[
        "exit_price"
    ] = current_price

    trade[
        "exit_time"
    ] = timestamp()

    trade[
        "exit_reason"
    ] = reason

    trade[
        "final_multiple"
    ] = multiple

    trade[
        "pnl"
    ] = pnl

    trade[
        "final_value"
    ] = final_value

    held_seconds = (
        time.time()
        - safe_float(
            trade.get(
                "entry_timestamp"
            ),
            time.time()
        )
    )

    trade[
        "holding_hours"
    ] = held_seconds / 3600

    state[
        "closed_trades"
    ].append(
        trade
    )

    del state[
        "open_trades"
    ][address]

    state[
        "total_exits"
    ] += 1

    log_trade_exit(
        trade
    )


# ============================================================
# EXIT LOG
# ============================================================

def log_trade_exit(
    trade
):

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
                f"Symbol: "
                f"{trade['symbol']}\n"
            )

            f.write(
                f"Token ID: "
                f"{trade['token_id']}\n"
            )

            f.write(
                f"Pair ID: "
                f"{trade['pair_id']}\n"
            )

            f.write(
                f"Pair URL: "
                f"{trade['pair_url']}\n"
            )

            f.write(
                f"Entry: "
                f"{price(trade['entry_price'])}\n"
            )

            f.write(
                f"Highest: "
                f"{price(trade['highest_price'])}\n"
            )

            f.write(
                f"Exit: "
                f"{price(trade['exit_price'])}\n"
            )

            f.write(
                f"Multiple: "
                f"{trade['final_multiple']:.2f}X\n"
            )

            f.write(
                f"P/L: "
                f"{money(trade['pnl'])}\n"
            )

            f.write(
                f"Exit Reason: "
                f"{trade['exit_reason']}\n"
            )

    except Exception:
        pass


# ============================================================
# STATISTICS
# ============================================================

def update_statistics(
    state
):

    balance = safe_float(
        state["balance"]
    )

    if balance > safe_float(
        state["peak_balance"]
    ):

        state[
            "peak_balance"
        ] = balance

    peak = safe_float(
        state["peak_balance"]
    )

    if peak > 0:

        drawdown = (
            peak - balance
        ) / peak

        if drawdown > safe_float(
            state["max_drawdown"]
        ):

            state[
                "max_drawdown"
            ] = drawdown


def write_stats(
    state
):

    closed = state[
        "closed_trades"
    ]

    wins = [
        x for x in closed
        if safe_float(
            x.get("pnl")
        ) > 0
    ]

    losses = [
        x for x in closed
        if safe_float(
            x.get("pnl")
        ) <= 0
    ]

    realized = sum(
        safe_float(
            x.get("pnl")
        )
        for x in closed
    )

    win_rate = (
        len(wins)
        / len(closed)
        * 100
        if closed
        else 0
    )

    best = max(
        [
            safe_float(
                x.get("pnl")
            )
            for x in closed
        ],
        default=0
    )

    worst = min(
        [
            safe_float(
                x.get("pnl")
            )
            for x in closed
        ],
        default=0
    )

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
                "=" * 60
                + "\n"
            )

            f.write(
                f"Updated: {timestamp()}\n\n"
            )

            f.write(
                f"Balance: "
                f"{money(state['balance'])}\n"
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
                f"Wins: "
                f"{len(wins)}\n"
            )

            f.write(
                f"Losses: "
                f"{len(losses)}\n"
            )

            f.write(
                f"Win Rate: "
                f"{win_rate:.2f}%\n"
            )

            f.write(
                f"Realized P/L: "
                f"{money(realized)}\n"
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
                f"Max Drawdown: "
                f"{pct(state['max_drawdown'])}\n"
            )

            f.write(
                "\nMILESTONES\n"
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

    except Exception:
        pass


# ============================================================
# MULTIPLE DISPLAY
# ============================================================

def multiple_text(
    multiple
):

    multiple = safe_float(
        multiple
    )

    if multiple >= 100:

        return color(
            f"{multiple:.1f}X 🚀🚀🚀",
            BRIGHT_MAGENTA
        )

    if multiple >= 50:

        return color(
            f"{multiple:.1f}X 🚀🚀",
            BRIGHT_MAGENTA
        )

    if multiple >= 10:

        return color(
            f"{multiple:.1f}X 🚀",
            BRIGHT_GREEN
        )

    if multiple >= 2:

        return color(
            f"{multiple:.2f}X",
            GREEN
        )

    if multiple >= 1:

        return color(
            f"{multiple:.2f}X",
            BRIGHT_GREEN
        )

    return color(
        f"{multiple:.2f}X",
        BRIGHT_RED
    )


# ============================================================
# P/L DISPLAY
# ============================================================

def pnl_text(
    value
):

    value = safe_float(
        value
    )

    if value > 0:

        return color(
            money(value),
            BRIGHT_GREEN
        )

    if value < 0:

        return color(
            money(value),
            BRIGHT_RED
        )

    return color(
        money(value),
        WHITE
    )


# ============================================================
# LIVE TERMINAL
# ============================================================

def live_terminal(
    state,
    market,
    last_analysis
):

    clear_terminal()

    closed = state[
        "closed_trades"
    ]

    wins = [
        x for x in closed
        if safe_float(
            x.get("pnl")
        ) > 0
    ]

    losses = [
        x for x in closed
        if safe_float(
            x.get("pnl")
        ) <= 0
    ]

    realized = sum(
        safe_float(
            x.get("pnl")
        )
        for x in closed
    )

    elapsed = (
        time.time()
        - last_analysis
    )

    next_scan = max(
        0,
        SCAN_INTERVAL
        - elapsed
    )

    # ========================================================
    # HEADER
    # ========================================================

    print(
        color(
            "=" * 105,
            BRIGHT_CYAN
        )
    )

    print(
        color(
            "🔥 ALVIN MEME GOD V6.1",
            BRIGHT_MAGENTA
        )
    )

    print(
        color(
            "PAPER TRADING ENGINE",
            BRIGHT_WHITE
        )
    )

    print(
        color(
            "⚡ TERMINAL: 1 SECOND    "
            "🧠 STRATEGY: 30 SECONDS    "
            "📄 PAPER MODE ONLY",
            BRIGHT_CYAN
        )
    )

    print(
        color(
            "=" * 105,
            BRIGHT_CYAN
        )
    )

    # ========================================================
    # ACCOUNT
    # ========================================================

    print(
        f"💰 Balance: "
        f"{color(money(state['balance']), BRIGHT_GREEN)}"
        f"    "
        f"📂 Open: "
        f"{color(str(len(state['open_trades'])) + '/' + str(MAX_OPEN_TRADES), BRIGHT_YELLOW)}"
        f"    "
        f"📊 Closed: "
        f"{color(str(len(closed)), BRIGHT_WHITE)}"
    )

    print(
        f"🟢 Wins: "
        f"{color(str(len(wins)), BRIGHT_GREEN)}"
        f"    "
        f"🔴 Losses: "
        f"{color(str(len(losses)), BRIGHT_RED)}"
        f"    "
        f"💵 Realized P/L: "
        f"{pnl_text(realized)}"
    )

    print(
        f"⏱ Next analysis: "
        f"{color(f'{next_scan:.0f}s', BRIGHT_YELLOW)}"
    )

    print()

    # ========================================================
    # OPEN TRADES
    # ========================================================

    print(
        color(
            "📡 LIVE OPEN PAPER TRADES",
            BRIGHT_CYAN
        )
    )

    print(
        color(
            "-" * 105,
            CYAN
        )
    )

    if not state[
        "open_trades"
    ]:

        print(
            color(
                "No open paper trades.",
                YELLOW
            )
        )

    else:

        print(
            f"{'#':<3}"
            f"{'TOKEN':<15}"
            f"{'ENTRY':<15}"
            f"{'CURRENT':<15}"
            f"{'MULTIPLE':<22}"
            f"{'P/L':<16}"
        )

        print(
            color(
                "-" * 105,
                CYAN
            )
        )

        for index, (
            address,
            trade
        ) in enumerate(
            state[
                "open_trades"
            ].items(),
            1
        ):

            data = market.get(
                address,
                {}
            )

            current = safe_float(
                data.get(
                    "price",
                    trade.get(
                        "current_price",
                        trade[
                            "entry_price"
                        ]
                    )
                )
            )

            entry = safe_float(
                trade[
                    "entry_price"
                ]
            )

            multiple = (
                current / entry
                if entry > 0
                else 0
            )

            pnl = (
                trade["stake"]
                * (multiple - 1)
            )

            token_display = (
                trade[
                    "symbol"
                ][:14]
            )

            print(
                f"{index:<3}"
                f"{token_display:<15}"
                f"{price(entry):<15}"
                f"{price(current):<15}",
                end=""
            )

            print(
                f"{multiple_text(multiple):<30}",
                end=""
            )

            print(
                pnl_text(pnl)
            )

    print()

    # ========================================================
    # DETAILS
    # ========================================================

    if state[
        "open_trades"
    ]:

        print(
            color(
                "🔎 OPEN TRADE DETAILS",
                BRIGHT_MAGENTA
            )
        )

        print(
            color(
                "=" * 105,
                MAGENTA
            )
        )

        for index, (
            address,
            trade
        ) in enumerate(
            state[
                "open_trades"
            ].items(),
            1
        ):

            data = market.get(
                address,
                {}
            )

            current = safe_float(
                data.get(
                    "price",
                    trade.get(
                        "current_price",
                        trade[
                            "entry_price"
                        ]
                    )
                )
            )

            entry = safe_float(
                trade[
                    "entry_price"
                ]
            )

            highest = max(
                safe_float(
                    trade.get(
                        "highest_price",
                        entry
                    )
                ),
                current
            )

            multiple = (
                current / entry
                if entry > 0
                else 0
            )

            max_multiple = (
                highest / entry
                if entry > 0
                else 0
            )

            pnl = (
                trade["stake"]
                * (multiple - 1)
            )

            trailing_trade = dict(
                trade
            )

            trailing_trade[
                "highest_price"
            ] = highest

            trailing = get_trailing_stop(
                trailing_trade
            )

            print(
                color(
                    f"[{index}] "
                    f"{trade['symbol']} "
                    f"- {trade['name']}",
                    BRIGHT_WHITE
                )
            )

            print()

            print(
                color(
                    "CONTRACT / TOKEN ID",
                    BRIGHT_CYAN
                )
            )

            print(
                trade[
                    "token_id"
                ]
            )

            print()

            print(
                color(
                    "PAIR ID",
                    BRIGHT_CYAN
                )
            )

            print(
                trade[
                    "pair_id"
                ]
            )

            print()

            print(
                color(
                    "PAIR URL",
                    BRIGHT_CYAN
                )
            )

            print(
                trade[
                    "pair_url"
                ]
            )

            print()

            print(
                f"Entry Price:    "
                f"{color(price(entry), WHITE)}"
            )

            print(
                f"Current Price:  "
                f"{color(price(current), BRIGHT_CYAN)}"
            )

            print(
                f"Highest Price:  "
                f"{color(price(highest), BRIGHT_GREEN)}"
            )

            print(
                f"Current Multiple: "
                f"{multiple_text(multiple)}"
            )

            print(
                f"Maximum Multiple: "
                f"{multiple_text(max_multiple)}"
            )

            print(
                f"Paper P/L:      "
                f"{pnl_text(pnl)}"
            )

            print()

            score_colour = (
                BRIGHT_GREEN
                if trade["entry_score"]
                >= ENTRY_SCORE
                else YELLOW
            )

            print(
                f"Entry Score:    "
                f"{color(str(trade['entry_score']) + '/100', score_colour)}"
            )

            print(
                f"Entry Reason:   "
                f"{color(trade['entry_reason'], BRIGHT_YELLOW)}"
            )

            print()

            buys = data.get(
                "m5_buys",
                trade.get(
                    "m5_buys",
                    0
                )
            )

            sells = data.get(
                "m5_sells",
                trade.get(
                    "m5_sells",
                    0
                )
            )

            pressure = safe_float(
                data.get(
                    "buy_pressure",
                    trade.get(
                        "buy_pressure",
                        0
                    )
                )
            )

            liquidity = safe_float(
                data.get(
                    "liquidity",
                    trade.get(
                        "liquidity",
                        0
                    )
                )
            )

            volume = safe_float(
                data.get(
                    "volume_m5",
                    trade.get(
                        "volume_m5",
                        0
                    )
                )
            )

            print(
                f"5M Buys:        "
                f"{color(str(buys), BRIGHT_GREEN)}"
            )

            print(
                f"5M Sells:       "
                f"{color(str(sells), BRIGHT_RED)}"
            )

            pressure_colour = (
                BRIGHT_GREEN
                if pressure >= 60
                else YELLOW
            )

            print(
                f"Buy Pressure:   "
                f"{color(f'{pressure:.2f}%', pressure_colour)}"
            )

            print(
                f"Liquidity:      "
                f"{color(money(liquidity), BRIGHT_CYAN)}"
            )

            print(
                f"5M Volume:      "
                f"{color(money(volume), BRIGHT_CYAN)}"
            )

            print()

            if trailing is not None:

                print(
                    f"Trailing Stop:  "
                    f"{color(price(trailing), BRIGHT_YELLOW)}"
                )

            else:

                print(
                    f"Trailing Stop:  "
                    f"{color('NOT ACTIVE', YELLOW)}"
                )

            milestones = trade.get(
                "milestones",
                []
            )

            if milestones:

                print(
                    "Milestones:     "
                    + color(
                        ", ".join(
                            milestones
                        ),
                        BRIGHT_MAGENTA
                    )
                )

            else:

                print(
                    "Milestones:     "
                    + color(
                        "None",
                        WHITE
                    )
                )

            print(
                color(
                    "-" * 105,
                    MAGENTA
                )
            )


# ============================================================
# STRATEGY CYCLE
# ============================================================

def strategy_cycle(
    state,
    market
):

    discoveries = discover_tokens()

    addresses = set()

    for item in discoveries:

        address = item.get(
            "address"
        )

        if address:

            addresses.add(
                address
            )

    analyzed = 0

    entries = 0
    exits = 0

    for address in addresses:

        pairs = get_pairs(
            address
        )

        if not pairs:
            continue

        valid = []

        for pair in pairs:

            data = normalize_pair(
                pair,
                "discovery"
            )

            if not data:
                continue

            if data[
                "liquidity"
            ] <= 0:

                continue

            valid.append(
                data
            )

        if not valid:
            continue

        valid.sort(
            key=lambda x: (
                x["liquidity"],
                x["volume_m5"]
            ),
            reverse=True
        )

        data = valid[0]

        token = data[
            "address"
        ]

        previous = state[
            "watchlist"
        ].get(token)

        score = score_token(
            data,
            previous
        )

        market[token] = data

        # ----------------------------------------------------
        # Save observation
        # ----------------------------------------------------

        state[
            "watchlist"
        ][token] = {

            "m5": data["m5"],

            "h1": data["h1"],

            "h6": data["h6"],

            "volume_m5":
                data["volume_m5"],

            "buy_pressure":
                data["buy_pressure"],

            "liquidity":
                data["liquidity"],

            "score":
                score,

            "last_price":
                data["price"],

            "timestamp":
                time.time()
        }

        # ----------------------------------------------------
        # Existing trade
        # ----------------------------------------------------

        if token in state[
            "open_trades"
        ]:

            trade = state[
                "open_trades"
            ][token]

            reason = update_trade(
                state,
                trade,
                data
            )

            if reason:

                close_trade(
                    state,
                    token,
                    data,
                    reason
                )

                exits += 1

            analyzed += 1

            continue

        # ----------------------------------------------------
        # Candidate
        # ----------------------------------------------------

        if score >= WATCH_SCORE:

            log_target(
                data,
                score,
                "WATCH / QUALITY CANDIDATE"
            )

        # ----------------------------------------------------
        # Entry
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

                entries += 1

        analyzed += 1

    # ========================================================
    # UPDATE OPEN TRADES
    # ========================================================

    for address in list(
        state[
            "open_trades"
        ].keys()
    ):

        data = market.get(
            address
        )

        if not data:
            continue

        trade = state[
            "open_trades"
        ][address]

        reason = update_trade(
            state,
            trade,
            data
        )

        if reason:

            close_trade(
                state,
                address,
                data,
                reason
            )

            exits += 1

    update_statistics(
        state
    )

    write_stats(
        state
    )

    save_state(
        state
    )

    return (
        analyzed,
        entries,
        exits
    )


# ============================================================
# MAIN
# ============================================================

def main():

    initialize_files()

    state = load_state()

    market = {}

    last_analysis = 0

    # --------------------------------------------------------
    # Startup
    # --------------------------------------------------------

    clear_terminal()

    print(
        color(
            "🔥 ALVIN MEME GOD V6.1",
            BRIGHT_MAGENTA
        )
    )

    print(
        color(
            "Paper Trading Engine",
            BRIGHT_WHITE
        )
    )

    print(
        color(
            "Terminal refresh: 1 second",
            BRIGHT_CYAN
        )
    )

    print(
        color(
            "Strategy analysis: 30 seconds",
            BRIGHT_YELLOW
        )
    )

    print(
        color(
            "No real trades are executed.",
            BRIGHT_GREEN
        )
    )

    print()

    if state[
        "open_trades"
    ]:

        print(
            color(
                f"Recovered "
                f"{len(state['open_trades'])} "
                f"open paper trade(s).",
                BRIGHT_GREEN
            )
        )

    print()

    time.sleep(2)

    # ========================================================
    # MAIN LOOP
    # ========================================================

    while True:

        try:

            current_time = time.time()

            # ------------------------------------------------
            # STRATEGY EVERY 30 SECONDS
            # ------------------------------------------------

            if (
                current_time
                - last_analysis
                >= SCAN_INTERVAL
            ):

                try:

                    print(
                        color(
                            f"[{timestamp()}] "
                            "Running market analysis...",
                            BRIGHT_YELLOW
                        )
                    )

                    (
                        analyzed,
                        entries,
                        exits
                    ) = strategy_cycle(
                        state,
                        market
                    )

                    print(
                        color(
                            f"[{timestamp()}] "
                            f"Analysis complete | "
                            f"Tokens: {analyzed} | "
                            f"Entries: {entries} | "
                            f"Exits: {exits}",
                            BRIGHT_GREEN
                        )
                    )

                except Exception as analysis_error:

                    print(
                        color(
                            f"ANALYSIS ERROR: "
                            f"{analysis_error}",
                            BRIGHT_RED
                        )
                    )

                finally:

                    last_analysis = time.time()

                    time.sleep(1)

            # ------------------------------------------------
            # TERMINAL EVERY SECOND
            # ------------------------------------------------

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
                color(
                    "Stopping ALVIN MEME GOD...",
                    BRIGHT_YELLOW
                )
            )

            save_state(
                state
            )

            write_stats(
                state
            )

            print(
                color(
                    "Paper-trading state saved.",
                    BRIGHT_GREEN
                )
            )

            break

        except Exception as error:

            print()

            print(
                color(
                    f"MAIN LOOP ERROR: {error}",
                    BRIGHT_RED
                )
            )

            time.sleep(2)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
