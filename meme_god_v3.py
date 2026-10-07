import requests
import time
import json
import os
from datetime import datetime, timezone

# ============================================================
# ALVIN MEME COIN GOD V3
# LIVE DISCOVERY + AUTOMATIC PAPER TRADING + LOGGING
# ============================================================

API_BASE = "https://api.dexscreener.com"

SCAN_INTERVAL = 30

STARTING_BALANCE = 100.00
TRADE_SIZE = 10.00

MIN_SCORE = 75
MAX_OPEN_TRADES = 5

MIN_LIQUIDITY = 10_000
MIN_VOLUME_5M = 1_000

TAKE_PROFIT = 0.30
STOP_LOSS = -0.15

# ------------------------------------------------------------
# FILES
# ------------------------------------------------------------

TARGET_LOG = "MEME_GOD_TARGETS.txt"
TRADE_LOG = "MEME_GOD_TRADES.txt"
STATS_LOG = "MEME_GOD_STATS.txt"
STATE_FILE = "MEME_GOD_STATE.json"

# ------------------------------------------------------------
# STATE
# ------------------------------------------------------------

balance = STARTING_BALANCE
open_trades = {}
closed_trades = []
seen_tokens = set()


# ============================================================
# TIME
# ============================================================

def now():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# FILE LOGGING
# ============================================================

def write_log(filename, text):
    try:
        with open(
            filename,
            "a",
            encoding="utf-8"
        ) as f:
            f.write(text)
            f.write("\n")

    except Exception as e:
        print("[LOG ERROR]", filename, e)


def save_state():

    data = {
        "balance": balance,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "seen_tokens": list(seen_tokens)
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
        print("[STATE ERROR]", e)


def load_state():

    global balance
    global open_trades
    global closed_trades
    global seen_tokens

    if not os.path.exists(STATE_FILE):
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

        seen_tokens = set(
            data.get(
                "seen_tokens",
                []
            )
        )

    except Exception as e:

        print(
            "[STATE LOAD ERROR]",
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
                "ALVIN-MEME-GOD/3.0"
            }
        )

        if response.status_code != 200:
            print(
                "[HTTP]",
                response.status_code,
                url
            )
            return None

        return response.json()

    except Exception as e:

        print(
            "[NETWORK ERROR]",
            e
        )

        return None


# ============================================================
# DISCOVER NEW SOLANA TOKENS
# ============================================================

def discover_tokens():

    url = (
        API_BASE
        + "/token-profiles/latest/v1"
    )

    data = get_json(url)

    if not data:
        return []

    if isinstance(data, dict):

        data = data.get(
            "tokens",
            []
        )

    if not isinstance(data, list):
        return []

    results = []

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

        if not address:
            continue

        results.append(
            {
                "address": address,
                "url": item.get(
                    "url",
                    ""
                ),
                "description": item.get(
                    "description",
                    ""
                )
            }
        )

    return results


# ============================================================
# GET PAIRS
# ============================================================

def get_pairs(address):

    url = (
        API_BASE
        + "/token-pairs/v1/solana/"
        + address
    )

    data = get_json(url)

    if not data:
        return []

    if isinstance(data, dict):

        data = data.get(
            "pairs",
            []
        )

    if not isinstance(data, list):
        return []

    return data


# ============================================================
# BEST PAIR
# ============================================================

def best_pair(pairs):

    if not pairs:
        return None

    solana = [
        p for p in pairs
        if p.get(
            "chainId"
        ) == "solana"
    ]

    if not solana:
        return None

    return max(
        solana,
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
# NORMALIZE MARKET DATA
# ============================================================

def normalize(pair):

    if not pair:
        return None

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

    price_change = (
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
                price_change.get(
                    "m5"
                )
                or 0
            ),

        "change1h":
            float(
                price_change.get(
                    "h1"
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
# TOKEN AGE
# ============================================================

def age_minutes(timestamp):

    if not timestamp:
        return 999999

    try:

        created = (
            float(timestamp)
            / 1000
        )

        return max(
            0,
            (
                time.time()
                - created
            ) / 60
        )

    except:

        return 999999


# ============================================================
# SCORE
# ============================================================

def score_token(t):

    score = 0
    reasons = []

    liquidity = t[
        "liquidity"
    ]

    market_cap = t[
        "market_cap"
    ]

    volume = t[
        "volume5m"
    ]

    # --------------------------------------------------------
    # LIQUIDITY
    # --------------------------------------------------------

    if liquidity >= 50_000:

        score += 20

        reasons.append(
            "+20 strong liquidity"
        )

    elif liquidity >= 25_000:

        score += 15

        reasons.append(
            "+15 good liquidity"
        )

    elif liquidity >= MIN_LIQUIDITY:

        score += 8

        reasons.append(
            "+8 acceptable liquidity"
        )

    else:

        score -= 20

        reasons.append(
            "-20 poor liquidity"
        )

    # --------------------------------------------------------
    # LIQUIDITY / MC
    # --------------------------------------------------------

    if market_cap > 0:

        ratio = (
            liquidity
            / market_cap
        )

        if ratio >= 0.20:

            score += 15

            reasons.append(
                "+15 healthy liquidity/MC"
            )

        elif ratio >= 0.10:

            score += 8

            reasons.append(
                "+8 acceptable liquidity/MC"
            )

        else:

            score -= 5

            reasons.append(
                "-5 low liquidity/MC"
            )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    if volume >= 50_000:

        score += 20

        reasons.append(
            "+20 strong volume"
        )

    elif volume >= 10_000:

        score += 15

        reasons.append(
            "+15 good volume"
        )

    elif volume >= MIN_VOLUME_5M:

        score += 7

        reasons.append(
            "+7 active market"
        )

    else:

        score -= 10

        reasons.append(
            "-10 weak volume"
        )

    # --------------------------------------------------------
    # BUY/SELL PRESSURE
    # --------------------------------------------------------

    buys = t[
        "buys5m"
    ]

    sells = t[
        "sells5m"
    ]

    total = buys + sells

    if total > 0:

        buy_ratio = (
            buys / total
        )

        if buy_ratio >= 0.65:

            score += 15

            reasons.append(
                "+15 strong buy pressure"
            )

        elif buy_ratio >= 0.55:

            score += 8

            reasons.append(
                "+8 positive buy pressure"
            )

        elif buy_ratio < 0.40:

            score -= 15

            reasons.append(
                "-15 heavy selling"
            )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    change = t[
        "change5m"
    ]

    if 3 <= change <= 25:

        score += 10

        reasons.append(
            "+10 healthy momentum"
        )

    elif change > 50:

        score -= 15

        reasons.append(
            "-15 possible overextension"
        )

    elif change < -10:

        score -= 10

        reasons.append(
            "-10 negative momentum"
        )

    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    age = age_minutes(
        t["created"]
    )

    if 2 <= age <= 30:

        score += 10

        reasons.append(
            "+10 early token"
        )

    elif age < 2:

        score += 3

        reasons.append(
            "+3 extremely early"
        )

    elif age > 1440:

        score -= 5

        reasons.append(
            "-5 older token"
        )

    score = max(
        0,
        min(100, score)
    )

    if score >= 85:

        signal = "STRONG PAPER BUY"

    elif score >= MIN_SCORE:

        signal = "PAPER BUY"

    elif score >= 55:

        signal = "WATCH"

    else:

        signal = "SKIP"

    return (
        score,
        signal,
        reasons
    )


# ============================================================
# TARGET LOG
# ============================================================

def log_target(
    token,
    score,
    signal,
    reasons,
    accepted
):

    age = age_minutes(
        token["created"]
    )

    text = "\n" + "=" * 70

    text += (
        "\nALVIN MEME COIN GOD "
        "— TARGET"
    )

    text += (
        "\nTime: "
        + now()
    )

    text += (
        "\n" + "=" * 70
    )

    text += (
        "\nToken: "
        + token["name"]
    )

    text += (
        "\nSymbol: "
        + token["symbol"]
    )

    text += (
        "\nAddress: "
        + str(
            token["address"]
        )
    )

    text += "\n\nMARKET DATA"

    text += (
        "\nPrice: $"
        + f"{token['price']:.10f}"
    )

    text += (
        "\nMarket Cap: $"
        + f"{token['market_cap']:,.0f}"
    )

    text += (
        "\nLiquidity: $"
        + f"{token['liquidity']:,.0f}"
    )

    text += (
        "\n5m Volume: $"
        + f"{token['volume5m']:,.0f}"
    )

    text += (
        "\n1h Volume: $"
        + f"{token['volume1h']:,.0f}"
    )

    text += (
        "\n5m Change: "
        + f"{token['change5m']:.2f}%"
    )

    text += (
        "\n1h Change: "
        + f"{token['change1h']:.2f}%"
    )

    text += (
        "\nBuys: "
        + str(token["buys5m"])
    )

    text += (
        "\nSells: "
        + str(token["sells5m"])
    )

    text += (
        "\nAge: "
        + f"{age:.2f} minutes"
    )

    text += "\n\nSCORING"

    text += (
        "\nGod Score: "
        + str(score)
        + "/100"
    )

    text += (
        "\nSignal: "
        + signal
    )

    text += (
        "\nAccepted: "
        + str(accepted)
    )

    text += "\nReasons:"

    for reason in reasons:

        text += (
            "\n  "
            + reason
        )

    if token["url"]:

        text += (
            "\n\nChart: "
            + token["url"]
        )

    write_log(
        TARGET_LOG,
        text
    )


# ============================================================
# OPEN PAPER TRADE
# ============================================================

def open_trade(
    token,
    score
):

    global balance

    address = token[
        "address"
    ]

    if address in open_trades:
        return False

    if len(open_trades) >= MAX_OPEN_TRADES:

        print(
            "Maximum open trades reached."
        )

        return False

    if balance < TRADE_SIZE:

        print(
            "Insufficient paper balance."
        )

        return False

    if token["price"] <= 0:
        return False

    trade = {

        "address":
            address,

        "symbol":
            token["symbol"],

        "name":
            token["name"],

        "entry":
            token["price"],

        "current":
            token["price"],

        "stake":
            TRADE_SIZE,

        "score":
            score,

        "opened":
            now()
    }

    balance -= TRADE_SIZE

    open_trades[
        address
    ] = trade

    text = "\n" + "=" * 70

    text += (
        "\nPAPER ENTRY"
    )

    text += (
        "\nTime: "
        + now()
    )

    text += (
        "\nToken: "
        + token["name"]
    )

    text += (
        "\nSymbol: "
        + token["symbol"]
    )

    text += (
        "\nAddress: "
        + address
    )

    text += (
        "\nEntry Price: $"
        + f"{token['price']:.10f}"
    )

    text += (
        "\nVirtual Stake: $"
        + f"{TRADE_SIZE:.2f}"
    )

    text += (
        "\nGod Score: "
        + str(score)
    )

    text += (
        "\nTake Profit: +"
        + f"{TAKE_PROFIT * 100:.0f}%"
    )

    text += (
        "\nStop Loss: "
        + f"{STOP_LOSS * 100:.0f}%"
    )

    text += (
        "\nStatus: OPEN"
    )

    write_log(
        TRADE_LOG,
        text
    )

    print(
        "\n🟢 PAPER ENTRY:",
        token["symbol"],
        "| Score:",
        score
    )

    return True


# ============================================================
# CLOSE PAPER TRADE
# ============================================================

def close_trade(
    address,
    reason,
    exit_price,
    pnl
):

    global balance

    trade = open_trades.pop(
        address,
        None
    )

    if not trade:
        return

    returned = (
        trade["stake"]
        + pnl
    )

    balance += max(
        0,
        returned
    )

    trade["exit"] = exit_price
    trade["pnl"] = pnl
    trade["result"] = reason
    trade["closed"] = now()

    closed_trades.append(
        trade
    )

    text = "\n" + "=" * 70

    text += (
        "\nPAPER EXIT"
    )

    text += (
        "\nTime: "
        + now()
    )

    text += (
        "\nToken: "
        + trade["name"]
    )

    text += (
        "\nSymbol: "
        + trade["symbol"]
    )

    text += (
        "\nEntry: $"
        + f"{trade['entry']:.10f}"
    )

    text += (
        "\nExit: $"
        + f"{exit_price:.10f}"
    )

    text += (
        "\nP/L: $"
        + f"{pnl:.2f}"
    )

    text += (
        "\nResult: "
        + reason
    )

    text += (
        "\nScore at Entry: "
        + str(trade["score"])
    )

    text += (
        "\nStatus: CLOSED"
    )

    write_log(
        TRADE_LOG,
        text
    )

    print(
        "\n🏁 PAPER EXIT:",
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

        try:

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

            if token["price"] <= 0:
                continue

            trade = open_trades[
                address
            ]

            entry = trade[
                "entry"
            ]

            current = token[
                "price"
            ]

            change = (
                current - entry
            ) / entry

            pnl = (
                trade["stake"]
                * change
            )

            print(
                f"📊 {trade['symbol']} "
                f"{change * 100:.2f}% "
                f"${pnl:.2f}"
            )

            if change >= TAKE_PROFIT:

                close_trade(
                    address,
                    "TAKE PROFIT",
                    current,
                    pnl
                )

            elif change <= STOP_LOSS:

                close_trade(
                    address,
                    "STOP LOSS",
                    current,
                    pnl
                )

        except Exception as e:

            print(
                "[UPDATE ERROR]",
                e
            )


# ============================================================
# STATS
# ============================================================

def write_stats():

    wins = sum(
        1
        for x in closed_trades
        if x.get("pnl", 0) > 0
    )

    losses = sum(
        1
        for x in closed_trades
        if x.get("pnl", 0) <= 0
    )

    total_pnl = sum(
        x.get("pnl", 0)
        for x in closed_trades
    )

    total = len(
        closed_trades
    )

    win_rate = (
        wins / total * 100
        if total
        else 0
    )

    avg_win = 0

    avg_loss = 0

    winning = [
        x["pnl"]
        for x in closed_trades
        if x.get("pnl", 0) > 0
    ]

    losing = [
        x["pnl"]
        for x in closed_trades
        if x.get("pnl", 0) <= 0
    ]

    if winning:
        avg_win = (
            sum(winning)
            / len(winning)
        )

    if losing:
        avg_loss = (
            sum(losing)
            / len(losing)
        )

    text = "\n" + "=" * 70

    text += (
        "\nALVIN MEME COIN GOD "
        "— STATISTICS"
    )

    text += (
        "\nGenerated: "
        + now()
    )

    text += (
        "\n" + "=" * 70
    )

    text += (
        "\nStarting Balance: $"
        + f"{STARTING_BALANCE:.2f}"
    )

    text += (
        "\nCurrent Cash: $"
        + f"{balance:.2f}"
    )

    text += (
        "\nOpen Trades: "
        + str(
            len(open_trades)
        )
    )

    text += (
        "\nClosed Trades: "
        + str(total)
    )

    text += (
        "\nWins: "
        + str(wins)
    )

    text += (
        "\nLosses: "
        + str(losses)
    )

    text += (
        "\nWin Rate: "
        + f"{win_rate:.2f}%"
    )

    text += (
        "\nTotal Realized P/L: $"
        + f"{total_pnl:.2f}"
    )

    text += (
        "\nAverage Win: $"
        + f"{avg_win:.2f}"
    )

    text += (
        "\nAverage Loss: $"
        + f"{avg_loss:.2f}"
    )

    write_log(
        STATS_LOG,
        text
    )


# ============================================================
# AUTOMATIC ENGINE
# ============================================================

def run_bot():

    print(
        "\n=========================================="
    )

    print(
        " ALVIN MEME COIN GOD V3"
    )

    print(
        " LIVE DISCOVERY / PAPER TRADING"
    )

    print(
        "=========================================="
    )

    print(
        "\nStarting balance: $"
        + f"{balance:.2f}"
    )

    while True:

        try:

            print(
                "\n"
                + "=" * 70
            )

            print(
                "SCAN:",
                now()
            )

            candidates = (
                discover_tokens()
            )

            print(
                "Candidates:",
                len(candidates)
            )

            for item in candidates:

                address = item[
                    "address"
                ]

                if address in seen_tokens:

                    continue

                seen_tokens.add(
                    address
                )

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

                # Basic liquidity filter
                if (
                    token["liquidity"]
                    < MIN_LIQUIDITY
                ):

                    continue

                score, signal, reasons = (
                    score_token(
                        token
                    )
                )

                accepted = (
                    score >= MIN_SCORE
                )

                log_target(
                    token,
                    score,
                    signal,
                    reasons,
                    accepted
                )

                print(
                    token["symbol"],
                    "| Score:",
                    score,
                    "|",
                    signal
                )

                if accepted:

                    open_trade(
                        token,
                        score
                    )

                # Small delay
                time.sleep(0.25)

            # Update positions
            update_trades()

            # Save stats
            write_stats()

            # Save state
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
                "Waiting",
                SCAN_INTERVAL,
                "seconds..."
            )

            time.sleep(
                SCAN_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\n\nBot stopped."
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

    load_state()

    run_bot()
