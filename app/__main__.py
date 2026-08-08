from __future__ import annotations

import argparse

from app.modules.config import get_settings
from app.modules.db import connect, init_db, recent_signal_counts


def main() -> None:
    parser = argparse.ArgumentParser(prog="zinsider")
    sub = parser.add_subparsers(dest="cmd")

    scan = sub.add_parser("scan", help="run the futures scanner once")
    scan.add_argument("--force", action="store_true")

    rollovers = sub.add_parser("rollovers", help="run the futures rollover alert check once")
    rollovers.add_argument("--force", action="store_true")

    sub.add_parser("serve", help="run the TradingView webhook server")
    sub.add_parser("scheduler", help="run the weekday scan and rollover scheduler")
    sub.add_parser("init-db", help="initialize the SQLite database")

    stats = sub.add_parser("stats", help="print basic signal counts")
    stats.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    settings = get_settings()

    if args.cmd in (None, "scan"):
        from app.main import run_futures_scan

        print(run_futures_scan(force=getattr(args, "force", False)))
        return

    if args.cmd == "rollovers":
        from app.modules.rollovers import run_rollover_alerts

        print(run_rollover_alerts(force=getattr(args, "force", False)))
        return

    if args.cmd == "serve":
        from app.presence import start_presence_thread
        from app.server import app

        start_presence_thread(settings)

        try:
            from waitress import serve
        except ImportError:
            app.run(host="0.0.0.0", port=8080)
        else:
            serve(app, host="0.0.0.0", port=8080)
        return

    if args.cmd == "scheduler":
        from app.scheduler import start_scheduler

        start_scheduler()
        return

    if args.cmd == "init-db":
        init_db(settings["db_path"])
        print(f"initialized {settings['db_path']}")
        return

    if args.cmd == "stats":
        with connect(settings["db_path"]) as conn:
            for row in recent_signal_counts(conn, limit=args.limit):
                direction = f" {row['direction']}" if row["direction"] else ""
                print(f"{row['ticker']} {row['model']} {row['timeframe']}{direction}: {row['count']}")
        return

    parser.error(f"unknown command: {args.cmd}")


if __name__ == "__main__":
    main()
