"""CLI. Examples:

  python -m agenthub send --as claude --to grok "Draft 3 LinkedIn posts" --body "..."
  python -m agenthub send --as instinct --to auto "Write a marketing email"   # auto-route
  python -m agenthub inbox --as grok
  python -m agenthub show T-0001
  python -m agenthub reply T-0001 --as grok "Draft ready: ..."
  python -m agenthub status T-0001 done --as grok --note "posted"
  python -m agenthub handoff T-0001 --as grok --to shay "Need budget approval"
"""
from __future__ import annotations

import argparse
import json
import sys

from .backends import from_env
from .core import STATUSES, PermissionDenied, Registry
from .hub import Hub


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agenthub", description="Task bus between AI agents")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send"); s.add_argument("title"); s.add_argument("--as", dest="agent", required=True)
    s.add_argument("--to", required=True, help="agent id or 'auto'"); s.add_argument("--body", default="")
    s.add_argument("--priority", type=int, default=3)

    s = sub.add_parser("inbox"); s.add_argument("--as", dest="agent", required=True)
    s.add_argument("--all", action="store_true", help="include done tasks")

    s = sub.add_parser("show"); s.add_argument("id"); s.add_argument("--full", action="store_true")

    s = sub.add_parser("reply"); s.add_argument("id"); s.add_argument("text")
    s.add_argument("--as", dest="agent", required=True)

    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("status", choices=STATUSES)
    s.add_argument("--as", dest="agent", required=True); s.add_argument("--note", default="")

    s = sub.add_parser("handoff"); s.add_argument("id"); s.add_argument("note")
    s.add_argument("--as", dest="agent", required=True); s.add_argument("--to", required=True)

    s = sub.add_parser("suggest"); s.add_argument("text")
    sub.add_parser("agents")

    a = p.parse_args(argv)
    reg = Registry.load()

    try:
        if a.cmd == "agents":
            for aid, info in reg.agents.items():
                print(f"{aid:<9} tier={info.get('cost_tier')} {', '.join(info.get('strengths', []))}")
            return 0
        if a.cmd == "suggest":
            print(reg.suggest(a.text))
            return 0

        hub = Hub(from_env(), reg)
        if a.cmd == "send":
            t = hub.send(a.agent, a.to, a.title, a.body, a.priority)
            print(json.dumps(t.to_dict(), ensure_ascii=False) if a.json else t.line())
        elif a.cmd == "inbox":
            tasks = hub.inbox(a.agent, a.all)
            if a.json:
                print(json.dumps([t.to_dict() for t in tasks], ensure_ascii=False))
            else:
                print("\n".join(t.line() for t in tasks) or "inbox empty")
        elif a.cmd == "show":
            t = hub.show(a.id)
            if a.json:
                print(json.dumps(t.to_dict(), ensure_ascii=False))
            else:
                print(t.brief(last=10**6, body_chars=10**9) if a.full else t.brief())
        elif a.cmd == "reply":
            hub.reply(a.id, a.agent, a.text)
        elif a.cmd == "status":
            hub.status(a.id, a.agent, a.status, a.note)
        elif a.cmd == "handoff":
            hub.handoff(a.id, a.agent, a.to, a.note)
    except (PermissionDenied, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
