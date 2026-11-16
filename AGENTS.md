# AGENTS.md — Google Photos to iCloud Migration

> Read this first if you are an AI agent working in this repo.

## What This Is

A macOS terminal tool that migrates photos and videos from a Google Takeout export to iCloud Photos, keeping metadata and albums. It runs locally on macOS only (it needs PhotoKit access to a real iCloud account).

## Layout

- `google_photos_icloud_migration/` — the Python package
- `scripts/`, `web/`, `docs/`, `tests/` — helpers, the web UI, docs and tests
- `config.yaml.example`, `config_schema.json` — configuration
- `Makefile`, `pyproject.toml`, `requirements*.txt` — build and dependencies
- `_run-output-2025-12/` — output from a past run

## Project Notes

Run the tests before and after a change (see the `Makefile` and `README.md`). Never run it against a real iCloud library without Skip's go-ahead.

## Working Rules

- Skip Shean (16Wells) owns scope and design decisions; ask before widening the scope of a change.
- Make small, reviewable changes, one concern at a time, and re-read the diff before calling it done.
- Verify by running the thing where you can; if you can't run it here, say so instead of claiming success.
- Never commit credentials, API keys or exported personal data. Check staged changes first.
- Changes go on a branch with a draft pull request; don't push straight to `main`.
