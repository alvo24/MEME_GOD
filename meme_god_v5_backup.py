import os
import json
import time
from datetime import datetime

import requests

# ============================================================
# ALVIN MEME GOD V5
# ACTIVE MOMENTUM + PULLBACK/RECOVERY PAPER TRADER
# PAPER TRADING ONLY
# ============================================================

API = "https://api.dexscreener.com"

SCAN_INTERVAL = 30

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0

# More active than V4
MAX_OPEN_TRADES = 10

# Looser entry filters
ENTRY_SCORE = 72
WATCH_SCORE = 60

MIN_LIQUIDITY = 10_000
MIN_VOLUME_5M = 1_000

MIN_BUY_PRESSURE = 0.52

# Protective paper stop
STOP_LOSS = -0.15

# Let winners run
TRAIL_START = 0.30
TRAIL_DISTANCE = 0.20

# Don't keep dead trades forever
MAX_HOLD_SECONDS = 4 * 60 * 60

# Don't immediately re-enter the same token
COOLDOWN_SECONDS = 30 * 60

TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_STATE.json"


# ============================================================
# FILES
# ============================================================

def ensure_files():
    for f in [
        TARGETS_FILE,
        TRADES_FILE,
        STATS_FILE,
    ]:
        if not os.path.exists(f):
            open(f, "a").close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(filename, message):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{now()}] {message}\n")


# ============================================================
# STATE
# ============================================================

def default_state():
    return {
        "balance": STARTING_BALANCE,
        "open_trades": {},
        "closed_trades": [],
        "watchlist": {},
        "observations": {},
        "cooldowns": {}
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return default_state()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        base = default_state()
        base.update(data)
        return base

    except Exception:
        return default_state()


def save_state(state):
    temp = STATE_FILE + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    os.replace(temp, STATE_FILE)


# ============================================================
# HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ALVIN-MEME-GOD/5.0"
})


def get_json(url):
    try:
        r = session.get(url, timeout=15)

        if r.status_code == 429:
            print("Rate limited. Waiting...")
            time.sleep(20)
            return None

        if r.status_code != 200:
            return None

        return r.json()

    except Exception as e:
        print("API error:", e)
        return None


# ============================================================
# DISCOVERY
# ============================================================

def discover_profiles():

    data = get_json(
        f"{API}/token-profiles/latest/v1"
    )

    if not isinstance(data, list):
        return []

    return [
        x.get("tokenAddress")
        for x in data
        if x.get("chainId") == "solana"
        and x.get("tokenAddress")
    ]


def discover_boosted():

    addresses = []

    for endpoint in [
        "/token-boosts/latest/v1",
        "/token-boosts/top/v1"
    ]:

        data = get_json(API + endpoint)

        if not isinstance(data, list):
            continue

        for x in data:

            if x.get("chainId") != "solana":
                continue

            address = x.get("tokenAddress")

            if address:
                addresses.append(address)

    return addresses


def discover():

    addresses = []

    for address in discover_boosted():
        if address not in addresses:
            addresses.append(address)

    for address in discover_profiles():
        if address not in addresses:
            addresses.append(address)

    return addresses[:35]


# ============================================================
# PAIRS
# ============================================================

def get_best_pair(address):

    data = get_json(
        f"{API}/token-pairs/v1/solana/{address}"
    )

    if not isinstance(data, list):
        return None

    pairs = [
        p for p in data
        if p.get("chainId") == "solana"
    ]

    if not pairs:
        return None

    def liquidity(pair):

        try:
            return float(
                pair.get("liquidity", {}).get("usd") or 0
            )
        except Exception:
            return 0

    return max(pairs, key=liquidity)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(pair, address, source):

    try:
        price = float(pair.get("priceUsd") or 0)
    except Exception:
        price = 0

    liquidity = float(
        pair.get("liquidity", {}).get("usd") or 0
    )

    volume = pair.get("volume", {})
    txns = pair.get("txns", {})
    price_change = pair.get("priceChange", {})

    m5_volume = float(volume.get("m5") or 0)
    h1_volume = float(volume.get("h1") or 0)

    m5_txns = txns.get("m5", {})
    h1_txns = txns.get("h1", {})

    buys = int(m5_txns.get("buys") or 0)
    sells = int(m5_txns.get("sells") or 0)

    total = buys + sells

    buy_pressure = (
        buys / total
        if total > 0
        else 0.50
    )

    return {
        "address": address,

        "symbol": pair.get("baseToken", {}).get(
            "symbol", "UNKNOWN"
        ),

        "name": pair.get("baseToken", {}).get(
            "name", "UNKNOWN"
        ),

        "price": price,

        "market_cap": float(
            pair.get("marketCap") or
            pair.get("fdv") or
            0
        ),

        "liquidity": liquidity,

        "volume_5m": m5_volume,
        "volume_1h": h1_volume,

        "buys": buys,
        "sells": sells,

        "buy_pressure": buy_pressure,

        "change_5m": float(
            price_change.get("m5") or 0
        ),

        "change_1h": float(
            price_change.get("h1") or 0
        ),

        "change_6h": float(
            price_change.get("h6") or 0
        ),

        "change_24h": float(
            price_change.get("h24") or 0
        ),

        "created": pair.get("pairCreatedAt"),

        "url": pair.get("url"),

        "source": source
    }


# ============================================================
# SCORING
# ============================================================

def calculate_score(t, previous=None):

    score = 0

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if t["liquidity"] >= 100_000:
        score += 15

    elif t["liquidity"] >= 50_000:
        score += 13

    elif t["liquidity"] >= 25_000:
        score += 10

    elif t["liquidity"] >= 10_000:
        score += 7

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if t["volume_5m"] >= 50_000:
        score += 20

    elif t["volume_5m"] >= 20_000:
        score += 17

    elif t["volume_5m"] >= 5_000:
        score += 13

    elif t["volume_5m"] >= 1_000:
        score += 8

    # --------------------------------------------------------
    # 1H VOLUME
    # --------------------------------------------------------

    if t["volume_1h"] >= 100_000:
        score += 10

    elif t["volume_1h"] >= 25_000:
        score += 7

    elif t["volume_1h"] >= 10_000:
        score += 4

    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    bp = t["buy_pressure"]

    if bp >= 0.65:
        score += 20

    elif bp >= 0.60:
        score += 17

    elif bp >= 0.55:
        score += 13

    elif bp >= 0.52:
        score += 8

    # --------------------------------------------------------
    # 5M MOMENTUM
    # --------------------------------------------------------

    m5 = t["change_5m"]

    if 2 <= m5 <= 12:
        score += 12

    elif 0 < m5 < 2:
        score += 8

    elif -3 <= m5 <= 0:
        score += 5

    elif m5 > 12:
        score += 6

    # --------------------------------------------------------
    # 1H TREND
    # --------------------------------------------------------

    h1 = t["change_1h"]

    if h1 >= 30:
        score += 12

    elif h1 >= 15:
        score += 10

    elif h1 >= 5:
        score += 7

    elif h1 > 0:
        score += 4

    elif h1 >= -5:
        score += 2

    # --------------------------------------------------------
    # 6H TREND
    # --------------------------------------------------------

    if t["change_6h"] > 20:
        score += 5

    elif t["change_6h"] > 0:
        score += 3

    # --------------------------------------------------------
    # PULLBACK / RECOVERY BONUS
    # --------------------------------------------------------

    if previous:

        previous_m5 = previous.get(
            "change_5m", 0
        )

        current_m5 = t["change_5m"]

        if previous_m5 <= 0 and current_m5 > 0:
            score += 7

        if previous_m5 < current_m5:
            score += 3

        if (
            previous.get("buy_pressure", 0.50)
            < t["buy_pressure"]
        ):
            score += 3

    # --------------------------------------------------------
    # LIQUIDITY / MARKET CAP
    # --------------------------------------------------------

    mc = t["market_cap"]

    if mc > 0:

        ratio = t["liquidity"] / mc

        if ratio >= 0.15:
            score += 6

        elif ratio >= 0.05:
            score += 3

    return min(100, max(0, score))


# ============================================================
# ENTRY LOGIC
# ============================================================

def entry_confirmation(t, previous):

    if t["liquidity"] < MIN_LIQUIDITY:
        return False, "low liquidity"

    if t["volume_5m"] < MIN_VOLUME_5M:
        return False, "low 5m volume"

    if t["buy_pressure"] < MIN_BUY_PRESSURE:
        return False, "weak buy pressure"

    # Avoid extremely vertical candles
    if t["change_5m"] > 25:
        return False, "chasing vertical move"

    positive_momentum = t["change_5m"] > 0

    recovery = False

    if previous:

        if (
            previous.get("change_5m", 0) <= 0
            and t["change_5m"] > 0
        ):
            recovery = True

        if (
            t["buy_pressure"]
            >= previous.get("buy_pressure", 0)
        ):
            recovery = recovery or True

    # Loose entry:
    # positive momentum OR recovery
    if positive_momentum or recovery:

        return True, "momentum/recovery confirmed"

    return False, "waiting for recovery"


# ============================================================
# OPEN TRADE
# ============================================================

def open_trade(state, t, score):

    address = t["address"]

    if len(state["open_trades"]) >= MAX_OPEN_TRADES:
        return False

    if address in state["open_trades"]:
        return False

    cooldown = state["cooldowns"].get(address, 0)

    if time.time() < cooldown:
        return False

    if state["balance"] < PAPER_TRADE_SIZE:
        return False

    entry = t["price"]

    if entry <= 0:
        return False

    state["balance"] -= PAPER_TRADE_SIZE

    state["open_trades"][address] = {
        "address": address,
        "symbol": t["symbol"],
        "name": t["name"],

        "entry_price": entry,

        "highest_price": entry,

        "lowest_price": entry,

        "stake": PAPER_TRADE_SIZE,

        "entry_score": score,

        "entry_time": time.time(),

        "source": t["source"],

        "url": t["url"]
    }

    log(
        TRADES_FILE,
        (
            f"🔥 PAPER ENTRY | "
            f"{t['symbol']} | "
            f"price=${entry:.12f} | "
            f"score={score} | "
            f"stake=${PAPER_TRADE_SIZE:.2f} | "
            f"source={t['source']}"
        )
    )

    return True


# ============================================================
# CLOSE TRADE
# ============================================================

def close_trade(state, address, current_price, reason):

    trade = state["open_trades"].get(address)

    if not trade:
        return

    entry = trade["entry_price"]

    if entry <= 0:
        return

    multiple = current_price / entry

    pnl_pct = multiple - 1

    pnl = trade["stake"] * pnl_pct

    returned_value = trade["stake"] + pnl

    state["balance"] += returned_value

    duration = time.time() - trade["entry_time"]

    max_multiple = (
        trade["highest_price"] / entry
        if entry > 0
        else 1
    )

    result = {
        **trade,

        "exit_price": current_price,

        "pnl": pnl,

        "pnl_pct": pnl_pct,

        "multiple": multiple,

        "max_multiple": max_multiple,

        "duration_seconds": duration,

        "exit_time": time.time(),

        "reason": reason
    }

    state["closed_trades"].append(result)

    del state["open_trades"][address]

    state["cooldowns"][address] = (
        time.time() + COOLDOWN_SECONDS
    )

    log(
        TRADES_FILE,
        (
            f"{'🟢 WIN' if pnl >= 0 else '🔴 LOSS'} | "
            f"{trade['symbol']} | "
            f"entry=${entry:.12f} | "
            f"exit=${current_price:.12f} | "
            f"P/L={pnl_pct * 100:+.2f}% | "
            f"multiple={multiple:.2f}x | "
            f"MAX={max_multiple:.2f}x | "
            f"duration={duration / 60:.1f}m | "
            f"reason={reason}"
        )
    )


# ============================================================
# UPDATE OPEN TRADES
# ============================================================

def update_open_trades(state, market_data):

    for address, trade in list(
        state["open_trades"].items()
    ):

        t = market_data.get(address)

        if not t:
            continue

        price = t["price"]

        if price <= 0:
            continue

        entry = trade["entry_price"]

        trade["highest_price"] = max(
            trade["highest_price"],
            price
        )

        trade["lowest_price"] = min(
            trade["lowest_price"],
            price
        )

        multiple = price / entry

        pnl_pct = multiple - 1

        # ----------------------------------------------------
        # PROTECTIVE STOP
        # ----------------------------------------------------

        if pnl_pct <= STOP_LOSS:

            close_trade(
                state,
                address,
                price,
                "protective stop"
            )

            continue

        # ----------------------------------------------------
        # LET WINNERS RUN
        # ----------------------------------------------------

        if pnl_pct >= TRAIL_START:

            high = trade["highest_price"]

            drawdown_from_high = (
                price / high
            ) - 1

            if drawdown_from_high <= -TRAIL_DISTANCE:

                close_trade(
                    state,
                    address,
                    price,
                    "trailing exit"
                )

                continue

        # ----------------------------------------------------
        # MAX HOLD
        # ----------------------------------------------------

        age = time.time() - trade["entry_time"]

        if age >= MAX_HOLD_SECONDS:

            close_trade(
                state,
                address,
                price,
                "maximum holding time"
            )


# ============================================================
# STATS
# ============================================================

def write_stats(state):

    closed = state["closed_trades"]

    wins = [
        x for x in closed
        if x["pnl"] > 0
    ]

    losses = [
        x for x in closed
        if x["pnl"] < 0
    ]

    realized = sum(
        x["pnl"] for x in closed
    )

    total = len(closed)

    win_rate = (
        len(wins) / total * 100
        if total
        else 0
    )

    best_multiple = max(
        [x.get("max_multiple", 1) for x in closed],
        default=1
    )

    best_pnl = max(
        [x["pnl_pct"] for x in closed],
        default=0
    )

    worst_pnl = min(
        [x["pnl_pct"] for x in closed],
        default=0
    )

    lines = [
        "========================================",
        "       ALVIN MEME GOD V5 STATS",
        "========================================",
        f"Time: {now()}",
        f"Balance: ${state['balance']:.2f}",
        f"Open trades: {len(state['open_trades'])}",
        f"Closed trades: {total}",
        f"Wins: {len(wins)}",
        f"Losses: {len(losses)}",
        f"Win rate: {win_rate:.2f}%",
        f"Realized P/L: ${realized:+.2f}",
        f"Best trade: {best_pnl * 100:+.2f}%",
        f"Worst trade: {worst_pnl * 100:+.2f}%",
        f"Best maximum multiple: {best_multiple:.2f}x",
        f"Watchlist: {len(state['watchlist'])}",
        "========================================"
    ]

    with open(
        STATS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines) + "\n"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    ensure_files()

    state = load_state()

    print()
    print("==========================================")
    print("       ALVIN MEME GOD V5")
    print(" ACTIVE MOMENTUM PAPER TRADER")
    print("==========================================")
    print(f"Paper balance: ${state['balance']:.2f}")
    print(f"Trade size: ${PAPER_TRADE_SIZE:.2f}")
    print(f"Max open trades: {MAX_OPEN_TRADES}")
    print(f"Entry score: {ENTRY_SCORE}")
    print("Fixed TP: DISABLED")
    print("Trailing runner: ENABLED")
    print("Real-money trading: DISABLED")
    print("==========================================")
    print()

    while True:

        try:

            cycle_start = time.time()

            addresses = discover()

            market_data = {}

            print(
                f"\n[{now()}] "
                f"Scanning {len(addresses)} tokens..."
            )

            for address in addresses:

                pair = get_best_pair(address)

                if not pair:
                    continue

                source = "TRENDING"

                t = normalize(
                    pair,
                    address,
                    source
                )

                previous = state["observations"].get(
                    address
                )

                score = calculate_score(
                    t,
                    previous
                )

                market_data[address] = t

                # --------------------------------------------
                # WATCHLIST
                # --------------------------------------------

                if score >= WATCH_SCORE:

                    state["watchlist"][address] = {
                        "symbol": t["symbol"],
                        "score": score,
                        "price": t["price"],
                        "updated": time.time()
                    }

                # --------------------------------------------
                # ENTRY
                # --------------------------------------------

                if score >= ENTRY_SCORE:

                    confirmed, reason = entry_confirmation(
                        t,
                        previous
                    )

                    if confirmed:

                        opened = open_trade(
                            state,
                            t,
                            score
                        )

                        if opened:

                            print(
                                f"🔥 ENTRY "
                                f"{t['symbol']} "
                                f"score={score}"
                            )

                    else:

                        log(
                            TARGETS_FILE,
                            (
                                f"⚠ WAIT | "
                                f"{t['symbol']} | "
                                f"score={score} | "
                                f"{reason}"
                            )
                        )

                elif score >= WATCH_SCORE:

                    log(
                        TARGETS_FILE,
                        (
                            f"👀 WATCH | "
                            f"{t['symbol']} | "
                            f"score={score} | "
                            f"5m={t['change_5m']:+.2f}% | "
                            f"BP={t['buy_pressure'] * 100:.1f}%"
                        )
                    )

                # Save observation
                state["observations"][address] = {
                    "change_5m": t["change_5m"],
                    "buy_pressure": t["buy_pressure"],
                    "volume_5m": t["volume_5m"],
                    "price": t["price"],
                    "time": time.time()
                }

                time.sleep(0.20)

            # --------------------------------------------
            # UPDATE OPEN TRADES
            # --------------------------------------------

            update_open_trades(
                state,
                market_data
            )

            # --------------------------------------------
            # CLEAN OLD WATCHLIST
            # --------------------------------------------

            cutoff = time.time() - 3600

            state["watchlist"] = {
                k: v
                for k, v in state["watchlist"].items()
                if v.get("updated", 0) >= cutoff
            }

            # --------------------------------------------
            # CLEAN OLD COOLDOWNS
            # --------------------------------------------

            state["cooldowns"] = {
                k: v
                for k, v in state["cooldowns"].items()
                if v > time.time()
            }

            save_state(state)
            write_stats(state)

            elapsed = time.time() - cycle_start

            print(
                f"[{now()}] "
                f"Balance=${state['balance']:.2f} | "
                f"Open={len(state['open_trades'])} | "
                f"Closed={len(state['closed_trades'])} | "
                f"Next scan in {max(1, SCAN_INTERVAL - int(elapsed))}s"
            )

            time.sleep(
                max(
                    1,
                    SCAN_INTERVAL - elapsed
                )
            )

        except KeyboardInterrupt:

            print("\nBot stopped.")

            save_state(state)
            write_stats(state)

            break

        except Exception as e:

            print(
                f"[{now()}] MAIN ERROR: {e}"
            )

            time.sleep(10)


if __name__ == "__main__":
    main()
