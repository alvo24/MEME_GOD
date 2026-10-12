#!/usr/bin/env bash
# ALVIN MEME GOD V2.2 — clean reset + sync + launch (paper/research only)
set -Eeuo pipefail

EXPECTED_REPO="alvo24/MEME_GOD"
BOT_FILE="ALVIN_MEME_GOD_V22.py"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
HOME_DIR="${HOME:?HOME is not set}"
SHARED_DIR="$HOME_DIR/storage/shared/Termux"

if [[ -z "$ROOT" || ! -f "$ROOT/$BOT_FILE" ]]; then
  echo "ERROR: Run this from inside your cloned MEME_GOD repository."
  echo "Expected $BOT_FILE in the repository root."
  exit 1
fi

cd "$ROOT"
REMOTE="$(git remote get-url origin 2>/dev/null || true)"
if [[ "$REMOTE" != *"github.com:alvo24/MEME_GOD.git"* && "$REMOTE" != *"github.com/alvo24/MEME_GOD"* ]]; then
  echo "ERROR: Unexpected Git remote: $REMOTE"
  echo "No files were deleted."
  exit 1
fi

echo
echo "======================================================"
echo " ALVIN MEME GOD V2.2 — RESET + SYNC + PAPER SCANNER"
echo "======================================================"
echo "This will permanently clear local scanner history and paper-trade data."
echo "It will remove superseded bot-version scripts from the project/shared"
echo "Termux workspace, sync the current GitHub version, then launch V2.2."
echo
echo "It will PRESERVE: Telegram credentials, SSH keys, unrelated projects,"
echo "Git commit history, and backup/safety-snapshot files."
echo "It cannot erase old GitHub commit history or old Telegram messages."
echo "Paper/research only: no wallet, no private keys, no live orders."
echo
read -r -p 'Type RESET to continue: ' CONFIRM
if [[ "$CONFIRM" != "RESET" ]]; then
  echo "Cancelled. Nothing was reset."
  exit 0
fi

echo
echo "[1/5] Syncing latest GitHub version..."
git pull --ff-only origin main

if [[ ! -f "$ROOT/$BOT_FILE" ]]; then
  echo "ERROR: $BOT_FILE is missing after sync; refusing to continue."
  exit 1
fi

echo "[2/5] Removing saved scanner and paper-trading state..."
for dir in "$HOME_DIR" "$ROOT" "$SHARED_DIR"; do
  [[ -d "$dir" ]] || continue
  # Search nested project folders but never traverse Git metadata or credentials.
  find "$dir" -type d -name .git -prune -o -type f \
    \( -name 'ALVIN_MEME_GOD_V*_STATE.json' \
       -o -name 'ALVIN_MEME_GOD_V*_HISTORY.txt' \
       -o -name 'ALVIN_MEME_GOD_V*_JOURNAL.txt' \
       -o -name 'ALVIN_MEME_GOD_PAPER_STATE.json' \
       -o -name 'ALVIN_MEME_GOD_STATS.txt' \
       -o -name 'ALVIN_MEME_GOD_TARGETS.txt' \
       -o -name 'ALVIN_MEME_GOD_TRADES.txt' \
       -o -name 'ALVIN_MEME_GOD_SEARCH_HISTORY.txt' \) -delete
done

echo "[3/5] Removing superseded version scripts from project/shared workspace..."
for dir in "$ROOT" "$SHARED_DIR"; do
  [[ -d "$dir" ]] || continue
  find "$dir" -type d -name .git -prune -o -type f \
    \( -name 'ALVIN_MEME_GOD_V*.py' -o -name 'meme_god_v*.py' \) \
    ! -name "$BOT_FILE" -delete
done

echo "[4/5] Checking Python syntax..."
python -m py_compile "$BOT_FILE" paper_trader.py telegram_helper.py

echo "[5/5] Starting the new scanner (paper/research only)..."
echo "Fresh state will be created as the bot runs."
exec python -u "$ROOT/$BOT_FILE"
