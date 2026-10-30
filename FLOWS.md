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
