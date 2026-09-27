import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from agenthub.__main__ import main
from agenthub.backends import GitHubBackend, LinearBackend, LocalBackend
from agenthub.core import PermissionDenied, Registry
from agenthub.hub import Hub

REG = Registry({
    "human": "shay",
    "agents": {
        "claude": {"strengths": ["code"], "cost_tier": 3, "can_assign_to": ["grok", "chatgpt", "instinct", "shay"]},
        "chatgpt": {"strengths": ["writing", "research"], "cost_tier": 2, "can_assign_to": ["claude", "shay"]},
        "grok": {"strengths": ["marketing", "writing"], "cost_tier": 1, "can_assign_to": ["claude", "shay"]},
        "instinct": {"role": "manager", "strengths": ["planning"], "cost_tier": 0,
                     "can_assign_to": ["claude", "chatgpt", "grok", "shay"]},
        "shay": {"strengths": ["approval"], "cost_tier": 99, "can_assign_to": ["claude", "chatgpt", "grok", "instinct"]},
    },
})


class HubFlow:
    """Same scenario runs against every backend."""

    def make_backend(self): raise NotImplementedError

    def setUp(self):
        self.hub = Hub(self.make_backend(), REG)

    def test_full_conversation(self):
        t = self.hub.send("instinct", "grok", "Launch post", "Write a launch post", priority=2)
        self.assertEqual([x.id for x in self.hub.inbox("grok")], [t.id])
        self.assertEqual(self.hub.inbox("claude"), [])

        self.hub.status(t.id, "grok", "in_progress")
        self.hub.reply(t.id, "grok", "draft: hello world")
        self.hub.handoff(t.id, "grok", "shay", "approve?")
        self.assertEqual(self.hub.inbox("grok"), [])
        got = self.hub.show(t.id)
        self.assertEqual((got.to, got.sender, got.status), ("shay", "instinct", "todo"))
        self.assertEqual([m.sender for m in got.thread], ["grok", "grok"])
        self.assertIn("draft: hello world", got.thread[0].text)

        self.hub.status(t.id, "shay", "done", "approved")
        self.assertEqual(self.hub.inbox("shay"), [])
        self.assertEqual(len(self.hub.inbox("shay", include_done=True)), 1)

    def test_blocked_status(self):
        t = self.hub.send("claude", "chatgpt", "Research")
        self.hub.status(t.id, "chatgpt", "blocked", "need access")
        self.assertEqual(self.hub.show(t.id).status, "blocked")
        self.hub.status(t.id, "chatgpt", "in_progress")
        self.assertEqual(self.hub.show(t.id).status, "in_progress")

    def test_permissions(self):
        with self.assertRaises(PermissionDenied):
            self.hub.send("grok", "chatgpt", "not allowed")
        t = self.hub.send("claude", "grok", "x")
        with self.assertRaises(PermissionDenied):
            self.hub.status(t.id, "chatgpt", "done")
        with self.assertRaises(PermissionDenied):
            self.hub.handoff(t.id, "chatgpt", "claude", "steal")


class LocalTest(HubFlow, unittest.TestCase):
    def make_backend(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return LocalBackend(self.tmp.name)

    def test_ids_increment_and_bad_ids_rejected(self):
        a = self.hub.send("claude", "grok", "a")
        b = self.hub.send("claude", "grok", "b")
        self.assertEqual((a.id, b.id), ("T-0001", "T-0002"))
        with self.assertRaises(KeyError):
            self.hub.show("../../etc/passwd")


class FakeLinear:
    """Minimal in-memory Linear GraphQL server covering the queries LinearBackend sends."""

    def __init__(self):
        self.labels = {}      # name -> id
        self.issues = {}      # id -> dict
        self.states = [{"id": "s1", "type": "unstarted", "position": 0}, {"id": "s2", "type": "started", "position": 1},
                       {"id": "s3", "type": "completed", "position": 2}, {"id": "s0", "type": "backlog", "position": -1}]

    def _node(self, i):
        by_id = {v: k for k, v in self.labels.items()}
        state = next(s for s in self.states if s["id"] == i["stateId"])
        return {"id": i["id"], "identifier": i["identifier"], "title": i["title"], "description": i["description"],
                "priority": i["priority"], "createdAt": i["createdAt"], "updatedAt": i["createdAt"],
                "state": {"type": state["type"]}, "labels": {"nodes": [{"name": by_id[l]} for l in i["labelIds"]]},
                "comments": {"nodes": i["comments"]}}

    def _find(self, ref):
        return next(i for i in self.issues.values() if ref in (i["id"], i["identifier"]))

    def __call__(self, method, url, headers, payload):
        assert headers["Authorization"] == "key"
        q, v = payload["query"], payload["variables"]
        if "team(id:$id){id}" in q:
            return {"data": {"team": {"id": "team-uuid"}}}
        if "states" in q:
            return {"data": {"team": {"states": {"nodes": self.states}}}}
        if "issueLabels(" in q:
            n = v["n"]
            return {"data": {"issueLabels": {"nodes": [{"id": self.labels[n]}] if n in self.labels else []}}}
        if "issueLabelCreate" in q:
            self.labels[v["i"]["name"]] = f"L{len(self.labels)}"
            return {"data": {"issueLabelCreate": {"issueLabel": {"id": self.labels[v['i']['name']]}}}}
        if "issueCreate" in q:
            n = len(self.issues) + 1
            i = {"id": f"uuid{n}", "identifier": f"OPS-{n}", "stateId": "s1", "comments": [],
                 "createdAt": f"2026-01-0{n}", **{k: v["i"][k] for k in ("title", "description", "priority", "labelIds")}}
            self.issues[i["id"]] = i
            return {"data": {"issueCreate": {"issue": self._node(i)}}}
        if "issueUpdate" in q:
            i = self._find(v["id"])
            if "stateId" in v["i"]:
                i["stateId"] = v["i"]["stateId"]
            if "labelIds" in v["i"]:
                i["labelIds"] = v["i"]["labelIds"]
            return {"data": {"issueUpdate": {"success": True}}}
        if "commentCreate" in q:
            self._find(v["i"]["issueId"])["comments"].append({"body": v["i"]["body"], "createdAt": "t"})
            return {"data": {"commentCreate": {"success": True}}}
        if "issue(id:" in q:
            return {"data": {"issue": self._node(self._find(v["id"]))}}
        if "issues(filter" in q:
            f = v["f"]
            want = self.labels.get(f["labels"]["name"]["eq"])
            out = [self._node(i) for i in self.issues.values() if want in i["labelIds"]]
            if "state" in f:
                out = [n for n in out if n["state"]["type"] not in f["state"]["type"]["nin"]]
            return {"data": {"issues": {"nodes": out}}}
        raise AssertionError(f"unexpected query: {q}")


class LinearTest(HubFlow, unittest.TestCase):
    def make_backend(self):
        return LinearBackend("key", "OPS", http=FakeLinear())


class FakeGitHub:
    def __init__(self):
        self.issues, self.comments = {}, {}

    def _issue(self, n):
        i = self.issues[n]
        return {**i, "labels": [{"name": l} for l in i["labels"]]}

    def __call__(self, method, url, headers, payload):
        path = url.split("/repos/o/r", 1)[1]
        if method == "POST" and path == "/issues":
            n = len(self.issues) + 1
            self.issues[n] = {"number": n, "state": "open", "created_at": str(n), "updated_at": str(n), **payload}
            self.comments[n] = []
            return self._issue(n)
        if path.startswith("/issues?"):
            params = dict(p.split("=") for p in path.split("?")[1].split("&"))
            return [self._issue(n) for n, i in self.issues.items()
                    if params["labels"] in i["labels"] and (params["state"] == "all" or i["state"] == "open")]
        n = int(path.split("/")[2].split("?")[0])
        if path.endswith("/comments") and method == "POST":
            self.comments[n].append({"body": payload["body"], "user": {"login": "bot"}, "created_at": "t"})
            return {}
        if "/comments" in path:
            return self.comments[n]
        if method == "PATCH":
            self.issues[n].update(payload)
        return self._issue(n)


class GitHubTest(HubFlow, unittest.TestCase):
    def make_backend(self):
        return GitHubBackend("tok", "o/r", http=FakeGitHub())


class RoutingTest(unittest.TestCase):
    def test_cheapest_matching_agent(self):
        self.assertEqual(REG.suggest("write a marketing campaign"), "grok")
        self.assertEqual(REG.suggest("fix this bug in the script"), "claude")
        self.assertEqual(REG.suggest("תכתוב פוסט לקמפיין"), "grok")

    def test_fallback_to_manager(self):
        self.assertEqual(REG.suggest("something vague"), "instinct")
        self.assertEqual(REG.suggest("something vague", exclude="instinct"), "shay")


class CliTest(unittest.TestCase):
    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            out = io.StringIO()
            with mock.patch.dict(os.environ, AGENTHUB_BACKEND="local", AGENTHUB_DIR=d), redirect_stdout(out):
                self.assertEqual(main(["send", "--as", "claude", "--to", "grok", "Hi", "--body", "b"]), 0)
                self.assertEqual(main(["inbox", "--as", "grok"]), 0)
                self.assertEqual(main(["send", "--as", "grok", "--to", "nobody", "nope"]), 2)
            self.assertIn("claude->grok  Hi", out.getvalue())


if __name__ == "__main__":
    unittest.main()
