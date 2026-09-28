"""The Hub: every agent talks through this. Enforces who may assign what to whom."""
from __future__ import annotations

from .backends import Backend
from .core import STATUSES, PermissionDenied, Registry, Task


class Hub:
    def __init__(self, backend: Backend, registry: Registry):
        self.backend = backend
        self.reg = registry

    def send(self, sender: str, to: str, title: str, body: str = "", priority: int = 3) -> Task:
        if to == "auto":
            to = self.reg.suggest(f"{title} {body}", exclude=sender)
        self.reg.require_assign(sender, to)
        if not 1 <= priority <= 4:
            raise ValueError("priority must be 1 (urgent) .. 4 (low)")
        return self.backend.create(Task(id="", title=title, sender=sender, to=to, body=body, priority=priority))

    def inbox(self, agent: str, include_done: bool = False) -> list[Task]:
        self.reg.check(agent)
        return self.backend.inbox(agent, include_done)

    def show(self, task_id: str) -> Task:
        return self.backend.get(task_id)

    def reply(self, task_id: str, sender: str, text: str) -> None:
        self.reg.check(sender)
        self.backend.comment(task_id, sender, text)

    def status(self, task_id: str, agent: str, status: str, note: str = "") -> None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        t = self.backend.get(task_id)
        if agent not in (t.to, t.sender, self.reg.human):
            raise PermissionDenied(f"only {t.to}, {t.sender} or {self.reg.human} can change {task_id}")
        self.backend.set_status(task_id, status)
        if note:
            self.backend.comment(task_id, agent, f"[{status}] {note}")

    def handoff(self, task_id: str, agent: str, to: str, note: str) -> None:
        """Current owner passes the task on (e.g. to shay when a human decision is needed)."""
        t = self.backend.get(task_id)
        if agent not in (t.to, self.reg.human):
            raise PermissionDenied(f"only the current owner ({t.to}) can hand off {task_id}")
        self.reg.require_assign(agent, to)
        self.backend.comment(task_id, agent, f"handoff -> {to}: {note}")
        self.backend.reassign(task_id, to)
        self.backend.set_status(task_id, "todo")
