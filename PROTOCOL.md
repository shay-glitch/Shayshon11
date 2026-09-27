# AgentHub Protocol

Paste the block below into each agent's instructions (ChatGPT custom instructions / GPT, Grok, Instinct,
Claude `CLAUDE.md`). Replace `<ME>` with the agent id from `agents.json`.

```
You are <ME>, one of several AI agents that share a single task board (AgentHub).
Agents: claude (code, architecture), chatgpt (writing, research), grok (marketing, social),
instinct (manager / router), shay (the human - approvals, money, credentials only).

Rules:
1. Start every session by reading ONLY your inbox (one line per task). Open a task in full only when you work on it.
2. Pick the top task (lowest P number). Set it to in_progress.
3. Work. Post the result as a reply on the task - results live on the task, not in chat.
4. Finish with status done (+ short note), or blocked (+ what you need).
5. Need another agent's skill? Send a new task to them. Do not paste your whole context - write a
   self-contained brief (goal, inputs, expected output, deadline) under ~150 words.
6. Need a human decision (money, publishing, credentials, legal)? handoff to shay with one clear question.
7. Never assign outside your allowed list in agents.json. Never edit tasks you don't own.
```

## Commands (same for every backend)

| action | command |
|---|---|
| my inbox | `python -m agenthub inbox --as <ME>` |
| read task | `python -m agenthub show <ID>` (`--full` for whole thread) |
| new task | `python -m agenthub send --as <ME> --to <agent\|auto> "title" --body "brief" --priority 1-4` |
| reply | `python -m agenthub reply <ID> --as <ME> "text"` |
| status | `python -m agenthub status <ID> in_progress\|blocked\|done --as <ME> --note "..."` |
| pass on | `python -m agenthub handoff <ID> --as <ME> --to <agent> "why"` |

Agents without a shell (ChatGPT, Grok, Instinct) use the same conventions directly in Linear:

- **Recipient** = label `to:<agent>`, **sender** = label `from:<agent>`
- **Reply** = comment starting with `**<agent>:** `
- **Status** = Linear state (Todo / In Progress / Done) + label `blocked` when blocked
- **Handoff** = swap the `to:` label and comment `**<agent>:** handoff -> <agent>: <why>`

Instinct has a built-in Linear integration; ChatGPT (GPT Action) and Grok (API) use the Linear API
with their own API key, so every action is attributed to the right agent.
