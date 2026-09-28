"""Storage backends. All share the same small interface so agents never care where tasks live.

- LocalBackend:  JSON files in a folder (works offline, or synced via git / Drive).
- LinearBackend: Linear issues. Recipient/sender are labels (to:grok, from:claude).
- GitHubBackend: GitHub issues, same label scheme. Free fallback when Linear isn't set up.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

from .core import STATUSES, Message, Task, now


class Backend:
    def create(self, task: Task) -> Task: raise NotImplementedError
    def get(self, task_id: str) -> Task: raise NotImplementedError
    def inbox(self, agent: str, include_done: bool = False) -> list[Task]: raise NotImplementedError
    def comment(self, task_id: str, sender: str, text: str) -> None: raise NotImplementedError
    def set_status(self, task_id: str, status: str) -> None: raise NotImplementedError
    def reassign(self, task_id: str, to: str) -> None: raise NotImplementedError


# ---------------------------------------------------------------- local

class LocalBackend(Backend):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        if not re.fullmatch(r"T-\d+", task_id):
            raise KeyError(f"bad task id '{task_id}'")
        return self.root / f"{task_id}.json"

    def _save(self, task: Task) -> None:
        task.updated = now()
        tmp = self._path(task.id).with_suffix(".tmp")
        tmp.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path(task.id))

    def _all(self) -> list[Task]:
        tasks = []
        for p in sorted(self.root.glob("T-*.json")):
            tasks.append(Task.from_dict(json.loads(p.read_text(encoding="utf-8"))))
        return tasks

    def create(self, task: Task) -> Task:
        nums = [int(p.stem[2:]) for p in self.root.glob("T-*.json")]
        task.id = f"T-{(max(nums) + 1 if nums else 1):04d}"
        self._save(task)
        return task

    def get(self, task_id: str) -> Task:
        p = self._path(task_id)
        if not p.exists():
            raise KeyError(f"no task {task_id}")
        return Task.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def inbox(self, agent: str, include_done: bool = False) -> list[Task]:
        tasks = [t for t in self._all() if t.to == agent and (include_done or t.status != "done")]
        return sorted(tasks, key=lambda t: (t.priority, t.created))

    def comment(self, task_id: str, sender: str, text: str) -> None:
        t = self.get(task_id)
        t.thread.append(Message(sender, text))
        self._save(t)

    def set_status(self, task_id: str, status: str) -> None:
        t = self.get(task_id)
        t.status = status
        self._save(t)

    def reassign(self, task_id: str, to: str) -> None:
        t = self.get(task_id)
        t.to = to
        self._save(t)


# ---------------------------------------------------------------- shared helpers for remote backends

def _http(method: str, url: str, headers: dict, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else None


COMMENT_RE = re.compile(r"^\*\*(\w+):\*\*\s?(.*)$", re.S)


def _fmt_comment(sender: str, text: str) -> str:
    return f"**{sender}:** {text}"


def _parse_comment(body: str, fallback: str, at: str) -> Message:
    m = COMMENT_RE.match(body or "")
    return Message(m.group(1), m.group(2), at) if m else Message(fallback, body or "", at)


def _label_value(labels: list[str], prefix: str, default: str = "") -> str:
    for name in labels:
        if name.startswith(prefix):
            return name[len(prefix):]
    return default


# ---------------------------------------------------------------- Linear

LINEAR_STATE_TYPE = {"todo": "unstarted", "in_progress": "started", "blocked": "started", "done": "completed"}
LINEAR_TYPE_STATUS = {"backlog": "todo", "unstarted": "todo", "triage": "todo",
                      "started": "in_progress", "completed": "done", "canceled": "done"}

ISSUE_FIELDS = """identifier title description priority createdAt updatedAt
  state { type } labels { nodes { name } }"""


class LinearBackend(Backend):
    """Needs LINEAR_API_KEY and LINEAR_TEAM_ID (the team's UUID or key, e.g. 'OPS')."""

    URL = "https://api.linear.app/graphql"

    def __init__(self, api_key: str | None = None, team: str | None = None, http=_http):
        self.key = api_key or os.environ["LINEAR_API_KEY"]
        self.team_ref = team or os.environ["LINEAR_TEAM_ID"]
        self._http = http
        self._team_id = None
        self._labels: dict[str, str] = {}

    def _q(self, query: str, variables: dict | None = None) -> dict:
        res = self._http("POST", self.URL, {"Authorization": self.key}, {"query": query, "variables": variables or {}})
        if res.get("errors"):
            raise RuntimeError(f"Linear error: {res['errors']}")
        return res["data"]

    @property
    def team_id(self) -> str:
        if self._team_id is None:
            self._team_id = self._q("query($id:String!){team(id:$id){id}}", {"id": self.team_ref})["team"]["id"]
        return self._team_id

    def _label_id(self, name: str) -> str:
        if name not in self._labels:
            found = self._q(
                "query($n:String!){issueLabels(filter:{name:{eq:$n}}){nodes{id}}}", {"n": name}
            )["issueLabels"]["nodes"]
            if found:
                self._labels[name] = found[0]["id"]
            else:
                self._labels[name] = self._q(
                    "mutation($i:IssueLabelCreateInput!){issueLabelCreate(input:$i){issueLabel{id}}}",
                    {"i": {"name": name, "teamId": self.team_id}},
                )["issueLabelCreate"]["issueLabel"]["id"]
        return self._labels[name]

    def _state_id(self, status: str) -> str:
        states = self._q("query($id:String!){team(id:$id){states{nodes{id type position}}}}",
                         {"id": self.team_id})["team"]["states"]["nodes"]
        wanted = [s for s in states if s["type"] == LINEAR_STATE_TYPE[status]]
        return min(wanted, key=lambda s: s["position"])["id"]

    def _to_task(self, n: dict, comments: list[dict] | None = None) -> Task:
        labels = [l["name"] for l in n["labels"]["nodes"]]
        sender = _label_value(labels, "from:")
        status = "blocked" if "blocked" in labels else LINEAR_TYPE_STATUS.get(n["state"]["type"], "todo")
        thread = [_parse_comment(c["body"], "?", c["createdAt"]) for c in (comments or [])]
        return Task(id=n["identifier"], title=n["title"], sender=sender, to=_label_value(labels, "to:"),
                    body=n.get("description") or "", status=status, priority=n.get("priority") or 3,
                    thread=thread, created=n["createdAt"], updated=n["updatedAt"])

    def _issue(self, task_id: str, with_comments: bool = False) -> dict:
        extra = "id comments(first:100){nodes{body createdAt}}" if with_comments else "id"
        return self._q(f"query($id:String!){{issue(id:$id){{{extra} {ISSUE_FIELDS}}}}}", {"id": task_id})["issue"]

    def _set_labels(self, task_id: str, drop_prefix: str | None, add: list[str], drop: list[str] = ()) -> None:
        issue = self._issue(task_id)
        names = [l["name"] for l in issue["labels"]["nodes"]
                 if not (drop_prefix and l["name"].startswith(drop_prefix)) and l["name"] not in drop]
        ids = [self._label_id(n) for n in dict.fromkeys(names + add)]
        self._q("mutation($id:String!,$i:IssueUpdateInput!){issueUpdate(id:$id,input:$i){success}}",
                {"id": issue["id"], "i": {"labelIds": ids}})

    def create(self, task: Task) -> Task:
        labels = [self._label_id(f"to:{task.to}"), self._label_id(f"from:{task.sender}")]
        n = self._q(
            f"mutation($i:IssueCreateInput!){{issueCreate(input:$i){{issue{{{ISSUE_FIELDS}}}}}}}",
            {"i": {"teamId": self.team_id, "title": task.title, "description": task.body,
                   "priority": task.priority, "labelIds": labels}},
        )["issueCreate"]["issue"]
        return self._to_task(n)

    def get(self, task_id: str) -> Task:
        n = self._issue(task_id, with_comments=True)
        return self._to_task(n, n["comments"]["nodes"])

    def inbox(self, agent: str, include_done: bool = False) -> list[Task]:
        flt = {"labels": {"name": {"eq": f"to:{agent}"}}, "team": {"id": {"eq": self.team_id}}}
        if not include_done:
            flt["state"] = {"type": {"nin": ["completed", "canceled"]}}
        nodes = self._q(f"query($f:IssueFilter){{issues(filter:$f,first:100){{nodes{{{ISSUE_FIELDS}}}}}}}",
                        {"f": flt})["issues"]["nodes"]
        return sorted((self._to_task(n) for n in nodes), key=lambda t: (t.priority or 5, t.created))

    def comment(self, task_id: str, sender: str, text: str) -> None:
        self._q("mutation($i:CommentCreateInput!){commentCreate(input:$i){success}}",
                {"i": {"issueId": self._issue(task_id)["id"], "body": _fmt_comment(sender, text)}})

    def set_status(self, task_id: str, status: str) -> None:
        issue_id = self._issue(task_id)["id"]
        self._q("mutation($id:String!,$i:IssueUpdateInput!){issueUpdate(id:$id,input:$i){success}}",
                {"id": issue_id, "i": {"stateId": self._state_id(status)}})
        if status == "blocked":
            self._set_labels(task_id, None, ["blocked"])
        else:
            self._set_labels(task_id, None, [], drop=["blocked"])

    def reassign(self, task_id: str, to: str) -> None:
        self._set_labels(task_id, "to:", [f"to:{to}"])


# ---------------------------------------------------------------- GitHub

class GitHubBackend(Backend):
    """Needs GITHUB_TOKEN and AGENTHUB_GITHUB_REPO ('owner/repo')."""

    def __init__(self, token: str | None = None, repo: str | None = None, http=_http):
        self.token = token or os.environ["GITHUB_TOKEN"]
        self.repo = repo or os.environ["AGENTHUB_GITHUB_REPO"]
        self._http = http

    def _call(self, method: str, path: str, payload: dict | None = None):
        return self._http(method, f"https://api.github.com/repos/{self.repo}{path}",
                          {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}, payload)

    def _to_task(self, i: dict, comments: list[dict] | None = None) -> Task:
        labels = [l["name"] for l in i["labels"]]
        status = _label_value(labels, "status:", "done" if i["state"] == "closed" else "todo")
        return Task(id=str(i["number"]), title=i["title"], sender=_label_value(labels, "from:"),
                    to=_label_value(labels, "to:"), body=i.get("body") or "", status=status,
                    priority=int(_label_value(labels, "P", "3") or 3),
                    thread=[_parse_comment(c["body"], c["user"]["login"], c["created_at"]) for c in comments or []],
                    created=i["created_at"], updated=i["updated_at"])

    def _relabel(self, task_id: str, prefix: str, value: str) -> dict:
        i = self._call("GET", f"/issues/{task_id}")
        labels = [l["name"] for l in i["labels"] if not l["name"].startswith(prefix)] + [f"{prefix}{value}"]
        return self._call("PATCH", f"/issues/{task_id}", {"labels": labels})

    def create(self, task: Task) -> Task:
        labels = [f"to:{task.to}", f"from:{task.sender}", f"status:{task.status}", f"P{task.priority}"]
        return self._to_task(self._call("POST", "/issues", {"title": task.title, "body": task.body, "labels": labels}))

    def get(self, task_id: str) -> Task:
        return self._to_task(self._call("GET", f"/issues/{task_id}"),
                             self._call("GET", f"/issues/{task_id}/comments?per_page=100"))

    def inbox(self, agent: str, include_done: bool = False) -> list[Task]:
        state = "all" if include_done else "open"
        items = self._call("GET", f"/issues?labels=to:{agent}&state={state}&per_page=100")
        tasks = [self._to_task(i) for i in items if "pull_request" not in i]
        return sorted(tasks, key=lambda t: (t.priority, t.created))

    def comment(self, task_id: str, sender: str, text: str) -> None:
        self._call("POST", f"/issues/{task_id}/comments", {"body": _fmt_comment(sender, text)})

    def set_status(self, task_id: str, status: str) -> None:
        self._relabel(task_id, "status:", status)
        self._call("PATCH", f"/issues/{task_id}", {"state": "closed" if status == "done" else "open"})

    def reassign(self, task_id: str, to: str) -> None:
        self._relabel(task_id, "to:", to)


def from_env() -> Backend:
    kind = os.environ.get("AGENTHUB_BACKEND", "local").lower()
    if kind == "linear":
        return LinearBackend()
    if kind == "github":
        return GitHubBackend()
    if kind == "local":
        return LocalBackend(os.environ.get("AGENTHUB_DIR", Path(__file__).resolve().parent.parent / "bus"))
    raise ValueError(f"AGENTHUB_BACKEND must be local|linear|github, got '{kind}'")


assert set(LINEAR_STATE_TYPE) == set(STATUSES)
