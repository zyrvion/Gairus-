# Gairus cloud repair: flows and verification

Baseline: upstream main at c4e8ead, inspected on 2026-10-25.
Browser: existing Flask UI at http://127.0.0.1:8787.
Baseline tests: 23 passed, 3 failed. Four Python files fail parsing.

## Main flows and checks

- Chat: real provider response or explicit missing-configuration message.
- Missions: create, list, plan and run, preserving approval gates.
- Tasks, actions, approvals, memory and activity: navigate and load data.
- Memory: save and reload a user-entered item.
- System: report provider configuration truthfully.
- Mobile: sidebar opens and closes at 375px, without horizontal overflow.
- Slack: preserve signed webhook and separate Socket Mode worker.
- All Python source files outside backup directories parse.
- Existing tests pass without weakening governance checks.
- Allowed and blocked actions produce audit records.
- Missing API configuration fails closed.
- Container build excludes databases, logs, secrets and backups.
- Cloud deployment persists the data directory and Slack memory.

## Scope boundaries

No GitHub write credentials, hosting authorization or DNS access were available
at baseline. Local commits are not upstream changes. A Computer preview is not a
permanent deployment. VIKTOR's private account has not been accessed or exported.
No production DNS changes, paid services, data deletion or autonomous sends.
