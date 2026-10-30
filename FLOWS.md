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
- The owner cancelled Render and all spending; no active Render Blueprint remains.
- Free Hugging Face deployment requests only `zero-a10g`, no paid storage.
- Sign-in is reserved to the actual Space owner, including direct callback calls.
- Private data survives process replacement because it is stored in a separate
  private dataset repository, not on the Space's temporary disk.
- Conversation: send, reload, select an older conversation, start a new one.
- Memory: save a Unicode/multiline note and reload the page to recover it.
- Missions: generate a real plan, select it, change its manual status and reload.
- Invalid, unauthenticated and non-owner requests cannot read or write data.
- ZeroGPU quota failures do not trigger paid fallback or claim successful work.
- The stateless owner service API rejects missing/incorrect keys.
- New free-cloud UI fits desktop and 375px, including login and populated views.
- A real deployed model reply is required before calling the free cloud usable.

## Scope boundaries

No GitHub write credentials, hosting authorization or DNS access were available
at baseline. Local commits are not upstream changes. A Computer preview is not a
permanent deployment. VIKTOR's private account has not been accessed or exported.
No production DNS changes, paid services, data deletion or autonomous sends.

## Own application and stable installation, 2026-10-30

The owner now explicitly rejects Hugging Face as the target platform. Preserve
the old service until a replacement has passed real checks; a cosmetic wrapper
or a redirect is not migration. The stable target is gairus.zyrvion.io, separate
from Zyrvion. No paid resources, main merge, or unrelated app changes.

Baseline inspection: original Flask login and application shell opened on an
isolated QA server, not the user's data. The existing manifest has no id/icons,
its icon files are absent, the old worker is not registered, and its cache-first
strategy would retain obsolete code if activated. The login key stays in RAM.

- Open the original app on desktop and 375px. Keep the private login, all
  navigation views, mission creation, memory save/reopen, explicit missing-model
  response, and logout. No real external messages or purchases during QA.
- Manifest: stable id, start URL and scope "/", standalone, French, and actual
  192/512 icons that preserve the existing typographic G.
- Installation: offer the browser's native install prompt when available;
  otherwise explain the browser's Add to Home Screen option. Do not imply the
  app is installed just because a button was clicked.
- Update: register the same-origin worker, bypass HTTP cache when checking it,
  detect a waiting update, and activate it only after an explicit user action.
  Never silently reload an objective the owner is typing.
- Offline: show a public offline page. No cached authenticated shell, memory,
  mission, key, API response, generated file, or automatically replayed task.
- Privacy: cached resources must be a small exact public allowlist. API requests,
  mutations, cross-origin fetches and Authorization requests bypass the worker.
- Cache upgrade: remove only old Gaïrus caches, leave unrelated caches intact.
- Verify reconnect and update lifecycle, offline/private API rejection, invalid
  sign-in, desktop/mobile/desktop resize, and absence of new console errors.
- Retain objective/title/note/chat text and cursor during automatic refresh of
  the same view. Clear a successfully saved form, not one still being edited.
- Vercel access, durable storage, actual model/voice/video providers and Slack
  credentials are independent deployment gates. Local PWA checks do not prove
  those integrations work or guarantee continuous execution.

Verification: 122 Python tests passed with isolated data. Browser flows passed
for all original navigation views, memory save/reopen, mission creation, missing
AI provider, invalid login/logout, desktop/mobile resize, real periodic draft
retention, offline/reconnect and explicit waiting-worker update. The latter uses
the isolated `scripts/qa_pwa_server.py`, which serves two worker revisions without
changing production source or mocking provider success. Effective phone install
is not verified; Chromium's ephemeral context reports `in-incognito`.

## Executable agent and free media checks, 2026-10-30

- Keep sign-in, conversations, manual missions, memory, owner checks and logout.
- Add an Agent tab that converts an objective to a bounded executable job.
- The job actually writes Markdown, synthesizes French WAV with Kokoro, and
  renders a narrated MP4 presentation when requested. It is not neural scene
  generation, a voice-cloning service, or a full VIKTOR replacement.
- Validate plans before invoking tools; reject unsupported actions and all
  paid providers. No fallback to a paid endpoint on quota exhaustion.
- Show journal entries only after verified tool output exists.
- Persist finished executions and their real files atomically in private
  storage; previous conversations and unknown state fields remain intact.
- Downloads and audio/video previews use authenticated callback data, never
  public Gradio file URLs. Saved results can be reopened after a restart.
- Exercise real French TTS and FFmpeg output, then browser UI desktop/375px.
- Slack remains unavailable until an authorized Slack application is connected.

## CPU-only tools and commercial target, 2026-10-30

- Preserve all existing private sign-in, Agent, Conversation, Missions, Memory,
  saved files, logout and mobile flows.
- A visible opt-in transforms supplied text without model/GPU inference.
- CPU mode requires an explicit document, voice or narrated-presentation
  format. It must not interpret text as commands, spend money or silently
  switch engines after an AI failure.
- Verify actual CPU-only WAV and MP4 on the deployed server even when GPU quota
  is exhausted. Verify the new API rejects an absent service key.
- Confirm browser mode toggle works both ways, saved CPU files reopen, empty
  text and an automatic format fail clearly, with no new console errors.
- The user targets commercial use and 24/7 autonomy. Neither uptime, all VIKTOR
  capabilities, tenant isolation nor commercial readiness is implied by this
  improvement. No account or paid resource is created.
