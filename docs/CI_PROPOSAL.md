# Proposed pull-request tests

This is a proposal, not an active workflow. Existing files under
`.github/workflows` remain unchanged in this repair branch.

The current GitHub authorization can publish repository code and pull requests,
but it does not include the `workflow` scope. Adding or updating GitHub Actions
workflow files requires that separate permission
([GitHub documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)).
No broader authorization was requested just to publish this fix.

An authorized repository owner can review and add the following as
`.github/workflows/gairus-tests.yml` later. It runs tests only, has no deployment
job and does not consume production SSH or provider credentials.

```yaml
name: Gairus regression tests
on:
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.14"]
    env:
      GAIRUS_AUTONOMY: "false"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m pip install -r requirements.txt pytest
      - run: python -m compileall -q -x 'backup_repair' .
      - run: python -m pytest tests -q
      - run: git diff --check
```

Before relying on this workflow, run it in the repository and inspect its result.
The 43 tests documented in this repair were run in the cloud working environment,
not by an already-enabled GitHub Actions run.
