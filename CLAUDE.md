# Notes for coding agents

This is a public repository: a forward-deployed-engineer work sample built on Graphed for a fictional customer, Halcyon Botanicals. Nothing sensitive belongs here.

## Layout

- `customer/brief.md` — the customer, their stack, their complaint, and the answer key for the planted data problems.
- `playbook/` — kickoff script, access checklist, sanity-check SQL (ClickHouse), five-day runbook, findings-note template.
- `data/generator/generate.py` — deterministic synthetic data; `data/load_supabase.py` loads it into Postgres for the Graphed connector.
- `halcyon/` — the Graphed Cloud project (`graphed.yaml`, Next.js dashboard, `@graphed-inc/sdk` queries in `packages/core/src/warehouse.ts`). It has its own `AGENTS.md`.

## Working notes

Prep and practice material is kept out of this repo in a separate private repository, `XanderCogan/graphed-prep`. If you have access, clone it alongside and read `call-crib.md` and `glossary-qa.md` first. Never copy its contents here.

## Rules

- `private/` and `CLAUDE.local.md` are gitignored on purpose. Never add them.
- Check `git status` before any push. Ask before any force-push.
- Graphed CLI commands need a paid plan; see the README for the current blocker.
