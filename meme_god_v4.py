import requests
import time
import json
import os
from datetime import datetime

# ============================================================
# ALVIN MEME GOD V4
#
# MARKET SCANNER + TRENDING TOKEN ENGINE
# PAPER TRADING ONLY
# ============================================================

API = "https://api.dexscreener.com"

SCAN_INTERVAL = 5

STARTING_BALANCE = 100.0
PAPER_TRADE_SIZE = 10.0

MAX_OPEN_TRADES = 5

# Entry thresholds
ENTRY_SCORE = 82
WATCH_SCORE = 70

MIN_LIQUIDITY = 15000
MIN_VOLUME_5M = 2000

TAKE_PROFIT = 0.30
STOP_LOSS = -0.15

# Pullback/recovery model
PULLBACK_MIN = -2.0
RECOVERY_MIN = 1.0

# Files
TARGETS_FILE = "MEME_GOD_TARGETS.txt"
TRADES_FILE = "MEME_GOD_TRADES.txt"
STATS_FILE = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_STATE.json"


# ============================================================
# GLOBAL STATE
# ============================================================

balance = STARTING_BALANCE

open_trades = {}
closed_trades = []

watchlist = {}

seen_tokens = set()


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# LOGGING
# ============================================================

def ensure_files():

    for filename in [
        TARGETS_FILE,
        TRADES_FILE,
        STATS_FILE
    ]:

        if not os.path.exists(filename):

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    "ALVIN MEME GOD V4\n"
                )


def log(filename, text):

    with open(
        filename,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            text + "\n"
        )


# ============================================================
# STATE
# ============================================================

def save_state():

    data = {
        "balance": balance,
        "open_trades": open_trades,
        "closed_trades": closed_trades[-200:],
        "watchlist": watchlist,
        "seen_tokens": list(seen_tokens)[-5000:]
    }

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2
            )

    except Exception as e:

        print(
            "STATE SAVE ERROR:",
            e
        )


def load_state():

    global balance
    global open_trades
    global closed_trades
    global watchlist
    global seen_tokens

    if not os.path.exists(
        STATE_FILE
    ):

        return

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        balance = data.get(
            "balance",
            STARTING_BALANCE
        )

        open_trades = data.get(
            "open_trades",
            {}
        )

        closed_trades = data.get(
            "closed_trades",
            []
        )

        watchlist = data.get(
            "watchlist",
            {}
        )

        seen_tokens = set(
            data.get(
                "seen_tokens",
                []
            )
        )

    except Exception as e:

        print(
            "STATE LOAD ERROR:",
            e
        )


# ============================================================
# HTTP
# ============================================================

def get_json(url):

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent":
                "ALVIN-MEME-GOD-V4"
            }
        )

        if response.status_code == 429:

            print(
                "API RATE LIMIT - WAITING"
            )

            time.sleep(20)

            return None

        if response.status_code != 200:

            print(
                "HTTP ERROR:",
                response.status_code
            )

            return None

        return response.json()

    except Exception as e:

        print(
            "NETWORK ERROR:",
            e
        )

        return None


# ============================================================
# DISCOVERY
# ============================================================

def discover_profiles():

    url = (
        API
        + "/token-profiles/latest/v1"
    )

    data = get_json(url)

    if not isinstance(
        data,
        list
    ):

        return []

    return [
        x for x in data
        if isinstance(x, dict)
        and x.get("chainId")
        == "solana"
        and x.get("tokenAddress")
    ]


def discover_boosted():

    urls = [

        API
        + "/token-boosts/latest/v1",

        API
        + "/token-boosts/top/v1"
    ]

    results = []

    for url in urls:

        data = get_json(url)

        if isinstance(
            data,
            list
        ):

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):

                    continue

                if item.get(
                    "chainId"
                ) != "solana":

                    continue

                address = item.get(
                    "tokenAddress"
                )

                if address:

                    results.append(
                        {
                            "address":
                                address,

                            "source":
                                "TRENDING"
                        }
                    )

    return results


# ============================================================
# TOKEN PAIRS
# ============================================================

def get_pairs(address):

    url = (
        API
        + "/token-pairs/v1/solana/"
        + address
    )

    data = get_json(url)

    if isinstance(
        data,
        list
    ):

        return data

    if isinstance(
        data,
        dict
    ):

        return data.get(
            "pairs",
            []
        )

    return []


# ============================================================
# BEST PAIR
# ============================================================

def best_pair(pairs):

    if not pairs:

        return None

    solana_pairs = [
        p for p in pairs
        if p.get("chainId")
        == "solana"
    ]

    if not solana_pairs:

        return None

    return max(
        solana_pairs,
        key=lambda p:
        float(
            (
                p.get(
                    "liquidity"
                )
                or {}
            ).get(
                "usd",
                0
            )
            or 0
        )
    )


# ============================================================
# NORMALIZE
# ============================================================

def normalize(pair):

    base = (
        pair.get(
            "baseToken"
        )
        or {}
    )

    liquidity = (
        pair.get(
            "liquidity"
        )
        or {}
    )

    volume = (
        pair.get(
            "volume"
        )
        or {}
    )

    txns = (
        pair.get(
            "txns"
        )
        or {}
    )

    change = (
        pair.get(
            "priceChange"
        )
        or {}
    )

    return {

        "address":
            base.get(
                "address"
            ),

        "symbol":
            base.get(
                "symbol",
                "UNKNOWN"
            ),

        "name":
            base.get(
                "name",
                "Unknown"
            ),

        "price":
            float(
                pair.get(
                    "priceUsd"
                )
                or 0
            ),

        "market_cap":
            float(
                pair.get(
                    "marketCap"
                )
                or pair.get(
                    "fdv"
                )
                or 0
            ),

        "liquidity":
            float(
                liquidity.get(
                    "usd"
                )
                or 0
            ),

        "volume5m":
            float(
                volume.get(
                    "m5"
                )
                or 0
            ),

        "volume1h":
            float(
                volume.get(
                    "h1"
                )
                or 0
            ),

        "buys5m":
            int(
                (
                    txns.get(
                        "m5"
                    )
                    or {}
                ).get(
                    "buys",
                    0
                )
                or 0
            ),

        "sells5m":
            int(
                (
                    txns.get(
                        "m5"
                    )
                    or {}
                ).get(
                    "sells",
                    0
                )
                or 0
            ),

        "change5m":
            float(
                change.get(
                    "m5"
                )
                or 0
            ),

        "change1h":
            float(
                change.get(
                    "h1"
                )
                or 0
            ),

        "change6h":
            float(
                change.get(
                    "h6"
                )
                or 0
            ),

        "change24h":
            float(
                change.get(
                    "h24"
                )
                or 0
            ),

        "created":
            pair.get(
                "pairCreatedAt"
            ),

        "url":
            pair.get(
                "url",
                ""
            )
    }


# ============================================================
# BUY PRESSURE
# ============================================================

def buy_ratio(token):

    buys = token[
        "buys5m"
    ]

    sells = token[
        "sells5m"
    ]

    total = buys + sells

    if total == 0:

        return 0.5

    return buys / total


# ============================================================
# TREND SCORE
# ============================================================

def calculate_score(
    token,
    source="TRENDING"
):

    score = 0

    reasons = []

    liquidity = token[
        "liquidity"
    ]

    volume5m = token[
        "volume5m"
    ]

    volume1h = token[
        "volume1h"
    ]

    change5m = token[
        "change5m"
    ]

    change1h = token[
        "change1h"
    ]

    change6h = token[
        "change6h"
    ]

    market_cap = token[
        "market_cap"
    ]

    pressure = buy_ratio(
        token
    )

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 100000:

        score += 15
        reasons.append(
            "+15 very strong liquidity"
        )

    elif liquidity >= 50000:

        score += 12
        reasons.append(
            "+12 strong liquidity"
        )

    elif liquidity >= MIN_LIQUIDITY:

        score += 7
        reasons.append(
            "+7 acceptable liquidity"
        )

    else:

        score -= 15
        reasons.append(
            "-15 weak liquidity"
        )

    # --------------------------------------------------------
    # 5M VOLUME
    # --------------------------------------------------------

    if volume5m >= 100000:

        score += 20
        reasons.append(
            "+20 exceptional 5m volume"
        )

    elif volume5m >= 25000:

        score += 15
        reasons.append(
            "+15 strong 5m volume"
        )

    elif volume5m >= MIN_VOLUME_5M:

        score += 8
        reasons.append(
            "+8 active 5m volume"
        )

    else:

        score -= 10
        reasons.append(
            "-10 weak 5m volume"
        )

    # --------------------------------------------------------
    # 1H VOLUME
    # --------------------------------------------------------

    if volume1h >= 500000:

        score += 10
        reasons.append(
            "+10 strong 1h volume"
        )

    elif volume1h >= 100000:

        score += 7
        reasons.append(
            "+7 good 1h volume"
        )

    # --------------------------------------------------------
    # BUY PRESSURE
    # --------------------------------------------------------

    if pressure >= 0.70:

        score += 20
        reasons.append(
            "+20 very strong buying"
        )

    elif pressure >= 0.60:

        score += 15
        reasons.append(
            "+15 strong buying"
        )

    elif pressure >= 0.55:

        score += 8
        reasons.append(
            "+8 positive buying"
        )

    elif pressure < 0.40:

        score -= 15
        reasons.append(
            "-15 heavy selling"
        )

    # --------------------------------------------------------
    # SHORT-TERM MOMENTUM
    # --------------------------------------------------------

    if 2 <= change5m <= 15:

        score += 12
        reasons.append(
            "+12 healthy 5m momentum"
        )

    elif change5m > 25:

        score -= 10
        reasons.append(
            "-10 possible pump extension"
        )

    elif change5m < -8:

        score -= 10
        reasons.append(
            "-10 negative 5m momentum"
        )

    # --------------------------------------------------------
    # 1H TREND
    # --------------------------------------------------------

    if change1h >= 20:

        score += 12
        reasons.append(
            "+12 strong 1h trend"
        )

    elif change1h >= 10:

        score += 8
        reasons.append(
            "+8 positive 1h trend"
        )

    elif change1h < -10:

        score -= 10
        reasons.append(
            "-10 negative 1h trend"
        )

    # --------------------------------------------------------
    # 6H TREND
    # --------------------------------------------------------

    if change6h > 20:

        score += 5
        reasons.append(
            "+5 broader trend"
        )

    # --------------------------------------------------------
    # LIQUIDITY / MARKET CAP
    # --------------------------------------------------------

    if market_cap > 0:

        ratio = (
            liquidity
            / market_cap
        )

        if ratio >= 0.15:

            score += 6
            reasons.append(
                "+6 healthy liquidity/MC"
            )

        elif ratio < 0.03:

            score -= 6
            reasons.append(
                "-6 weak liquidity/MC"
            )

    # --------------------------------------------------------
    # TRENDING BONUS
    # --------------------------------------------------------

    if source == "TRENDING":

        score += 5

        reasons.append(
            "+5 trending-market signal"
        )

    return max(
        0,
        min(100, score)
    ), reasons


# ============================================================
# ENTRY CONFIRMATION
# ============================================================

def entry_confirmation(
    token,
    previous
):

    if not previous:

        return False, [
            "No previous observation"
        ]

    reasons = []

    current_change = token[
        "change5m"
    ]

    previous_change = previous.get(
        "change5m",
        0
    )

    pressure = buy_ratio(
        token
    )

    previous_pressure = previous.get(
        "buy_ratio",
        0.5
    )

    # Momentum must be positive
    momentum_ok = (
        current_change > 0
    )

    # Buying pressure must be improving
    pressure_ok = (
        pressure >= 0.55
        and pressure >= previous_pressure
    )

    # Avoid chasing giant instant pumps
    not_overextended = (
        current_change < 20
    )

    # Detect recovery
    recovery = (
        previous_change <= 0
        and current_change >= RECOVERY_MIN
    )

    if momentum_ok:

        reasons.append(
            "positive short-term momentum"
        )

    if pressure_ok:

        reasons.append(
            "buy pressure improving"
        )

    if not_overextended:

        reasons.append(
            "not excessively extended"
        )

    if recovery:

        reasons.append(
            "pullback/recovery detected"
        )

    confirmed = (
        momentum_ok
        and pressure_ok
        and not_overextended
    )

    return confirmed, reasons


# ============================================================
# TARGET LOG
# ============================================================

def log_target(
    token,
    score,
    signal,
    reasons,
    source
):

    pressure = (
        buy_ratio(token)
        * 100
    )

    text = (
        "\n"
        + "=" * 72
        + "\n"
        + "ALVIN MEME GOD V4 TARGET"
        + "\n"
        + "=" * 72
        + "\n"
        + "Time: "
        + now()
        + "\n"
        + "Source: "
        + source
        + "\n"
        + "Name: "
        + token["name"]
        + "\n"
        + "Symbol: "
        + token["symbol"]
        + "\n"
        + "Address: "
        + str(token["address"])
        + "\n"
        + "Price: $"
        + f"{token['price']:.10f}"
        + "\n"
        + "Market Cap: $"
        + f"{token['market_cap']:,.0f}"
        + "\n"
        + "Liquidity: $"
        + f"{token['liquidity']:,.0f}"
        + "\n"
        + "5m Volume: $"
        + f"{token['volume5m']:,.0f}"
        + "\n"
        + "1h Volume: $"
        + f"{token['volume1h']:,.0f}"
        + "\n"
        + "5m Change: "
        + f"{token['change5m']:.2f}%"
        + "\n"
        + "1h Change: "
        + f"{token['change1h']:.2f}%"
        + "\n"
        + "6h Change: "
        + f"{token['change6h']:.2f}%"
        + "\n"
        + "Buy Pressure: "
        + f"{pressure:.1f}%"
        + "\n"
        + "Score: "
        + str(score)
        + "/100"
        + "\n"
        + "Signal: "
        + signal
        + "\n"
        + "Reasons:"
    )

    for reason in reasons:

        text += (
            "\n  "
            + reason
        )

    if token["url"]:

        text += (
            "\nChart: "
            + token["url"]
        )

    log(
        TARGETS_FILE,
        text
    )


# ============================================================
# PAPER ENTRY
# ============================================================

def open_trade(
    token,
    score,
    source
):

    global balance

    address = token[
        "address"
    ]

    if address in open_trades:

        return

    if balance < PAPER_TRADE_SIZE:

        return

    if len(open_trades) >= MAX_OPEN_TRADES:

        return

    entry = token[
        "price"
    ]

    if entry <= 0:

        return

    trade = {

        "address":
            address,

        "symbol":
            token["symbol"],

        "name":
            token["name"],

        "entry":
            entry,

        "stake":
            PAPER_TRADE_SIZE,

        "score":
            score,

        "source":
            source,

        "opened":
            now(),

        "highest":
            entry,

        "lowest":
            entry
    }

    balance -= (
        PAPER_TRADE_SIZE
    )

    open_trades[
        address
    ] = trade

    log(
        TRADES_FILE,
        "\n"
        + "=" * 72
        + "\n"
        + "PAPER ENTRY"
        + "\n"
        + "Time: "
        + now()
        + "\n"
        + "Token: "
        + token["name"]
        + "\n"
        + "Symbol: "
        + token["symbol"]
        + "\n"
        + "Source: "
        + source
        + "\n"
        + "Entry Price: $"
        + f"{entry:.10f}"
        + "\n"
        + "Stake: $"
        + f"{PAPER_TRADE_SIZE:.2f}"
        + "\n"
        + "Score: "
        + str(score)
        + "\n"
        + "TP: +"
        + f"{TAKE_PROFIT * 100:.0f}%"
        + "\n"
        + "SL: "
        + f"{STOP_LOSS * 100:.0f}%"
    )

    print(
        "\n🟢 PAPER ENTRY",
        token["symbol"],
        "Score:",
        score
    )


# ============================================================
# PAPER EXIT
# ============================================================

def close_trade(
    address,
    price,
    reason
):

    global balance

    trade = open_trades.pop(
        address,
        None
    )

    if not trade:

        return

    change = (
        price - trade["entry"]
    ) / trade["entry"]

    pnl = (
        trade["stake"]
        * change
    )

    balance += (
        trade["stake"]
        + pnl
    )

    trade["exit"] = price
    trade["pnl"] = pnl
    trade["result"] = reason
    trade["closed"] = now()

    closed_trades.append(
        trade
    )

    log(
        TRADES_FILE,
        "\n"
        + "=" * 72
        + "\n"
        + "PAPER EXIT"
        + "\n"
        + "Time: "
        + now()
        + "\n"
        + "Token: "
        + trade["name"]
        + "\n"
        + "Symbol: "
        + trade["symbol"]
        + "\n"
        + "Entry: $"
        + f"{trade['entry']:.10f}"
        + "\n"
        + "Exit: $"
        + f"{price:.10f}"
        + "\n"
        + "P/L: $"
        + f"{pnl:.2f}"
        + "\n"
        + "Return: "
        + f"{change * 100:.2f}%"
        + "\n"
        + "Reason: "
        + reason
    )

    print(
        "\n🏁 PAPER EXIT",
        trade["symbol"],
        reason,
        f"${pnl:.2f}"
    )


# ============================================================
# UPDATE OPEN TRADES
# ============================================================

def update_trades():

    for address in list(
        open_trades.keys()
    ):

        pairs = get_pairs(
            address
        )

        pair = best_pair(
            pairs
        )

        if not pair:

            continue

        token = normalize(
            pair
        )

        if not token:

            continue

        price = token[
            "price"
        ]

        if price <= 0:

            continue

        trade = open_trades[
            address
        ]

        trade["highest"] = max(
            trade["highest"],
            price
        )

        trade["lowest"] = min(
            trade["lowest"],
            price
        )

        change = (
            price - trade["entry"]
        ) / trade["entry"]

        pnl = (
            trade["stake"]
            * change
        )

        print(
            f"   {trade['symbol']:<12}"
            f"{change * 100:>8.2f}%"
            f"  ${pnl:>7.2f}"
        )

        if change >= TAKE_PROFIT:

            close_trade(
                address,
                price,
                "TAKE PROFIT"
            )

        elif change <= STOP_LOSS:

            close_trade(
                address,
                price,
                "STOP LOSS"
            )


# ============================================================
# STATS
# ============================================================

def write_stats():

    total = len(
        closed_trades
    )

    wins = [
        x for x in closed_trades
        if x.get("pnl", 0) > 0
    ]

    losses = [
        x for x in closed_trades
        if x.get("pnl", 0) <= 0
    ]

    total_pnl = sum(
        x.get("pnl", 0)
        for x in closed_trades
    )

    win_rate = (
        len(wins)
        / total
        * 100
        if total
        else 0
    )

    best = max(
        (
            x.get("pnl", 0)
            for x in closed_trades
        ),
        default=0
    )

    worst = min(
        (
            x.get("pnl", 0)
            for x in closed_trades
        ),
        default=0
    )

    avg_win = (
        sum(
            x["pnl"]
            for x in wins
        )
        / len(wins)
        if wins
        else 0
    )

    avg_loss = (
        sum(
            x["pnl"]
            for x in losses
        )
        / len(losses)
        if losses
        else 0
    )

    text = (
        "\n"
        + "=" * 72
        + "\n"
        + "ALVIN MEME GOD V4 STATISTICS"
        + "\n"
        + "=" * 72
        + "\n"
        + "Updated: "
        + now()
        + "\n"
        + "Starting Balance: $"
        + f"{STARTING_BALANCE:.2f}"
        + "\n"
        + "Available Balance: $"
        + f"{balance:.2f}"
        + "\n"
        + "Open Trades: "
        + str(len(open_trades))
        + "\n"
        + "Closed Trades: "
        + str(total)
        + "\n"
        + "Wins: "
        + str(len(wins))
        + "\n"
        + "Losses: "
        + str(len(losses))
        + "\n"
        + "Win Rate: "
        + f"{win_rate:.2f}%"
        + "\n"
        + "Realized P/L: $"
        + f"{total_pnl:.2f}"
        + "\n"
        + "Average Win: $"
        + f"{avg_win:.2f}"
        + "\n"
        + "Average Loss: $"
        + f"{avg_loss:.2f}"
        + "\n"
        + "Best Trade: $"
        + f"{best:.2f}"
        + "\n"
        + "Worst Trade: $"
        + f"{worst:.2f}"
        + "\n"
        + "Watchlist: "
        + str(len(watchlist))
    )

    # Append latest stats
    log(
        STATS_FILE,
        text
    )


# ============================================================
# PROCESS TOKEN
# ============================================================

def process_token(
    address,
    source
):

    pairs = get_pairs(
        address
    )

    pair = best_pair(
        pairs
    )

    if not pair:

        return

    token = normalize(
        pair
    )

    if not token:

        return

    if token["price"] <= 0:

        return

    if (
        token["liquidity"]
        < MIN_LIQUIDITY
    ):

        return

    score, reasons = (
        calculate_score(
            token,
            source
        )
    )

    previous = watchlist.get(
        address
    )

    confirmation, confirm_reasons = (
        entry_confirmation(
            token,
            previous
        )
    )

    # Save current observation
    watchlist[address] = {

        "symbol":
            token["symbol"],

        "price":
            token["price"],

        "change5m":
            token["change5m"],

        "buy_ratio":
            buy_ratio(token),

        "score":
            score,

        "last_seen":
            now(),

        "source":
            source
    }

    # --------------------------------------------------------
    # SIGNAL
    # --------------------------------------------------------

    if (
        score >= ENTRY_SCORE
        and confirmation
    ):

        signal = (
            "🔥 PAPER ENTRY CONFIRMED"
        )

        all_reasons = (
            reasons
            + confirm_reasons
        )

        log_target(
            token,
            score,
            signal,
            all_reasons,
            source
        )

        open_trade(
            token,
            score,
            source
        )

        print(
            f"🔥 {token['symbol']}"
            f" | {score}/100"
            f" | ENTRY"
        )

    elif score >= ENTRY_SCORE:

        signal = (
            "⚠ HIGH SCORE - WAITING "
            "FOR CONFIRMATION"
        )

        log_target(
            token,
            score,
            signal,
            reasons
            + confirm_reasons,
            source
        )

        print(
            f"⚠ {token['symbol']}"
            f" | {score}/100"
            f" | WAIT"
        )

    elif score >= WATCH_SCORE:

        signal = "WATCH"

        log_target(
            token,
            score,
            signal,
            reasons,
            source
        )

        print(
            f"👀 {token['symbol']}"
            f" | {score}/100"
            f" | WATCH"
        )


# ============================================================
# MAIN ENGINE
# ============================================================

def run():

    print(
        "\n"
        + "=" * 72
    )

    print(
        " ALVIN MEME GOD V4"
    )

    print(
        " TRENDING + EARLY MARKET SCANNER"
    )

    print(
        " PAPER TRADING ONLY"
    )

    print(
        "=" * 72
    )

    print(
        "\nBalance: $"
        + f"{balance:.2f}"
    )

    while True:

        try:

            print(
                "\n"
                + "=" * 72
            )

            print(
                "SCAN:",
                now()
            )

            # ------------------------------------------------
            # TRENDING
            # ------------------------------------------------

            boosted = (
                discover_boosted()
            )

            print(
                "Trending candidates:",
                len(boosted)
            )

            # ------------------------------------------------
            # NEW / RECENT
            # ------------------------------------------------

            profiles = (
                discover_profiles()
            )

            print(
                "Recent candidates:",
                len(profiles)
            )

            # ------------------------------------------------
            # COMBINE
            # ------------------------------------------------

            candidates = {}

            for item in boosted:

                candidates[
                    item["address"]
                ] = "TRENDING"

            for item in profiles:

                address = item[
                    "tokenAddress"
                ]

                if address not in candidates:

                    candidates[
                        address
                    ] = "EARLY"

            print(
                "Unique candidates:",
                len(candidates)
            )

            # Limit each scan to prevent
            # unnecessary API pressure
            items = list(
                candidates.items()
            )[:25]

            for address, source in items:

                try:

                    process_token(
                        address,
                        source
                    )

                    time.sleep(
                        0.25
                    )

                except Exception as e:

                    print(
                        "TOKEN ERROR:",
                        e
                    )

            # ------------------------------------------------
            # UPDATE TRADES
            # ------------------------------------------------

            if open_trades:

                print(
                    "\nOPEN PAPER TRADES"
                )

                update_trades()

            # ------------------------------------------------
            # STATS / STATE
            # ------------------------------------------------

            write_stats()
            save_state()

            print(
                "\nBalance: $"
                + f"{balance:.2f}"
            )

            print(
                "Open trades:",
                len(open_trades)
            )

            print(
                "Watchlist:",
                len(watchlist)
            )

            print(
                "\nNext scan in",
                SCAN_INTERVAL,
                "seconds..."
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\nBot stopped."
            )

            save_state()
            write_stats()

            break

        except Exception as e:

            print(
                "\nENGINE ERROR:",
                e
            )

            save_state()

            time.sleep(10)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    ensure_files()

    load_state()

    run()
