# Gairus: cloud repair and deployment handoff

Prepared 2026-10-25 against main commit c4e8ead from
[zyrvion/Gairus-](https://github.com/zyrvion/Gairus-).
This repair branch contains proposed changes for review, not a production
deployment. Main must not be merged or deployed without the owner's approval.

## Verified results

49 unit/regression tests pass on Python 3.12.15 and Python 3.14, including six
deployment-configuration checks for persistence, secrets and manual rollout.
All non-backup Python source parses, JavaScript syntax and Bash syntax pass.
Browser checks at desktop and 375px covered owner sign-in, unauthorized API
rejection, mission creation, memory saving, page navigation, truthful missing-AI
status and chat's no-provider response. No browser page errors or horizontal
overflow were observed in those checks.

Live provider calls, Slack credentials, Docker image build, permanent hosting,
DNS edits, backup restoration and VIKTOR export are not verified.

## Repairs and safeguards

- Removed shell fragments accidentally pasted into Python modules and completed
  truncated syntax. Historical `core.autonomous_runtime` remains a legacy
  partial implementation: its missing tools explicitly raise NotImplementedError.
  Parsing does not mean those historical runtimes are production-certified.
- Restored audit logging on allowed and blocked gateway actions.
- Repaired an outdated approval test using an explicit human test fixture.
  The application does not invent a production human approver.
- Added fail-closed owner authentication to the web API. Slack signatures and
  the existing separately scoped ORTA bearer token retain their own validators.
- Added an owner sign-in screen. The owner key is kept in tab memory, not browser
  storage. Chat history is reloaded from the authenticated server, not browser storage.
- Displayed AI-provider configuration honestly instead of always saying active.
- Protected write tools against model-supplied approval bypasses, repaired
  native-tool calling conventions and stopped treating failed tools as completed.
- Prevented self-code tools from opening environment secrets, databases or Git metadata.
- Fixed direct Flask startup so all routes are registered before serving.
- Supervised web and optional Slack processes and respected Gunicorn configuration.
- Excluded live databases, logs, secrets and repair backups from Docker builds.
- Added persistent Slack memory and an optional Caddy HTTPS deployment profile.
- Added regression tests and a proposed pull-request test workflow in
  `docs/CI_PROPOSAL.md`. Existing GitHub Actions workflow files are unchanged.
  The current authorization does not include workflow-file modification, and
  no additional OAuth permissions were requested
  ([GitHub scope documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)).

## Production topology

Suggested Gairus entry point: `gairus.zyrvion.io`. Do not change the apex,
`www`, MX, SPF, DKIM or other working DNS records.
DNS nameservers currently resolve to Spaceship
([DNS response](https://dns.google/resolve?name=zyrvion.io&type=NS)).

Use an authorized cloud Linux server or container service that supports
long-lived processes and persistent volumes. The application's current SQLite,
background scheduling and Slack workers are not migrated merely by publishing
the frontend alongside the existing Zyrvion site.

`deploy/compose.cloud.yml` provides the application, Caddy HTTPS and named
volumes. It has not been Docker-built or launched here because Docker is not
available. YAML parsing and application startup have been tested separately.
The Render Blueprint now prepares a Docker service with a 1 GB persistent disk,
explicit data paths, generated secrets and automatic deploys disabled.
See `docs/RENDER_DEPLOYMENT.md` for the selected topology, base budget,
account-approval requirements and rollout checks. No Render resource has been
created or purchased, and persistence still requires a real deployment test.

## Required authorized access

- GitHub write access for the repair branch and pull request was authorized
  directly through GitHub CLI as `zyrvion`; no Perplexity connector or deploy
  key was used. This does not authorize a main-branch merge or production deployment.
- A chosen existing cloud account/server. Do not buy resources without approval.
- Spaceship DNS access, limited to the new Gairus hostname.
- Provider API credentials entered through secure credentials, not Slack.
- A new high-entropy owner access key of at least 32 characters.
- Slack bot/app/signing credentials if Slack operation is required.

After access is granted:

1. Back up current databases and export the old Slack memory before any migration.
2. Review the repair branch; do not overwrite main or discard unrelated changes.
3. Provision or select the authorized host; configure secrets outside Git.
4. Start with autonomy disabled and approvals enabled.
5. Mount all runtime data at `/app/data` and import verified backups there.
6. Create only the approved hostname A/AAAA records for that host.
7. Run health, authenticated API, provider, Slack and HTTPS tests.
8. Restart/redeploy and verify mission and memory persistence.
9. Configure daily off-host backups and test restore before enabling autonomy.

Do not purge committed data/history without separate approval. Adding ignore
rules does not remove previously committed database and audit files. Inspect
that history privately and rotate any exposed credential before production.

## VIKTOR and the field application

VIKTOR's login page was inspected but no sign-in or export was performed.
Retrieve only the user's own projects, documents and data, not proprietary
platform code. Inventory source availability, dependencies, databases, files,
credentials to rotate, domain bindings and scheduled tasks before migration.
Do not delete the source service until the imported projects and backups are
verified independently.

The field application is the next phase requested by the owner; it is not
claimed as built, imported or hosted in this repair.
