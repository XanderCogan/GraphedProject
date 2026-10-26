# Halcyon Botanicals

Marketing software running on [Graphed](https://graphed.com): a Postgres
database, cron jobs, and a dashboard, all deployed from `graphed.yaml`.

## Local development

Requires Docker and Node 20.12+.

```bash
docker compose up -d          # local Postgres on :5432
npm install                   # one install for all packages (npm workspaces)
npm run db:migrate            # apply packages/core/src/migrations/*.ts
npm run dev                   # dashboard on http://localhost:3000
npm run job:example-daily     # run the cron job against the same local DB
graphed dev run -- npm run job:meta-ads-daily   # the agent, with warehouse + LLM credentials injected
```

`graphed init` already wrote a `.env` with the local `DATABASE_URL`. Reset
everything with `npm run db:reset`.

## Deploy

```bash
graphed deploy
```

The first deploy provisions the `primary` database and wires `DATABASE_URL`
into every service/job. Read logs with `graphed logs --service dashboard` or `graphed logs --job meta-ads-daily`.

## What runs here

- `dashboard` service: the Monday board at `/monday` and the agent page at `/meta-ads`. Both read the warehouse schema named by the `WAREHOUSE_SCHEMA` secret.
- `meta-ads-daily` job (8:00 America/Chicago): the Meta ads agent in `packages/core/src/meta-ads/`. Scope and thresholds live in `clients/meta-ads/client.config.json`. Recommend-only; `writes.enabled` stays false until a Meta credential exists.
- `example-daily` job: the scaffold's heartbeat, left in place.

## Add capabilities

```bash
graphed plugins list                 # browse the registry
graphed plugins add seo              # stage a kit into .graphed/plugins/seo
```

`plugins add` does not modify your code — it stages an integration kit
(reference source + `AGENT.md` runbook) that your coding agent follows to
wire the capability into this repo. See `graphed docs plugins`.

## Layout

One npm workspace, three packages:

```
graphed.yaml                # services, jobs, databases — the whole system definition
packages/
  core/                     # @app/core — shared library: env config, Kysely db, domain logic
    src/migrations/         # numbered TS migrations (up/down), run by `npm run db:migrate`
    src/db/                 # getDb() + the single Database type registry
    src/config.ts           # env loading (.env walk-up) + zod-validated config
    src/warehouse.ts        # the Monday board's seven ClickHouse queries
    src/meta-ads/           # the agent: config, warehouse reads, rules, brief, store, run
  jobs/                     # @app/jobs — cron entrypoints, one thin file per job
  dashboard/                # @app/dashboard — Next.js App Router
    app/                    # routes; one folder per capability
    lib/plugins.ts          # nav registry — plugins add one entry here
```

Domain logic lives in `packages/core` so jobs and dashboard API routes call
the same functions. Job files in `packages/jobs/src/` are thin: read config,
call core, exit.
