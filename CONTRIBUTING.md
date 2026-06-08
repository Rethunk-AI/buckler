# Contributing to Buckler

## Dev setup

```bash
# Clone
git clone https://github.com/Rethunk-AI/buckler.git
cd buckler

# Install Python deps (uv required)
uv sync

# Verify
uv run pytest
uv run ruff check src/ tests/
```

## Version control policy (mandatory)

Buckler contributors and agents follow the same **`/good-version-control`** rules enforced by Buckler's own Git pack:

| Rule | Requirement |
|------|-------------|
| **Staging / commits** | Use `plugin-rethunk-git-rethunk-git` / `batch_commit` (MCP) in Cursor sessions. Never use raw shell `git commit` / `git add` when MCP is available. |
| **If MCP unavailable** | Stop. Surface the error. Do not silently fall back to shell git unless the user explicitly opts in. |
| **Cadence** | Commit in small thematic batches after each coherent unit. Do not defer everything to one "completion" commit. |
| **Paths per commit** | ≤ ~7 paths; split by theme, not file count. |

## Conventional commits

```
type(scope): imperative summary (≤72 chars)

Body: explain why, not what. One logical unit per commit.
```

**Types:** `feat` `fix` `refactor` `perf` `test` `docs` `chore` `ci` `build`

**Scopes:** `core` `adapters` `cli` `packs` `paths` `hooks` `setup` `ci` `docs`

### Examples

```
feat(core): add ask action support in PolicyOutput

The ask action surfaces a confirmation prompt in harnesses that
support interactive mode; deny is used as fallback in non-interactive
contexts.
```

```
feat(packs): add force-push rule to agent-git baseline

git push --force-with-lease is now warn (not deny) at baseline tier;
--force and -f remain deny. Configurable via tier=strict to promote
force-with-lease to deny.
```

## Testing

```bash
# All tests
uv run pytest

# Core evaluator only (no Cursor fixtures)
uv run pytest tests/test_core.py

# Git pack
uv run pytest tests/test_agent_git.py

# Cursor adapter round-trips
uv run pytest tests/test_adapter_cursor.py

# Validate pack YAML (same checks as `buckler validate`)
uv run pytest tests/test_pack_loader.py

# Lint
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type check (matches CI / release)
uv run mypy src/buckler/
```

Coverage is enforced at **100%** (`pytest` is invoked with `--cov-fail-under=100` in CI and local `uv run pytest` via `pyproject.toml`). If you add a module or branch that is hard to exercise, use `# pragma: no cover` **only** for:

- `if __name__ == "__main__":` blocks, and
- platform- or environment-specific branches that are covered elsewhere in the matrix.

Do not use `pragma: no cover` to hide logic that should have a test.

## Adding a new pack

1. Create `packs/<name>.yaml` following [docs/rule-schema.md](docs/rule-schema.md).
2. Add tests in `tests/test_<name>.py`.
3. Document the operator matrix in `docs/<name>.md`.
4. Register the pack in `HUMANS.md` pack table.
5. Update `AGENTS.md` contract-change table if a new trigger or field is introduced.

## Adding a new adapter

1. Create `src/buckler/adapters/<harness>.py` following [docs/adapters/README.md](docs/adapters/README.md).
2. Document the field mapping in `docs/adapters/<harness>.md`.
3. Add golden fixtures in `tests/fixtures/adapters/<harness>/`.
4. Add tests in `tests/test_adapter_<harness>.py`.
5. Update `docs/adapters/README.md` adapter table and `AGENTS.md`.

## CI

GitHub Actions runs on push and pull requests:

- **`ci.yml` `test` job:** mixes OS and Python intentionally — **`ubuntu-latest`** runs **Python 3.11, 3.12, and 3.13** (full minor coverage). **`macos-latest`** and **`windows-latest`** each run **one** representative cell (**Python 3.13**) so we keep cross-platform signal without tripling macOS/Windows minutes.
- The **`shellcheck`** job runs `shellcheck --shell=bash --severity=warning scripts/setup.sh` with **no** `continue-on-error`; warnings fail the workflow.
- **Maintainers:** periodically prove the shellcheck gate is live — push a one-commit branch or draft PR that introduces a deliberate `shellcheck` warning in `scripts/setup.sh`, confirm the **`shellcheck`** job turns red on GitHub Actions, then drop/revert the branch. Locally you can run the same command as CI; exit code must be non-zero when the script violates Shellcheck at `--severity=warning`.
- **`release.yml`:** triggered on version tags; runs the same ruff, format, and mypy gates as `ci.yml`, then `pytest`; builds a tarball, signs with Cosign keyless, attaches to the GitHub Release.

Python versions declared under `Programming Language :: Python :: …` in `pyproject.toml` are checked against `.github/workflows/ci.yml` by `tests/test_ci_matrix_coherence.py`.

**`greenfield-scrub`:** the repo may still carry descriptive “legacy” wording in contract docs (`policy-io`, architecture notes). A CI gate on `greenfield-scrub --fail-on HIGH` is **not** enabled; maintainers run the scrub ad hoc when cleaning deadwood.

## Pull request checklist

- [ ] Tests pass (`uv run pytest`).
- [ ] Lint clean (`uv run ruff check src/ tests/`).
- [ ] Contract canon updated (see [AGENTS.md](AGENTS.md)).
- [ ] Commits follow conventional format in small thematic batches.
- [ ] No raw `git commit` / `git add` in agent-authored work (MCP-only per policy).
