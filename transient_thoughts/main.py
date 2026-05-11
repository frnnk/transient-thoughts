"""
CLI entry point: parses args and either dumps entries (--view) or starts the tray app.
"""

import argparse
import sys
from transient_thoughts import config
from transient_thoughts.app import TransientThoughtsApp
from transient_thoughts.storage import ThoughtStorage


def main():
    parser = argparse.ArgumentParser(description="Transient Thoughts: quick thought journaling")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override the stored interval (minutes between prompts) and persist it",
    )
    parser.add_argument(
        "--view",
        action="store_true",
        help="Print all entries to stdout and exit",
    )
    args = parser.parse_args()

    if args.view:
        storage = ThoughtStorage()
        entries = storage.get_all()
        if not entries:
            print("No thoughts recorded yet.")
        else:
            for _id, timestamp, text in entries:
                print(f"[{timestamp}]  {text}")
        sys.exit(0)

    app = TransientThoughtsApp(interval_minutes=args.interval)
    app.start()


if __name__ == "__main__":
    main()
