# Working with Instinct (Shay Hershcovich's lead agent)

Instinct is the manager agent. Claude reports to it through two channels:

1. **Email** — tasks, questions, handing over information: `6jwl78@mail.instinct.com`
   - Subject: `Claude`
   - Body: date, what is needed, attachments if relevant. Instinct replies to the same address.
2. **Shared AGENT-HUB folder in Google Drive** — day-to-day work:
   - Folder: https://drive.google.com/drive/folders/1fUP_vG9YQXqtYOGWwQw0V9qJQKaCMSYN
   - Tasks doc (INBOX): https://docs.google.com/document/d/1VR-jjsWgIUxS82na809g71o4xTciqtmShTBvAm2ro9A/edit
   - Status sheet: https://docs.google.com/spreadsheets/d/1AcQ2ekq26JKg5VwqItD1jM7lrqkJyKjWkiqIHc6FstA/edit

Rules:
- Every deliverable, task or piece of information Instinct needs to see goes in the tasks doc as a new
  section: `date | sender (Claude) | content | status`.
- Update Claude's status row in the sheet.
- Instinct monitors the doc and answers under a "תשובת Instinct" section below each task.
- No write access to the files → send the content by email instead, or ask Shay to share them.

The code in this repo (`agenthub/`) is the task bus for a later move to Linear; see `README.md` and `PROTOCOL.md`.
