import html
import json
import urllib.parse
import urllib.request
from pathlib import Path


def score_bar(value, width=10):
    value = max(0.0, min(100.0, float(value)))
    filled = round(value / 100 * width)
    return "🟩" * filled + "⬜" * (width - filled) + f" {value:.0f}/100"


def telegram_notify_scan(results, state):
    config_path = (
        Path.home()
        / ".config"
        / "alvin_meme_god"
        / "telegram.env"
    )

    config = {}
    try:
        for line in config_path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    except OSError:
        print("Telegram: configuration file unavailable.")
        return

    token = config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        print("Telegram: token or chat ID missing.")
        return

    ledger_path = (
        Path.home() / "ALVIN_MEME_GOD_V21_TELEGRAM_STATE.json"
    )

    try:
        ledger = json.loads(ledger_path.read_text())
        if not isinstance(ledger, dict):
            ledger = {}
    except (OSError, ValueError):
        ledger = {}

    def send(message):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()

        try:
            request = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(request, timeout=15) as response:
                result = json.load(response)

            if result.get("ok"):
                print("Telegram: alert sent.")
                return True

            print("Telegram: API rejected the message.")
        except Exception as exc:
            print("Telegram delivery failed:", type(exc).__name__)

        return False

    def number(market, *keys):
        for key in keys:
            try:
                return float(market.get(key, 0) or 0)
            except (ValueError, TypeError):
                continue
        return 0.0

    candidates = [
        item for item in results
        if item.get("verdict") in ("PAPER ENTER", "PAPER WATCH")
    ]
    candidates.sort(
        key=lambda item: (
            item.get("verdict") == "PAPER ENTER",
            number({"v": item.get("combined", 0)}, "v"),
        ),
        reverse=True,
    )

    sent = 0

    for item in candidates:
        market = item.get("market", {})
        if not isinstance(market, dict):
            continue

        address = str(market.get("address") or "")
        if not address:
            continue

        verdict = str(item.get("verdict", ""))
        score = number({"v": item.get("combined", 0)}, "v")
        previous = ledger.get(address, {})

        if (
            previous.get("verdict") == verdict
            and abs(score - float(previous.get("score", -100))) < 10
        ):
            continue

        name = html.escape(str(market.get("name", "Unknown token")))
        symbol = html.escape(str(market.get("symbol", "N/A")))
        pair_id = str(
            market.get("pair_id")
            or market.get("pairAddress")
            or market.get("pair_address")
            or ""
        )

        liquidity = number(market, "liquidity", "liquidity_usd")
        vol5 = number(market, "volume_5m", "volume5m")
        vol1h = number(market, "volume_1h", "volume1h")
        buy = number(market, "buy_pressure", "buy_power")
        momentum = number(market, "momentum_score")

        risk_data = item.get("risk", {})
        fomo_data = item.get("fomo", {})

        risk = (
            risk_data.get("score", 0)
            if isinstance(risk_data, dict) else risk_data
        )
        fomo = (
            fomo_data.get("score", 0)
            if isinstance(fomo_data, dict) else fomo_data
        )

        try:
            risk = float(risk or 0)
            fomo = float(fomo or 0)
        except (TypeError, ValueError):
            risk, fomo = 0, 0

        hype = number(item, "hype")
        early = number(item, "early")

        chart = str(
            market.get("url")
            or market.get("pair_url")
            or market.get("urlAddress")
            or ""
        )

        if not (
            chart.startswith("https://")
            and "dexscreener.com/" in chart
        ):
            chart = (
                "https://dexscreener.com/solana/" + pair_id
                if pair_id else ""
            )

        chart_line = (
            '<a href="' + html.escape(chart, quote=True)
            + '">OPEN DEXSCREENER CHART</a>'
            if chart else "Chart link unavailable"
        )

        emoji = "🚀" if verdict == "PAPER ENTER" else "👀"

        message = (
            "🧠 <b>ALVIN MEME GOD AI</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"{emoji} <b>{html.escape(verdict)}</b>\n\n"
            f"🪙 <b>{name} | ${symbol}</b>\n"
            "⛓️ Solana research\n\n"
            "🔑 <b>FULL TOKEN ADDRESS</b>\n"
            f"<code>{html.escape(address)}</code>\n\n"
            "🔗 <b>FULL PAIR ID</b>\n"
            f"<code>{html.escape(pair_id or 'Unavailable')}</code>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📊 <b>MARKET INTELLIGENCE</b>\n"
            f"💧 Liquidity: ${liquidity:,.2f}\n"
            f"📊 5M Volume: ${vol5:,.2f}\n"
            f"📈 1H Volume: ${vol1h:,.2f}\n"
            f"🟢 Buy Pressure: {buy:.1f}%\n"
            f"⚡ Momentum: {score_bar(momentum)}\n\n"
            "🧠 <b>BRAIN ANALYSIS</b>\n"
            f"🌐 Hype: {score_bar(hype)}\n"
            f"🐣 Early Score: {score_bar(early)}\n"
            f"🔥 FOMO: {score_bar(fomo)}\n"
            f"🛡️ Risk: {score_bar(risk)}\n"
            f"🎯 Combined: {score_bar(score)}\n\n"
            f"🌐 {chart_line}\n\n"
            "⚠️ Research and paper simulation only.\n"
            "No real trade has been executed."
        )

        if send(message):
            ledger[address] = {
                "verdict": verdict,
                "score": score,
            }
            sent += 1

            try:
                ledger_path.write_text(json.dumps(ledger, indent=2))
                ledger_path.chmod(0o600)
            except OSError:
                print("Could not save alert history.")

        if sent >= 5:
            break

    # Warn once for each token with a risk score of 80 or higher.
    for item in results:
        risk_data = item.get("risk", {})
        risk = (
            risk_data.get("score", 0)
            if isinstance(risk_data, dict) else risk_data
        )

        try:
            risk = float(risk or 0)
        except (TypeError, ValueError):
            risk = 0

        market = item.get("market", {})
        if risk < 80 or not isinstance(market, dict):
            continue

        address = str(market.get("address") or "")
        if not address:
            continue

        key = address + ":HIGH_RISK"
        if ledger.get(key, {}).get("sent"):
            continue

        message = (
            "🚨 <b>HIGH RISK WARNING</b>\n"
            f"Estimated risk score: {risk:.0f}/100\n"
            "This is a research warning, not a prediction.\n"
            "Paper simulation only."
        )

        if send(message):
            ledger[key] = {"sent": True}
            try:
                ledger_path.write_text(json.dumps(ledger, indent=2))
                ledger_path.chmod(0o600)
            except OSError:
                pass

    scan_number = int(state.get("total_scans", 0))
    summary_key = "_last_summary_scan"

    if scan_number > 0 and scan_number % 6 == 0:
        if ledger.get(summary_key) != scan_number:
            enters = sum(
                item.get("verdict") == "PAPER ENTER"
                for item in results
            )
            watches = sum(
                item.get("verdict") == "PAPER WATCH"
                for item in results
            )

            summary = (
                "🧠 <b>ALVIN MEME GOD — SCAN SUMMARY</b>\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🔎 Tokens analyzed: {len(results)}\n"
                f"🚀 PAPER ENTER candidates: {enters}\n"
                f"👀 PAPER WATCH candidates: {watches}\n"
                f"📊 Scan number: {scan_number}\n\n"
                "⚠️ Paper simulation only. No real trades executed."
            )

            if send(summary):
                ledger[summary_key] = scan_number
                try:
                    ledger_path.write_text(json.dumps(ledger, indent=2))
                    ledger_path.chmod(0o600)
                except OSError:
                    pass
