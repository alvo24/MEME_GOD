#!/usr/bin/env python3

import os
import json
import time
from datetime import datetime, timezone

import requests


# ============================================================
# ALVIN MEME GOD V6.1
# LIVE TRADE TERMINAL
# PAPER TRADING ONLY
# ============================================================

BOT_NAME = "ALVIN MEME GOD V6.1"
BASE_URL = "https://api.dexscreener.com"

SCAN_INTERVAL = 5

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

# QUALITY ENTRY
ENTRY_SCORE = 82
WATCH_SCORE = 70
MIN_LIQUIDITY = 25000
MIN_VOLUME_5M = 5000
MIN_BUY_PRESSURE = 58
MAX_ENTRY_SPIKE_5M = 20.0

# RISK
INITIAL_STOP = -0.10
MAX_HOLD_HOURS = 6

# gain -> trailing distance
TRAILING_LEVELS = [
    (0.15, 0.08),
    (0.30, 0.12),
    (1.00, 0.18),
    (5.00, 0.22),
    (10.00, 0.25),
    (50.00, 0.30),
]

TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_V6_1_STATE.json"


# ============================================================
# TERMINAL
# ============================================================

RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BLUE = "\033[94m"


def clear_screen():
    os.system("clear")


def now():
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def fnum(x, default=0.0):
    try:
        return float(x)
    except:
        return default


def write_log(filename, text):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(text + "\n")


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

    except Exception:
        return default_state()


def save_state(state):

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ============================================================
# API
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD-V6.1-PAPER"
})


def api_get(endpoint):

    try:

        r = session.get(
            BASE_URL + endpoint,
            timeout=20
        )

        if r.status_code == 429:
            print(
                f"{YELLOW}Rate limited. Waiting...{RESET}"
            )
            time.sleep(20)
            return []

        if r.status_code != 200:
            return []

        return r.json()

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

            if str(
                item.get("chainId", "")
            ).lower() != "solana":
                continue

            address = item.get(
                "tokenAddress"
            )

            if address:
                found[address] = endpoint

    return found


# ============================================================
# PAIR
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

        liq = fnum(
            pair.get(
                "liquidity",
                {}
            ).get("usd")
        )

        pairs.append(
            (liq, pair)
        )

    if not pairs:
        return None

    pairs.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return pairs[0][1]


def normalize(pair, source):

    base = pair.get(
        "baseToken",
        {}
    )

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
    )

    m1 = txns.get(
        "m1",
        {}
    ) or {}

    m5 = txns.get(
        "m5",
        {}
    ) or {}

    buys = int(
        fnum(m1.get("buys"))
    )

    sells = int(
        fnum(m1.get("sells"))
    )

    total = buys + sells

    buy_pressure = (
        buys / total * 100
        if total
        else 0
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

        "liquidity": fnum(
            pair.get(
                "liquidity",
                {}
            ).get("usd")
        ),

        "volume_m5": fnum(
            pair.get(
                "volume",
                {}
            ).get("m5")
        ),

        "volume_h1": fnum(
            pair.get(
                "volume",
                {}
            ).get("h1")
        ),

        "m5_buys": buys,
        "m5_sells": sells,
        "m5_total": total,

        "h1_buys": int(
            fnum(h1.get("buys"))
        ),

        "h1_sells": int(
            fnum(h1.get("sells"))
        ),

        "buy_pressure": buy_pressure,

        "change_m5": fnum(
            pair.get(
                "priceChange",
                {}
            ).get("m5")
        ),

        "change_h1": fnum(
            pair.get(
                "priceChange",
                {}
            ).get("h1")
        ),

        "change_h6": fnum(
            pair.get(
                "priceChange",
                {}
            ).get("h6")
        ),

        "source": source
    }


# ============================================================
# SCORE
# ============================================================

def score(d, old=None):

    s = 0

    liq = d["liquidity"]
    vol = d["volume_m5"]
    vol1 = d["volume_h1"]
    bp = d["buy_pressure"]
    m5 = d["change_m5"]
    h1 = d["change_h1"]
    h6 = d["change_h6"]

    if liq >= 100000:
        s += 15
    elif liq >= 50000:
        s += 13
    elif liq >= 25000:
        s += 10
    elif liq >= 15000:
        s += 6

    if vol >= 50000:
        s += 20
    elif vol >= 20000:
        s += 17
    elif vol >= 10000:
        s += 14
    elif vol >= 5000:
        s += 10

    if vol1 >= 500000:
        s += 10
    elif vol1 >= 200000:
        s += 8
    elif vol1 >= 50000:
        s += 6
    elif vol1 >= 20000:
        s += 4

    if bp >= 70:
        s += 20
    elif bp >= 65:
        s += 17
    elif bp >= 60:
        s += 14
    elif bp >= 58:
        s += 11

    if 3 <= m5 <= 15:
        s += 15
    elif 0 < m5 < 3:
        s += 9
    elif m5 > 15:
        s += 5

    if h1 >= 20:
        s += 12
    elif h1 >= 10:
        s += 10
    elif h1 > 0:
        s += 7

    if h6 >= 50:
        s += 6
    elif h6 >= 20:
        s += 5
    elif h6 > 0:
        s += 3

    if old:

        if d["change_m5"] > old.get(
            "change_m5", 0
        ):
            s += 6

        if d["buy_pressure"] > old.get(
            "buy_pressure", 0
        ):
            s += 5

        if d["volume_m5"] > old.get(
            "volume_m5", 0
        ):
            s += 5

    return min(100, max(0, s))


# ============================================================
# ENTRY SIGNAL
# ============================================================

def entry_signal(d, old, s):

    if d["liquidity"] < MIN_LIQUIDITY:
        return False, "LOW LIQUIDITY"

    if d["volume_m5"] < MIN_VOLUME_5M:
        return False, "LOW 5M VOLUME"

    if d["buy_pressure"] < MIN_BUY_PRESSURE:
        return False, "WEAK BUY PRESSURE"

    if s < ENTRY_SCORE:
        return False, "LOW SCORE"

    if d["change_h1"] <= 0:
        return False, "1H TREND NEGATIVE"

    if d["change_m5"] > MAX_ENTRY_SPIKE_5M:
        return False, "ENTRY TOO EXTENDED"

    if old is None:
        return False, "WAITING CONFIRMATION"

    old_m5 = old.get(
        "change_m5",
        0
    )

    old_bp = old.get(
        "buy_pressure",
        0
    )

    old_vol = old.get(
        "volume_m5",
        0
    )

    improving_momentum = (
        d["change_m5"] > old_m5
    )

    improving_buying = (
        d["buy_pressure"] > old_bp
    )

    improving_volume = (
        d["volume_m5"] > old_vol
    )

    recovery = (
        old_m5 <= 0
        and d["change_m5"] > 0
        and improving_buying
    )

    continuation = (
        d["change_m5"] > 0
        and improving_momentum
        and (
            improving_volume
            or improving_buying
        )
    )

    strong_buying = (
        d["buy_pressure"] >= 65
        and d["change_m5"] >= 0
        and (
            improving_buying
            or improving_volume
        )
    )

    if recovery:
        return True, "PULLBACK RECOVERY"

    if continuation:
        return True, "MOMENTUM CONTINUATION"

    if strong_buying:
        return True, "STRONG BUY PRESSURE"

    return False, "NO CONFIRMATION"


# ============================================================
# TRAILING
# ============================================================

def trailing_stop(trade):

    entry = trade["entry_price"]
    high = trade["highest_price"]

    if entry <= 0:
        return None

    gain = high / entry - 1

    trail = None

    for minimum, distance in TRAILING_LEVELS:

        if gain >= minimum:
            trail = distance

    if trail is None:
        return None

    return high * (1 - trail)


# ============================================================
# OPEN TRADE
# ============================================================

def already_open(state, address):

    return any(
        x["address"] == address
        for x in state["open_trades"]
    )


def open_trade(state, d, s, reason):

    if len(state["open_trades"]) >= MAX_OPEN_TRADES:
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

        "entry_score": s,
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

    state["balance"] -= PAPER_TRADE_SIZE

    state["open_trades"].append(
        trade
    )

    msg = (
        f"\nPAPER ENTRY\n"
        f"Token: {d['symbol']}\n"
        f"Contract: {d['address']}\n"
        f"Pair ID: {d['pair_id']}\n"
        f"Pair URL: {d['pair_url']}\n"
        f"Price: ${d['price']:.10f}\n"
        f"Score: {s}/100\n"
        f"Reason: {reason}\n"
        f"5M Buys: {d['m5_buys']}\n"
        f"5M Sells: {d['m5_sells']}\n"
        f"Buy Pressure: {d['buy_pressure']:.2f}%\n"
        f"Liquidity: ${d['liquidity']:,.2f}\n"
        f"5M Volume: ${d['volume_m5']:,.2f}\n"
        f"Time: {now()}\n"
    )

    write_log(
        TRADES_FILE,
        msg
    )


# ============================================================
# MILESTONES
# ============================================================

def milestones(state, trade, price):

    entry = trade["entry_price"]

    if entry <= 0:
        return

    multiple = price / entry

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

            trade["milestones_hit"].append(
                name
            )

            state["milestones"][name] += 1

            write_log(
                TRADES_FILE,
                (
                    f"\n🚀 {name} MILESTONE\n"
                    f"Token: {trade['symbol']}\n"
                    f"Contract: {trade['address']}\n"
                    f"Pair ID: {trade['pair_id']}\n"
                    f"Pair URL: {trade['pair_url']}\n"
                    f"Multiple: {multiple:.2f}X\n"
                    f"Time: {now()}\n"
                )
            )


# ============================================================
# CLOSE
# ============================================================

def close_trade(state, trade, d, reason):

    entry = trade["entry_price"]
    price = d["price"]

    if entry <= 0:
        return

    multiple = price / entry

    returned = (
        trade["stake"] * multiple
    )

    profit = (
        returned - trade["stake"]
    )

    state["balance"] += returned

    trade["exit_price"] = price
    trade["exit_time"] = now()
    trade["exit_reason"] = reason
    trade["profit"] = profit
    trade["final_multiple"] = multiple
    trade["return_value"] = returned

    state["closed_trades"].append(
        trade
    )

    state["open_trades"].remove(
        trade
    )

    write_log(
        TRADES_FILE,
        (
            f"\n"
            f"PAPER EXIT\n"
            f"Token: {trade['symbol']}\n"
            f"Contract: {trade['address']}\n"
            f"Pair ID: {trade['pair_id']}\n"
            f"Pair URL: {trade['pair_url']}\n"
            f"Entry: ${entry:.10f}\n"
            f"Exit: ${price:.10f}\n"
            f"Highest: ${trade['highest_price']:.10f}\n"
            f"Maximum: {trade['max_multiple']:.2f}X\n"
            f"Final: {multiple:.2f}X\n"
            f"P/L: ${profit:.2f}\n"
            f"Reason: {reason}\n"
            f"Time: {now()}\n"
        )
    )


# ============================================================
# UPDATE TRADES
# ============================================================

def update_trades(state, market):

    for trade in list(
        state["open_trades"]
    ):

        d = market.get(
            trade["address"]
        )

        if not d:
            continue

        price = d["price"]

        if price <= 0:
            continue

        if price > trade["highest_price"]:
            trade["highest_price"] = price

        multiple = (
            price /
            trade["entry_price"]
        )

        trade["max_multiple"] = max(
            trade["max_multiple"],
            trade["highest_price"] /
            trade["entry_price"]
        )

        milestones(
            state,
            trade,
            price
        )

        gain = multiple - 1

        reason = None

        if gain <= INITIAL_STOP:
            reason = "INITIAL STOP"

        stop = trailing_stop(trade)

        if stop is not None and price <= stop:
            reason = "TRAILING STOP"

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

        except:
            pass

        if reason:
            close_trade(
                state,
                trade,
                d,
                reason
            )


# ============================================================
# LIVE TERMINAL
# ============================================================

def live_terminal(state, market):

    clear_screen()

    closed = state["closed_trades"]

    wins = sum(
        1 for x in closed
        if x.get("profit", 0) > 0
    )

    losses = sum(
        1 for x in closed
        if x.get("profit", 0) < 0
    )

    realized = sum(
        x.get("profit", 0)
        for x in closed
    )

    print(
        f"{MAGENTA}"
        "╔════════════════════════════════════════════════════════════════════════════╗"
        "\n"
        f"║                    {BOT_NAME:^42} ║\n"
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
        f"{RESET}"
    )

    print(
        f"{WHITE}"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{RESET}"
    )

    if not state["open_trades"]:

        print(
            f"{YELLOW}"
            "                    NO OPEN PAPER TRADES"
            f"{RESET}"
        )

    else:

        print(
            f"{GREEN}"
            "                         LIVE PAPER TRADES"
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

            entry = trade["entry_price"]

            multiple = (
                price / entry
                if entry > 0
                else 1
            )

            pnl = (
                trade["stake"]
                * (multiple - 1)
            )

            print(
                f"│{i:>3} "
                f"│{trade['symbol'][:8]:<8} "
                f"│${entry:.6f} "
                f"│${price:.6f} "
                f"│{multiple:>7.2f}X "
                f"│${pnl:>7.2f} "
                "│"
            )

        print(
            "└────┴──────────┴──────────┴──────────┴──────────┴──────────┘"
        )

        print()

        # ----------------------------------------------------
        # DETAILED CONTRACT INFORMATION
        # ----------------------------------------------------

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
            entry = trade["entry_price"]

            multiple = (
                price / entry
                if entry > 0
                else 1
            )

            pnl = (
                trade["stake"]
                * (multiple - 1)
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
                f"{d['m5_total']}  "
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
                f"│ Entry Score: "
                f"{trade['entry_score']}/100"
            )

            print(
                f"│ Entry Reason: "
                f"{trade['entry_reason']}"
            )

            print(
                f"│ Entry: "
                f"${entry:.10f}"
            )

            print(
                f"│ Current: "
                f"${price:.10f}"
            )

            print(
                f"│ Highest: "
                f"${trade['highest_price']:.10f}"
            )

            print(
                f"│ Multiple: "
                f"{multiple:.2f}X"
            )

            print(
                f"│ Maximum: "
                f"{trade['max_multiple']:.2f}X"
            )

            print(
                f"│ P/L: "
                f"{pnl_color}${pnl:.2f}{RESET}"
            )

            print(
                f"{BLUE}"
                "└──────────────────────────────────────────────────────────────────────────"
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

    closed = state["closed_trades"]

    wins = [
        x for x in closed
        if x.get("profit", 0) > 0
    ]

    losses = [
        x for x in closed
        if x.get("profit", 0) < 0
    ]

    gp = sum(
        x.get("profit", 0)
        for x in wins
    )

    gl = sum(
        x.get("profit", 0)
        for x in losses
    )

    pf = (
        gp / abs(gl)
        if gl < 0
        else 0
    )

    wr = (
        len(wins) / len(closed) * 100
        if closed
        else 0
    )

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{BOT_NAME}\n"
            f"Updated: {now()}\n\n"
            f"Balance: ${state['balance']:.2f}\n"
            f"Open: {len(state['open_trades'])}\n"
            f"Closed: {len(closed)}\n"
            f"Wins: {len(wins)}\n"
            f"Losses: {len(losses)}\n"
            f"Win Rate: {wr:.2f}%\n"
            f"Realized P/L: "
            f"${sum(x.get('profit',0) for x in closed):.2f}\n"
            f"Profit Factor: {pf:.2f}\n\n"
            f"2X: {state['milestones']['2X']}\n"
            f"5X: {state['milestones']['5X']}\n"
            f"10X: {state['milestones']['10X']}\n"
            f"50X: {state['milestones']['50X']}\n"
            f"100X: {state['milestones']['100X']}\n"
        )


# ============================================================
# MAIN SCAN
# ============================================================

def scan(state):

    discovered = discover()

    market = {}

    candidates = []

    for address, source in discovered.items():

        pair = get_pair(address)

        if not pair:
            continue

        d = normalize(
            pair,
            source
        )

        if not d or d["price"] <= 0:
            continue

        old = state["watchlist"].get(
            address
        )

        s = score(
            d,
            old
        )

        market[address] = d

        state["watchlist"][address] = d

        if s >= WATCH_SCORE:

            valid, reason = entry_signal(
                d,
                old,
                s
            )

            candidates.append(
                (
                    s,
                    d,
                    old,
                    valid,
                    reason
                )
            )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # Update existing trades first
    update_trades(
        state,
        market
    )

    # New entries
    for s, d, old, valid, reason in candidates:

        if not valid:
            continue

        if len(
            state["open_trades"]
        ) >= MAX_OPEN_TRADES:
            break

        open_trade(
            state,
            d,
            s,
            reason
        )

    state["scans"] += 1

    save_state(state)
    save_stats(state)

    live_terminal(
        state,
        market
    )


# ============================================================
# START
# ============================================================

def main():

    for filename in [
        TARGETS_FILE,
        TRADES_FILE,
        STATS_FILE
    ]:

        if not os.path.exists(filename):

            open(
                filename,
                "w",
                encoding="utf-8"
            ).close()

    state = load_state()

    clear_screen()

    print(
        f"{MAGENTA}"
        f"""
╔══════════════════════════════════════════════════════════════════════╗
║                       ALVIN MEME GOD V6.1                           ║
║                     LIVE TRADE TERMINAL                             ║
║                                                                      ║
║                         PAPER MODE                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        f"{RESET}"
    )

    time.sleep(2)

    while True:

        try:

            scan(state)

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            save_state(state)
            save_stats(state)

            print(
                f"\n{YELLOW}"
                "V6.1 stopped."
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
