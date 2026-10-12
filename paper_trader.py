#!/usr/bin/env python3
"""ALVIN MEME GOD — combined paper-trading engine. Simulation only."""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

STATE_FILE = Path.home() / "ALVIN_MEME_GOD_PAPER_STATE.json"
CONFIG_FILE = Path.home() / ".config" / "alvin_meme_god" / "telegram.env"

PAPER_STAKE_USD = 10.0
MAX_OPEN_POSITIONS = 5

# Simulation settings; these are test parameters, not profit guarantees.
STOP_LOSS_PCT = -10.0
TAKE_PROFIT_PCT = 20.0

# Additional requirements for PAPER WATCH entries.
WATCH_MIN_LIQUIDITY = 25_000
WATCH_MIN_VOLUME_5M = 5_000
WATCH_MIN_VOLUME_1H = 15_000
WATCH_MIN_MARKET_SCORE = 60
WATCH_MIN_BUY_PRESSURE = 55
WATCH_MIN_MOMENTUM = 30
WATCH_MIN_COMBINED = 62
WATCH_MIN_EARLY = 55
WATCH_MAX_RISK = 59
WATCH_MAX_FOMO = 79

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def number(obj, *keys, default=0):
    """Read a numeric field safely from a dictionary."""
    if not isinstance(obj, dict):
        return default
    for key in keys:
        try:
            value = obj.get(key)
            if value is not None and value != "":
                return float(value)
        except (TypeError, ValueError):
            continue
    return default


def load_ledger():
    try:
        data = json.loads(STATE_FILE.read_text())
        if isinstance(data, dict):
            data.setdefault("next_id", 1)
            data.setdefault("tokens", {})
            data.setdefault("positions", [])
            data.setdefault("realized_pnl", 0.0)
            return data
    except (OSError, ValueError):
        pass

    return {
        "next_id": 1,
        "tokens": {},
        "positions": [],
        "realized_pnl": 0.0,
    }


def save_ledger(ledger):
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(ledger, indent=2))
    os.replace(temp, STATE_FILE)
    try:
        STATE_FILE.chmod(0o600)
    except OSError:
        pass


def send_telegram(message):
    try:
        config = {}
        for line in CONFIG_FILE.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

        token = config.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = config.get("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            return

        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
        }).encode()

        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()

    except Exception as exc:
        print("Paper Telegram notification failed:", type(exc).__name__)


def watch_candidate_qualifies(item, market):
    """Extra checks for WATCH entries; strict ENTER uses scanner rules."""
    combined = number(item, "combined", "combined_score", default=-1)
    early = number(item, "early", "early_score", default=-1)
    fomo = number(item, "fomo", "fomo_score", default=100)
    risk = number(item, "risk", "risk_score", default=100)

    return (
        combined >= WATCH_MIN_COMBINED
        and early >= WATCH_MIN_EARLY
        and fomo <= WATCH_MAX_FOMO
        and risk <= WATCH_MAX_RISK
        and number(market, "liquidity") >= WATCH_MIN_LIQUIDITY
        and number(market, "volume_5m") >= WATCH_MIN_VOLUME_5M
        and number(market, "volume_1h") >= WATCH_MIN_VOLUME_1H
        and number(market, "market_score") >= WATCH_MIN_MARKET_SCORE
        and number(market, "buy_pressure") >= WATCH_MIN_BUY_PRESSURE
        and number(market, "momentum_score") >= WATCH_MIN_MOMENTUM
    )


def close_position(ledger, position, price, reason, events):
    """Close a simulated position and record its realised P/L."""
    stake = number(position, "stake_usd")
    quantity = number(position, "quantity")
    entry = number(position, "entry_price")

    if price <= 0 or entry <= 0 or quantity <= 0:
        return

    pnl = quantity * price - stake
    pct = (price / entry - 1) * 100

    position["current_price"] = price
    position["exit_price"] = price
    position["exit_at"] = timestamp()
    position["exit_reason"] = reason
    position["realized_pnl"] = round(pnl, 8)
    position["status"] = "CLOSED"

    ledger["realized_pnl"] = (
        number(ledger, "realized_pnl") + pnl
    )

    events.append({
        "type": "EXIT",
        "token_id": position.get("token_id", "N/A"),
        "name": position.get("name", "Unknown"),
        "symbol": position.get("symbol", "N/A"),
        "address": position.get("address", ""),
        "exit_price": price,
        "pnl": pnl,
        "pct": pct,
        "reason": reason,
        "realized_total": ledger["realized_pnl"],
    })


def process_scan(results):
    ledger = load_ledger()
    positions = ledger["positions"]
    events = []

    if not isinstance(results, list):
        print("Paper trader: scan results were not a list.")
        return []

    # Build a price lookup from this scan.
    markets = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        market = item.get("market")
        if isinstance(market, dict):
            address = str(market.get("address", "")).strip()
            if address:
                markets[address] = market

    # Refresh positions and apply simulated exits.
    for position in positions:
        if position.get("status") != "OPEN":
            continue

        market = markets.get(str(position.get("address", "")))
        if not market:
            continue

        price = number(market, "price")
        if price <= 0:
            continue

        position["current_price"] = price
        position["updated_at"] = timestamp()

        entry = number(position, "entry_price")
        if entry <= 0:
            continue

        change_pct = (price / entry - 1) * 100

        if change_pct <= STOP_LOSS_PCT:
            close_position(
                ledger, position, price,
                f"Stop-loss threshold ({STOP_LOSS_PCT:.1f}%)",
                events,
            )
        elif change_pct >= TAKE_PROFIT_PCT:
            close_position(
                ledger, position, price,
                f"Take-profit threshold (+{TAKE_PROFIT_PCT:.1f}%)",
                events,
            )

    # Strict ENTER entries first; qualifying WATCH entries second.
    ranked = []
    for item in results:
        if not isinstance(item, dict):
            continue

        verdict = str(item.get("verdict", "")).strip().upper()
        market = item.get("market")
        if not isinstance(market, dict):
            continue

        if verdict == "PAPER ENTER":
            priority = 0
            strategy = "STRICT ENTER"
        elif verdict == "PAPER WATCH" and watch_candidate_qualifies(
            item, market
        ):
            priority = 1
            strategy = "QUALIFIED WATCH"
        else:
            continue

        ranked.append((priority, item, market, strategy))

    ranked.sort(key=lambda row: row[0])

    for _, item, market, strategy in ranked:
        open_positions = [
            p for p in positions if p.get("status") == "OPEN"
        ]
        if len(open_positions) >= MAX_OPEN_POSITIONS:
            break

        address = str(market.get("address", "")).strip()
        price = number(market, "price")
        if not address or price <= 0:
            continue

        # Do not open a duplicate while the same token is already open.
        if any(
            p.get("address") == address and p.get("status") == "OPEN"
            for p in positions
        ):
            continue

        token_id = ledger["tokens"].get(address)
        if not token_id:
            token_id = f"SOL-{int(ledger['next_id']):06d}"
            ledger["next_id"] = int(ledger["next_id"]) + 1
            ledger["tokens"][address] = token_id

        stake = PAPER_STAKE_USD
        position = {
            "token_id": token_id,
            "name": str(market.get("name", "Unknown")),
            "symbol": str(market.get("symbol", "N/A")),
            "address": address,
            "pair_address": str(market.get("pair_address", "")),
            "strategy": strategy,
            "entry_price": price,
            "current_price": price,
            "stake_usd": stake,
            "quantity": stake / price,
            "entry_at": timestamp(),
            "updated_at": timestamp(),
            "status": "OPEN",
        }

        positions.append(position)
        events.append({
            "type": "ENTRY",
            "position": position.copy(),
            "open_count": len([
                p for p in positions if p.get("status") == "OPEN"
            ]),
        })

    save_ledger(ledger)
    print_dashboard(ledger)

    for event in events:
        if event["type"] == "ENTRY":
            p = event["position"]
            send_telegram(
                "🧠 ALVIN MEME GOD — PAPER ENTRY\n"
                "SIMULATION ONLY — NO REAL TRANSACTION\n\n"
                f"Strategy: {p['strategy']}\n"
                f"Token ID: {p['token_id']}\n"
                f"Name: {p['name']}\n"
                f"Symbol: ${p['symbol']}\n"
                f"Address: {p['address']}\n"
                f"Entry price: ${p['entry_price']:.10g}\n"
                f"Paper stake: ${p['stake_usd']:.2f}\n"
                f"Open positions: {event['open_count']}/{MAX_OPEN_POSITIONS}\n"
                f"Stop-loss: {STOP_LOSS_PCT:.1f}%\n"
                f"Take-profit: +{TAKE_PROFIT_PCT:.1f}%"
            )
        elif event["type"] == "EXIT":
            send_telegram(
                "📊 ALVIN MEME GOD — PAPER EXIT\n"
                "SIMULATION ONLY — NO REAL TRANSACTION\n\n"
                f"Token ID: {event['token_id']}\n"
                f"Name: {event['name']}\n"
                f"Symbol: ${event['symbol']}\n"
                f"Exit reason: {event['reason']}\n"
                f"Exit price: ${event['exit_price']:.10g}\n"
                f"Trade P/L: ${event['pnl']:+.4f} "
                f"({event['pct']:+.2f}%)\n"
                f"Total realised P/L: "
                f"${event['realized_total']:+.4f}"
            )

    return events


def print_dashboard(ledger):
    positions = [
        p for p in ledger["positions"] if p.get("status") == "OPEN"
    ]
    unrealized = 0.0

    print(f"\n{CYAN}{BOLD}{'=' * 64}")
    print("  ALVIN MEME GOD — PAPER TRADING DASHBOARD")
    print(f"{'=' * 64}{RESET}")
    print(f"Mode: {YELLOW}SIMULATION ONLY{RESET}")
    print(f"Open positions: {len(positions)}/{MAX_OPEN_POSITIONS}")
    print("-" * 64)

    if not positions:
        print("No open paper positions yet.")

    for p in positions:
        entry = number(p, "entry_price")
        current = number(p, "current_price", default=entry) or entry
        stake = number(p, "stake_usd")
        quantity = number(p, "quantity")

        pnl = quantity * current - stake
        pct = (current / entry - 1) * 100 if entry > 0 else 0
        unrealized += pnl
        color = GREEN if pnl >= 0 else RED

        print(
            f"\n{CYAN}{p.get('token_id')} | "
            f"{p.get('name')} (${p.get('symbol')}){RESET}"
        )
        print(f"  Strategy: {p.get('strategy', 'STRICT ENTER')}")
        print(f"  Entry: ${entry:.10g} | Current: ${current:.10g}")
        print(f"  Paper stake: ${stake:.2f}")
        print(f"  P/L: {color}${pnl:+.4f} ({pct:+.2f}%){RESET}")

    realized = number(ledger, "realized_pnl")
    open_color = GREEN if unrealized >= 0 else RED
    realized_color = GREEN if realized >= 0 else RED
    allocated = sum(number(p, "stake_usd") for p in positions)

    print("\n" + "-" * 64)
    print(f"Unrealised P/L: {open_color}${unrealized:+.4f}{RESET}")
    print(f"Realised P/L:   {realized_color}${realized:+.4f}{RESET}")
    print(f"Paper capital allocated: ${allocated:.2f}")
    print(f"Stop-loss: {STOP_LOSS_PCT:.1f}% | Take-profit: +{TAKE_PROFIT_PCT:.1f}%")
    print(f"{CYAN}{'=' * 64}{RESET}\n")


if __name__ == "__main__":
    print_dashboard(load_ledger())
