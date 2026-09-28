"""Agent registry, permissions, task model and routing. Backend-agnostic."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("todo", "in_progress", "blocked", "done")
REGISTRY_PATH = Path(os.environ.get("AGENTHUB_REGISTRY", Path(__file__).resolve().parent.parent / "agents.json"))

# Keywords that hint which strength a task needs. Used only for suggestions;
# the sender always makes the final call.
KEYWORDS = {
    "code": ["code", "bug", "script", "api", "deploy", "קוד", "באג", "סקריפט"],
    "marketing": ["marketing", "campaign", "ad ", "ads", "מרקטינג", "שיווק", "קמפיין", "מודעה"],
    "social": ["post", "tweet", "linkedin", "instagram", "פוסט", "רשתות"],
    "research": ["research", "compare", "find", "מחקר", "השוואה", "תמצא"],
    "writing": ["write", "draft", "email", "article", "כתוב", "טיוטה", "מאמר", "מייל"],
    "planning": ["plan", "prioritize", "roadmap", "תכנון", "תעדוף"],
    "approval": ["approve", "pay", "password", "אישור", "תשלום", "סיסמה"],
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PermissionDenied(Exception):
    pass


class Registry:
    def __init__(self, data: dict):
        self.human = data["human"]
        self.agents = data["agents"]

    @classmethod
    def load(cls, path: Path | str = REGISTRY_PATH) -> "Registry":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def check(self, agent: str) -> None:
        if agent not in self.agents:
            raise KeyError(f"unknown agent '{agent}'. known: {', '.join(self.agents)}")

    def can_assign(self, sender: str, recipient: str) -> bool:
        self.check(sender)
        self.check(recipient)
        return recipient in self.agents[sender].get("can_assign_to", [])

    def require_assign(self, sender: str, recipient: str) -> None:
        if not self.can_assign(sender, recipient):
            raise PermissionDenied(f"{sender} is not allowed to assign tasks to {recipient}")

    def suggest(self, text: str, exclude: str | None = None) -> str:
        """Best-matching agent (most strengths hit, then cheapest); falls back to the manager."""
        text = f" {text.lower()} "
        needed = {s for s, words in KEYWORDS.items() if any(w in text for w in words)}
        candidates = [
            (-len(needed & set(a.get("strengths", []))), a.get("cost_tier", 50), aid)
            for aid, a in self.agents.items()
            if aid != exclude and needed & set(a.get("strengths", []))
        ]
        if candidates:
            return min(candidates)[2]
        managers = [aid for aid, a in self.agents.items() if a.get("role") == "manager" and aid != exclude]
        return managers[0] if managers else self.human


@dataclass
class Message:
    sender: str
    text: str
    at: str = field(default_factory=now)


@dataclass
class Task:
    id: str
    title: str
    sender: str
    to: str
    body: str = ""
    status: str = "todo"
    priority: int = 3  # 1 urgent .. 4 low (same scale as Linear)
    thread: list[Message] = field(default_factory=list)
    created: str = field(default_factory=now)
    updated: str = field(default_factory=now)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        d = dict(d)
        d["thread"] = [Message(**m) for m in d.get("thread", [])]
        return cls(**d)

    def line(self) -> str:
        """One-line summary: what an agent reads first, to save tokens."""
        return f"[{self.id}] P{self.priority} {self.status:<11} {self.sender}->{self.to}  {self.title}"

    def brief(self, last: int = 3, body_chars: int = 600) -> str:
        """Compact view: truncated body plus only the last few thread messages."""
        body = self.body if len(self.body) <= body_chars else self.body[:body_chars] + " …"
        out = [self.line(), body] if body else [self.line()]
        skipped = len(self.thread) - last
        if skipped > 0:
            out.append(f"  ({skipped} earlier messages hidden)")
        out += [f"  {m.sender} @ {m.at}: {m.text}" for m in self.thread[-last:]]
        return "\n".join(out)
