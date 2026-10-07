#!/usr/bin/env python3

"""
============================================================
        ALVIN MEME GOD V1.1
   HUMANIZED SOLANA MEME PAPER-TRADING ENGINE
============================================================

PUBLIC MARKET DATA + PAPER TRADING ONLY

Features:
- Solana token discovery through DexScreener
- Multi-factor humanized scoring
- Momentum analysis
- Volume analysis
- Buy-pressure analysis
- Liquidity analysis
- Anti-chasing
- Risk assessment
- WATCH / WAIT / PAPER ENTER decisions
- Simulated positions
- Trailing protection
- Runner alerts
- Persistent state
- Trade logging
- Colourful Termux dashboard

NO REAL TRADES
NO WALLET
NO PRIVATE KEYS
============================================================
"""

import os
import time
import json
import requests
from datetime import datetime, timezone


# ============================================================
# CONFIG
# ============================================================

BOT_NAME = "ALVIN MEME GOD V1.1"

BASE_URL = "https://api.dexscreener.com"
CHAIN = "solana"

SCAN_INTERVAL = 10
REQUEST_TIMEOUT = 15

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0
MAX_OPEN_TRADES = 5

MIN_LIQUIDITY = 25_000
MIN_VOLUME_5M = 5_000
MIN_VOLUME_1H = 15_000

MIN_QUALITY_SCORE = 55
MIN_ENTRY_SCORE = 72

MAX_HOLD_HOURS = 6


# ============================================================
# FILES
# ============================================================

STATE_FILE = "MEME_GOD_V1_STATE.json"
TRADE_LOG = "MEME_GOD_V1_TRADES.txt"


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

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
    if risk >= 70:
        return BRIGHT_RED
    if risk >= 45:
        return YELLOW
    return BRIGHT_GREEN


def pct_color(value):
    if value > 0:
        return BRIGHT_GREEN
    if value < 0:
        return BRIGHT_RED
    return WHITE


def decision_color(decision):
    if decision == "PAPER ENTER":
        return BRIGHT_GREEN
    if decision == "WATCH":
        return BRIGHT_YELLOW
    if decision == "WAIT":
        return YELLOW
    if decision == "AVOID":
        return BRIGHT_RED
    if decision == "HOLD":
        return BRIGHT_CYAN
    if decision == "EXIT":
        return BRIGHT_RED
    return WHITE


def decision_icon(decision):
    icons = {
        "PAPER ENTER": "🚀",
        "WATCH": "👀",
        "WAIT": "⏳",
        "AVOID": "⛔",
        "HOLD": "💎",
        "EXIT": "🔴",
    }
    return icons.get(decision, "•")


# ============================================================
# GENERAL HELPERS
# ============================================================

def clear_screen():
    os.system("clear")


def current_time():
    return datetime.now(timezone.utc)


def timestamp():
    return current_time().strftime("%Y-%m-%d %H:%M:%S UTC")


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_div(a, b):
    if b == 0:
        return 0.0
    return a / b


def clamp(value, low, high):
    return max(low, min(high, value))


# ============================================================
# STATE
# ============================================================

def default_state():
    return {
        "balance": STARTING_BALANCE,
        "starting_balance": STARTING_BALANCE,
        "realized_pnl": 0.0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "open_positions": {},
        "runner_alerts": [],
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return default_state()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)

        state = default_state()
        state.update(saved)
        return state

    except Exception:
        return default_state()


def save_state(state):
    temp_file = STATE_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

        os.replace(temp_file, STATE_FILE)

    except Exception as error:
        print(C(BRIGHT_RED, f"State error: {error}"))


def log_trade(message):
    try:
        with open(TRADE_LOG, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp()}] {message}\n")
    except Exception:
        pass


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD-PAPER/1.1"
})


def api_get(url):
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT
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

    url = f"{BASE_URL}/token-profiles/latest/v1"

    data = api_get(url)

    if not isinstance(data, list):
        return []

    results = []

    for item in data:

        if item.get("chainId") != CHAIN:
            continue

        address = item.get("tokenAddress")

        if not address:
            continue

        results.append(address)

    return results


# ============================================================
# TOKEN PAIRS
# ============================================================

def get_pairs(address):

    url = f"{BASE_URL}/token-pairs/v1/{CHAIN}/{address}"

    data = api_get(url)

    if not isinstance(data, list):
        return []

    return data


# ============================================================
# NORMALIZE MARKET DATA
# ============================================================

def normalize_pair(pair):

    txns = pair.get("txns") or {}
    volume = pair.get("volume") or {}
    liquidity = pair.get("liquidity") or {}
    price_change = pair.get("priceChange") or {}

    m5 = txns.get("m5") or {}
    h1 = txns.get("h1") or {}

    buys_5m = number(m5.get("buys"))
    sells_5m = number(m5.get("sells"))

    total_trades = buys_5m + sells_5m

    buy_pressure = safe_div(
        buys_5m,
        total_trades
    )

    base_token = pair.get("baseToken") or {}

    return {
        "pair_address": pair.get("pairAddress"),
        "token_address": base_token.get("address"),
        "symbol": base_token.get("symbol") or "UNKNOWN",
        "name": base_token.get("name") or "Unknown",

        "price": number(pair.get("priceUsd")),

        "liquidity": number(
            liquidity.get("usd")
        ),

        "volume_5m": number(
            volume.get("m5")
        ),

        "volume_1h": number(
            volume.get("h1")
        ),

        "volume_6h": number(
            volume.get("h6")
        ),

        "volume_24h": number(
            volume.get("h24")
        ),

        "buys_5m": buys_5m,
        "sells_5m": sells_5m,

        "buys_1h": number(
            h1.get("buys")
        ),

        "sells_1h": number(
            h1.get("sells")
        ),

        "buy_pressure": buy_pressure,

        "change_5m": number(
            price_change.get("m5")
        ),

        "change_1h": number(
            price_change.get("h1")
        ),

        "change_6h": number(
            price_change.get("h6")
        ),

        "change_24h": number(
            price_change.get("h24")
        ),

        "url": pair.get("url") or "",
    }


# ============================================================
# MOMENTUM
# ============================================================

def momentum_score(m):

    score = 0.0

    change_5m = m["change_5m"]
    change_1h = m["change_1h"]
    change_6h = m["change_6h"]

    if 2 <= change_5m <= 8:
        score += 20

    elif 8 < change_5m <= 15:
        score += 17

    elif 15 < change_5m <= 25:
        score += 10

    elif change_5m > 25:
        score += 2

    elif change_5m > 0:
        score += 8

    if change_1h > 15:
        score += 25

    elif change_1h > 8:
        score += 20

    elif change_1h > 3:
        score += 14

    elif change_1h > 0:
        score += 8

    if change_6h > 30:
        score += 20

    elif change_6h > 15:
        score += 15

    elif change_6h > 5:
        score += 10

    return clamp(score, 0, 65)


# ============================================================
# VOLUME
# ============================================================

def volume_score(m):

    score = 0.0

    if m["volume_5m"] >= MIN_VOLUME_5M:
        score += 20

    if m["volume_1h"] >= MIN_VOLUME_1H:
        score += 20

    expected_5m = m["volume_1h"] / 12

    if expected_5m > 0:

        acceleration = safe_div(
            m["volume_5m"],
            expected_5m
        )

        if acceleration >= 2.0:
            score += 20

        elif acceleration >= 1.4:
            score += 15

        elif acceleration >= 1.0:
            score += 10

    return clamp(score, 0, 60)


def volume_label(m):

    expected = safe_div(
        m["volume_1h"],
        12
    )

    if expected <= 0:
        return "UNKNOWN"

    acceleration = safe_div(
        m["volume_5m"],
        expected
    )

    if acceleration >= 2:
        return "🔥 ACCELERATING"

    if acceleration >= 1.4:
        return "📈 INCREASING"

    if acceleration >= 0.8:
        return "😐 NORMAL"

    return "🔴 LOW"


# ============================================================
# BUY PRESSURE
# ============================================================

def pressure_score(m):

    pressure = m["buy_pressure"]

    if pressure >= 0.70:
        return 30

    if pressure >= 0.65:
        return 25

    if pressure >= 0.60:
        return 20

    if pressure >= 0.55:
        return 12

    return 0


# ============================================================
# LIQUIDITY
# ============================================================

def liquidity_score(m):

    liquidity = m["liquidity"]

    if liquidity >= 100_000:
        return 25

    if liquidity >= 50_000:
        return 22

    if liquidity >= 25_000:
        return 17

    return 0


def liquidity_label(m):

    liquidity = m["liquidity"]

    if liquidity >= 100_000:
        return "💧 VERY HEALTHY"

    if liquidity >= 50_000:
        return "💧 HEALTHY"

    if liquidity >= 25_000:
        return "🟡 ACCEPTABLE"

    return "🔴 THIN"


# ============================================================
# CHASE RISK
# ============================================================

def chase_risk(m):

    change = m["change_5m"]

    if change >= 30:
        return 90

    if change >= 20:
        return 70

    if change >= 12:
        return 45

    if change >= 5:
        return 20

    return 10


# ============================================================
# GENERAL RISK
# ============================================================

def risk_score(m):

    risk = 0.0

    if m["liquidity"] < MIN_LIQUIDITY:
        risk += 30

    if m["buy_pressure"] < 0.55:
        risk += 20

    if m["volume_5m"] < MIN_VOLUME_5M:
        risk += 15

    if m["change_5m"] > 25:
        risk += 20

    if m["change_5m"] < -10:
        risk += 25

    if m["change_1h"] < -15:
        risk += 20

    return clamp(risk, 0, 100)


# ============================================================
# STRUCTURE
# ============================================================

def structure_label(m):

    short = m["change_5m"]
    hour = m["change_1h"]
    six = m["change_6h"]

    if short > 0 and hour > 0 and six > 0:
        return "BUILDING"

    if short > 0 and hour > 0:
        return "POSITIVE"

    if short > 0 and hour < 0:
        return "RECOVERY"

    if short < 0 and hour < 0:
        return "WEAK"

    return "MIXED"


# ============================================================
# HUMAN ANALYSIS
# ============================================================

def analyze(m):

    momentum = momentum_score(m)
    volume = volume_score(m)
    pressure = pressure_score(m)
    liquidity = liquidity_score(m)

    quality = (
        momentum
        + volume
        + pressure
        + liquidity
    ) / 1.8

    quality = clamp(
        quality,
        0,
        100
    )

    chase = chase_risk(m)
    risk = risk_score(m)

    entry = (
        quality * 0.40
        + momentum * 0.25
        + pressure * 0.15
        + liquidity * 0.20
    )

    entry -= chase * 0.20
    entry -= risk * 0.15

    entry = clamp(
        entry,
        0,
        100
    )

    signals = []
    warnings = []

    if momentum >= 35:
        signals.append(
            "Momentum is positive"
        )

    if volume >= 30:
        signals.append(
            "Volume supports the move"
        )

    if pressure >= 20:
        signals.append(
            "Buyers are gaining control"
        )

    if liquidity >= 17:
        signals.append(
            "Liquidity is reasonably healthy"
        )

    if (
        m["change_5m"] > 0
        and m["change_1h"] > 0
    ):
        signals.append(
            "Short and hourly direction agree"
        )

    if chase >= 70:
        warnings.append(
            "Price is becoming extended."
        )

    if risk >= 60:
        warnings.append(
            "Overall risk is elevated."
        )

    if m["buy_pressure"] < 0.55:
        warnings.append(
            "Selling pressure remains significant."
        )

    if risk >= 75:
        decision = "AVOID"

    elif chase >= 80:
        decision = "WAIT"

    elif (
        entry >= MIN_ENTRY_SCORE
        and quality >= MIN_QUALITY_SCORE
        and risk < 50
        and chase < 70
    ):
        decision = "PAPER ENTER"

    elif quality >= MIN_QUALITY_SCORE:
        decision = "WATCH"

    else:
        decision = "WAIT"

    if len(signals) >= 5:
        reason = (
            "Strong agreement across momentum, "
            "volume, buyers and liquidity."
        )

    elif len(signals) >= 3:
        reason = (
            "Several positive signals agree, "
            "but risk still needs monitoring."
        )

    elif signals:
        reason = (
            "There is positive activity, "
            "but confirmation is limited."
        )

    else:
        reason = (
            "Market evidence is currently weak."
        )

    if warnings:
        reason += " " + warnings[0]

    return {
        "momentum": momentum,
        "volume": volume,
        "pressure": pressure,
        "liquidity": liquidity,

        "quality": quality,
        "entry": entry,
        "risk": risk,
        "chase": chase,

        "structure": structure_label(m),
        "volume_label": volume_label(m),
        "liquidity_label": liquidity_label(m),

        "signals": signals,
        "warnings": warnings,

        "decision": decision,
        "reason": reason,
    }


# ============================================================
# DASHBOARD
# ============================================================

def print_header(state):

    clear_screen()

    width = 68

    print(
        C(
            BRIGHT_CYAN,
            "╔" + "═" * width + "╗"
        )
    )

    title_text = " 🧠 ALVIN MEME GOD V1.1"

    print(
        C(BRIGHT_CYAN, "║")
        + C(BOLD + BRIGHT_WHITE, title_text)
        + " " * (width - len(title_text))
        + C(BRIGHT_CYAN, "║")
    )

    subtitle = "     HUMANIZED PAPER TRADING ENGINE"

    print(
        C(BRIGHT_CYAN, "║")
        + C(BRIGHT_YELLOW, subtitle)
        + " " * (width - len(subtitle))
        + C(BRIGHT_CYAN, "║")
    )

    print(
        C(
            BRIGHT_CYAN,
            "╚" + "═" * width + "╝"
        )
    )

    pnl = (
        state["balance"]
        - state["starting_balance"]
    )

    if pnl >= 0:
        pnl_text = C(
            BRIGHT_GREEN,
            f"+${pnl:.2f}"
        )
    else:
        pnl_text = C(
            BRIGHT_RED,
            f"-${abs(pnl):.2f}"
        )

    print()

    print(
        f"💰 Balance: "
        f"{C(BRIGHT_WHITE, '${:.2f}'.format(state['balance']))}"
        f"   📈 P/L: {pnl_text}"
    )

    print(
        f"🟢 Wins: {C(BRIGHT_GREEN, state['wins'])}"
        f"   🔴 Losses: {C(BRIGHT_RED, state['losses'])}"
        f"   📊 Trades: {state['total_trades']}"
    )

    print(
        f"🚀 Open: "
        f"{len(state['open_positions'])}/{MAX_OPEN_TRADES}"
    )

    print(
        C(BLUE, "─" * 68)
    )


def print_candidate(m, analysis):

    decision = analysis["decision"]

    print(
        C(
            decision_color(decision),
            f"{decision_icon(decision)} "
            f"{m['symbol'][:12]:<12}"
        )
        + " "
        + C(
            score_color(analysis["quality"]),
            f"Q:{analysis['quality']:5.1f}"
        )
        + " "
        + C(
            score_color(analysis["entry"]),
            f"E:{analysis['entry']:5.1f}"
        )
        + " "
        + C(
            risk_color(analysis["risk"]),
            f"R:{analysis['risk']:5.1f}"
        )
    )

    print(
        f"   💵 ${m['price']:.10f}"
        f"   5m {C(pct_color(m['change_5m']), f'{m['change_5m']:+.1f}%')}"
        f"   1h {C(pct_color(m['change_1h']), f'{m['change_1h']:+.1f}%')}"
    )

    print(
        f"   💧 ${m['liquidity']:,.0f}"
        f"   🟢 Buy {m['buy_pressure'] * 100:.1f}%"
    )


def print_analysis(m, analysis):

    print()

    print(
        C(
            BOLD + BRIGHT_CYAN,
            "┌─ HUMAN ANALYSIS ───────────────────────────────────────────"
        )
    )

    print(
        f"│ 🪙 {C(BOLD + BRIGHT_WHITE, m['symbol'])}"
        f" — {m['name'][:35]}"
    )

    print(
        f"│ 📈 Momentum: "
        f"{C(score_color(analysis['momentum']), f'{analysis['momentum']:.0f}/65')}"
    )

    print(
        f"│ 📊 Volume: "
        f"{C(BRIGHT_WHITE, analysis['volume_label'])}"
    )

    print(
        f"│ 🟢 Buy pressure: "
        f"{C(score_color(m['buy_pressure'] * 100), f'{m['buy_pressure'] * 100:.1f}%')}"
    )

    print(
        f"│ 🏗️ Structure: "
        f"{C(BRIGHT_WHITE, analysis['structure'])}"
    )

    print(
        f"│ 💧 Liquidity: "
        f"${m['liquidity']:,.0f} "
        f"{analysis['liquidity_label']}"
    )

    print(
        f"│ 🏃 Chase risk: "
        f"{C(risk_color(analysis['chase']), f'{analysis['chase']:.0f}/100')}"
    )

    print(
        f"│ ⚠️ Risk: "
        f"{C(risk_color(analysis['risk']), f'{analysis['risk']:.0f}/100')}"
    )

    print(
        f"│ 🎯 Quality: "
        f"{C(score_color(analysis['quality']), f'{analysis['quality']:.1f}/100')}"
    )

    print(
        f"│ 🚪 Entry: "
        f"{C(score_color(analysis['entry']), f'{analysis['entry']:.1f}/100')}"
    )

    print("│")

    for signal in analysis["signals"]:
        print(
            f"│ {C(BRIGHT_GREEN, '✓')} {signal}"
        )

    for warning in analysis["warnings"]:
        print(
            f"│ {C(BRIGHT_YELLOW, '⚠')} {warning}"
        )

    print("│")

    decision = analysis["decision"]

    print(
        f"│ {C(BOLD + decision_color(decision), decision_icon(decision) + ' ' + decision)}"
    )

    print(
        f"│ 💭 {analysis['reason']}"
    )

    print(
        C(
            BRIGHT_CYAN,
            "└──────────────────────────────────────────────────────────────"
        )
    )


# ============================================================
# PAPER TRADING
# ============================================================

def position_pnl(position, price):

    entry = position["entry_price"]

    if entry <= 0:
        return 0.0

    return (
        (price - entry)
        / entry
    ) * 100


def enter_paper_trade(
    state,
    market,
    analysis
):

    if len(state["open_positions"]) >= MAX_OPEN_TRADES:
        return False

    address = market["token_address"]

    if not address:
        return False

    if address in state["open_positions"]:
        return False

    if state["balance"] < PAPER_TRADE_SIZE:
        return False

    position = {
        "symbol": market["symbol"],
        "address": address,
        "pair_address": market["pair_address"],
        "entry_price": market["price"],
        "highest_price": market["price"],
        "amount": PAPER_TRADE_SIZE,
        "entry_time": timestamp(),
        "entry_score": analysis["entry"],
    }

    state["balance"] -= PAPER_TRADE_SIZE

    state["open_positions"][address] = position

    state["total_trades"] += 1

    log_trade(
        f"PAPER ENTRY | "
        f"{market['symbol']} | "
        f"price={market['price']} | "
        f"entry={analysis['entry']:.1f}"
    )

    return True


def exit_paper_trade(
    state,
    address,
    price,
    reason
):

    position = state["open_positions"].get(address)

    if not position:
        return

    pnl_percent = position_pnl(
        position,
        price
    )

    pnl_money = (
        PAPER_TRADE_SIZE
        * pnl_percent
        / 100
    )

    state["balance"] += (
        PAPER_TRADE_SIZE
        + pnl_money
    )

    state["realized_pnl"] += pnl_money

    if pnl_money >= 0:
        state["wins"] += 1
    else:
        state["losses"] += 1

    state["best_trade"] = max(
        state["best_trade"],
        pnl_money
    )

    state["worst_trade"] = min(
        state["worst_trade"],
        pnl_money
    )

    log_trade(
        f"PAPER EXIT | "
        f"{position['symbol']} | "
        f"pnl={pnl_percent:+.2f}% | "
        f"${pnl_money:+.2f} | "
        f"reason={reason}"
    )

    del state["open_positions"][address]


# ============================================================
# POSITION MANAGEMENT
# ============================================================

def manage_positions(
    state,
    markets
):

    for address, position in list(
        state["open_positions"].items()
    ):

        market = markets.get(address)

        if not market:
            continue

        price = market["price"]

        if price <= 0:
            continue

        if price > position["highest_price"]:
            position["highest_price"] = price

        pnl = position_pnl(
            position,
            price
        )

        # Hard paper protection
        if pnl <= -5:
            exit_paper_trade(
                state,
                address,
                price,
                "Paper risk protection"
            )
            continue

        # Time protection
        try:

            entry_time = datetime.strptime(
                position["entry_time"],
                "%Y-%m-%d %H:%M:%S UTC"
            ).replace(
                tzinfo=timezone.utc
            )

            hours = (
                current_time()
                - entry_time
            ).total_seconds() / 3600

        except Exception:

            hours = 0

        if hours >= MAX_HOLD_HOURS:
            exit_paper_trade(
                state,
                address,
                price,
                "Maximum hold time"
            )
            continue

        # Trailing protection
        peak = position["highest_price"]

        if peak <= position["entry_price"]:
            continue

        drawdown = safe_div(
            price - peak,
            peak
        ) * 100

        if peak >= position["entry_price"] * 1.50:
            trailing = 15

        elif peak >= position["entry_price"] * 1.25:
            trailing = 12

        elif peak >= position["entry_price"] * 1.10:
            trailing = 10

        else:
            trailing = 8

        if drawdown <= -trailing:
            exit_paper_trade(
                state,
                address,
                price,
                "Trailing protection"
            )


# ============================================================
# RUNNER DETECTION
# ============================================================

def is_runner(market, analysis):

    return (
        analysis["quality"] >= 65
        and analysis["momentum"] >= 35
        and market["buy_pressure"] >= 0.62
        and market["volume_5m"] >= MIN_VOLUME_5M
        and market["liquidity"] >= MIN_LIQUIDITY
    )


# ============================================================
# SCAN
# ============================================================

def scan(state):

    discovered = discover_tokens()

    candidates = []

    for address in discovered[:30]:

        pairs = get_pairs(address)

        best_market = None

        for pair in pairs:

            if pair.get("chainId") != CHAIN:
                continue

            market = normalize_pair(pair)

            if market["price"] <= 0:
                continue

            if market["liquidity"] < MIN_LIQUIDITY:
                continue

            if market["volume_5m"] < MIN_VOLUME_5M:
                continue

            if (
                best_market is None
                or market["liquidity"]
                > best_market["liquidity"]
            ):
                best_market = market

        if best_market is None:
            continue

        analysis = analyze(
            best_market
        )

        candidates.append(
            (best_market, analysis)
        )

    candidates.sort(
        key=lambda item: (
            item[1]["entry"],
            item[1]["quality"]
        ),
        reverse=True
    )

    markets = {}

    for market, analysis in candidates:
        markets[
            market["token_address"]
        ] = market

    manage_positions(
        state,
        markets
    )

    print_header(state)

    print(
        C(
            BOLD + BRIGHT_WHITE,
            f"🔎 Discoveries: {len(discovered)}"
            f"   Qualified: {len(candidates)}"
        )
    )

    print()

    for market, analysis in candidates[:10]:

        print_candidate(
            market,
            analysis
        )

    if candidates:

        best_market, best_analysis = candidates[0]

        print_analysis(
            best_market,
            best_analysis
        )

        if (
            best_analysis["decision"]
            == "PAPER ENTER"
        ):

            entered = enter_paper_trade(
                state,
                best_market,
                best_analysis
            )

            if entered:

                print()

                print(
                    C(
                        BOLD + BRIGHT_GREEN,
                        f"🚀 PAPER ENTRY: "
                        f"{best_market['symbol']}"
                    )
                )

    # Runner alerts
    for market, analysis in candidates:

        if not is_runner(
            market,
            analysis
        ):
            continue

        address = market["token_address"]

        if address not in state["runner_alerts"]:

            state["runner_alerts"].append(
                address
            )

            print()

            print(
                C(
                    BOLD + BRIGHT_MAGENTA,
                    f"🚀 RUNNER ALERT: "
                    f"{market['symbol']}"
                )
            )

    save_state(state)


# ============================================================
# MAIN
# ============================================================

def main():

    state = load_state()

    print_header(state)

    print(
        C(
            BOLD + BRIGHT_YELLOW,
            "⚠️ PAPER TRADING MODE ONLY"
        )
    )

    print(
        C(
            BRIGHT_CYAN,
            "No wallet • No private key • No real orders"
        )
    )

    time.sleep(2)

    while True:

        try:

            scan(state)

            print()

            print(
                C(
                    DIM,
                    f"⏱️ Next scan in "
                    f"{SCAN_INTERVAL} seconds..."
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
                    "👋 ALVIN MEME GOD stopped."
                )
            )

            break

        except Exception as error:

            print()

            print(
                C(
                    BRIGHT_RED,
                    f"⚠️ Engine error: {error}"
                )
            )

            time.sleep(10)


if __name__ == "__main__":
    main()
