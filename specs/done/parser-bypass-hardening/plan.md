# Plan — parser-bypass-hardening

## Overview

Harden `buckler.core` shell segmentation and policy expansion so common agent bypasses (`&`, `|`, newlines, command substitution, `bash -c`, env prefixes) are evaluated under the same deny rules, with a strict depth cap and fail-closed behavior.

## Verification

- `uv run pytest` at 100% coverage.
- Redteam file `tests/test_agent_git_redteam.py`.
