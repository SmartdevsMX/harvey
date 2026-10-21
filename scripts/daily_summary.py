#!/usr/bin/env python3
"""Daily Harvey summary to Telegram.

Reads data/harvey.db directly (no Harvey imports) and posts a few counts.
Cron: 0 9 * * * (America/Mexico_City). Needs TELEGRAM_BOT_TOKEN in ENV_FILE.
"""
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "harvey.db"
ENV_FILE = Path(os.environ.get("ENV_FILE", Path.home() / ".claude/channels/telegram/.env"))
CHAT_ID = os.environ.get("CHAT_ID", "8667973440")

# Timestamps in the DB are UTC (CURRENT_TIMESTAMP), so compare with SQLite's 'now'.
QUERIES = [
    ("Negocios nuevos", "SELECT count(*) FROM companies WHERE created_at >= datetime('now','-1 day')"),
    ("Negocios en total", "SELECT count(*) FROM companies"),
    ("Borradores por revisar", "SELECT count(*) FROM outbox WHERE status='pending_review'"),
    ("Enviados (24 h)", "SELECT count(*) FROM outbox WHERE sent_at >= datetime('now','-1 day')"),
    ("Respondieron (total)", "SELECT count(*) FROM prospects WHERE status='replied'"),
    ("Reuniones (total)", "SELECT count(*) FROM prospects WHERE status='meeting'"),
]


def summary(db_path: Path) -> str:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    lines = ["Harvey — últimas 24 h"]
    for label, sql in QUERIES:
        try:
            value = con.execute(sql).fetchone()[0]
        except sqlite3.Error:
            value = "?"
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def token() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("TELEGRAM_BOT_TOKEN not found")


def main() -> None:
    if not DB.exists():
        return
    text = summary(DB)
    if "--dry-run" in sys.argv:
        print(text)
        return
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token()}/sendMessage", data, timeout=15)


if __name__ == "__main__":
    main()
