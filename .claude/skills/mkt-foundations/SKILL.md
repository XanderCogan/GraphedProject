---
name: mkt-foundations
description: Shared rules, setup and command reference for marketing engineering with the Graphed CLI (warehouse, tools, secrets, storage, jobs, plugins). Read this before running any other mkt-* skill, or when the user asks to set up Graphed, connect data sources, store API tokens, schedule a marketing job, or check what Graphed can do.
---

# Marketing engineering foundations (Graphed)

Every `mkt-*` workflow skill builds on this file. It covers the operating rules, how to reach Graphed, cost guardrails, and where things live.

## 1. Operating rules

1. **Read from the warehouse; write through platform APIs.** Analytics questions go to the Graphed warehouse using SQL. Platform APIs (Meta Ads, Google Ads, CMS, Instantly) are only for actions: uploading, toggling and publishing. Never pull bulk reporting data straight from ad-platform APIs. That causes rate limits, can break their terms of service (Meta can ban the ad account) and fills your context.
2. **Join through to revenue.** Don't judge a channel from its own platform numbers alone. Join ad data with GA4, CRM sign-ups and Stripe/payments wherever those sources exist.
3. **Use a plugin before building your own.** If a Graphed plugin covers the job (SEO, Google Ads, outbound, ...), use it: `graphed plugins search "<job>"`, then `graphed plugins add <name>`, then follow its staged `AGENT.md`. Graphed also installs its own skills (`/graphed`, `/graphed:plugins:<name>-agent`). If one fits, prefer it to a mkt-* skill.
4. **Keep a record of everything you generate.** For every image, video or script, keep the exact tool id and input JSON, the result id (`trn_…`) and where the output was stored. Use a project Postgres table when a Graphed project exists. Otherwise append to `./outputs/<workflow>/log.jsonl`.
5. **Run long jobs in the background** and keep working on other requests. Tell the user what's running.
6. **Once a workflow works, offer to schedule it** as a Graphed job (section 6). Don't schedule anything without the user's go-ahead.

## 2. Setup check (do this once per session)

Run these in order and stop at the first failure:

```sh
graphed --version                         # missing → npm install -g @graphed-inc/cli
graphed --format json accounts list       # auth error → user runs `graphed login` (needs a paid Graphed plan)
graphed --format json sources list        # which data sources are connected, with their schema_name
```

- If the user has several accounts, ask which one to use. After that, pass `--account <id>` on every command.
- If there's a `graphed.yaml` nearby, the project and account are inferred from it. Otherwise, pass `--project <slug>` for project-scoped commands: tools, secrets, storage, jobs and databases. If there's no project and one is needed, suggest `graphed init <dir> --yes --format json`.
- The CLI ships its own up-to-date docs. When unsure, read them rather than guessing: `graphed docs agents|commands|tools|warehouse|storage|plugins|sdk|manifest`.
- Use `--format json` whenever you'll parse the output.

## 3. Command reference

| Need | Command |
|------|---------|
| See a source's tables | `graphed warehouse schema <schema_name>` |
| Query the warehouse (read-only SQL) | `graphed --format json warehouse query -- '<SQL>'` |
| Find a tool | `graphed tools catalog --query "<keywords>"` |
| Tool input/output schema and price | `graphed tools catalog detail <tool_id>` |
| Run a tool and save the result | `graphed tools run <tool_id> --wait --out <file> --body-file <input.json>` |
| Check or cancel a run | `graphed tools get trn_…` / `graphed tools abort trn_…` |
| Store a file and get a share link | `graphed storage upload <local> <key>` then `graphed storage url <key> --expires-in 3600` |
| Secrets | `graphed secrets list` / `graphed secrets set <NAME>` (prompts for the value) |
| Project database | `graphed databases list` / `graphed databases query --database <name> -- '<SQL>'` |
| Run code with project secrets and credentials | `graphed dev run -- <cmd>` (local) or `graphed exec -- <cmd>` (cloud) |
| Jobs | `graphed jobs list` / `graphed jobs run <name>` |
| Missing capability or broken command | `graphed feedback --kind bug|feature_request "<msg>"` |

**Tool ids** follow these patterns:
- Catalog ids, such as `million-verifier:validate`.
- Any Apify actor: `apify:<owner~actor>`.
- Any Kie.ai model: `kie:<model>`.

The catalog only lists suggestions, so you can swap in any Apify actor or Kie model. Known ids:
- Images: `kie:gpt-image-2-text-to-image`, `kie:gpt-image-2-image-to-image`, `kie:nano-banana-2`, `kie:nano-banana-pro`
- Video: `kie:bytedance/seedance-2-5`, `heygen:videos.avatar_iii`
- UGC talking-head ads: `graphed:ugc.avatar`
- Email verification: `million-verifier:validate` (one address), `million-verifier:bulk` (CSV URL)
- LinkedIn: `apify:apimaestro~linkedin-post-comments-replies-engagements-scraper-no-cookies`, `apify:apimaestro~linkedin-profile-posts`

For anything else (email finding, DataForSEO, ad libraries, Reddit, people lookup, funding/news), search the catalog by keyword first.

**LLM calls from code** (clustering, writing at scale) go through the SDK's OpenRouter proxy. See `graphed docs sdk`.

## 4. Cost guardrails

- 1 Graphed credit = 1 cent. Before any batch run, use `catalog detail` to get the per-call cost, multiply by the number of items, and tell the user the estimate.
- **Ask for confirmation before any run estimated above $5**, or any run over 100 items, unless the user has already set a budget for it.
- After a batch, report the actual cost by adding up `billedCredits` from `graphed tools get`.
- Use `--idempotency-key` on retries so a failed loop doesn't pay twice.

## 5. Secrets

- Platform tokens such as `META_ACCESS_TOKEN`, `GOOGLE_ADS_*`, `INSTANTLY_API_KEY` and the CMS token go into Graphed secrets with `graphed secrets set <NAME>`. Never put them in files, `graphed.yaml`, chat output or URLs.
- Code reads them as environment variables when run through `graphed dev run` or `graphed exec`.
- Never print `env` inside `graphed exec`, because it leaks secrets into the logs.
- Don't declare Graphed's own platform credentials as secrets. The runtime injects them.

### Meta Ads token (one-time, done by the user in Meta Business Settings)
1. Business Settings → create a developer app. Use cases: manage ads with the Marketing API, manage ads with Ads Manager, and connect the business portfolio.
2. Finish the requirements and add a privacy-policy URL.
3. Create a **system user**, assign it the ad accounts and pages, and generate a token with `ads_management` and `ads_read`. This token doesn't expire.
4. Store it: `graphed secrets set META_ACCESS_TOKEN` (the user pastes the value at the prompt). Also store `META_AD_ACCOUNT_ID` (`act_…`).

## 6. Scheduling a workflow

To run a working workflow on its own schedule:

1. Make sure it's a script in a Graphed project. If there's no project, run `graphed init`.
2. Add it to `graphed.yaml` under `jobs.<name>` with `command` and `schedule.cron` (UTC).
3. Run `graphed deploy --dry-run`, then `graphed deploy`. Trigger it once with `graphed jobs run <name>` and check `graphed logs --job <name>`.

Services and dashboards are private behind the Graphed login by default. Only add `public.paths` for webhooks.

## 7. Workflow skills

| Skill | Use for |
|-------|---------|
| `mkt-ad-creative` | Generate static ad images or variations |
| `mkt-meta-ads-manage` | Upload ads to a Meta ad set, turn ads on/off, move ads |
| `mkt-voc-research` | Pull pain points, desired outcomes and objections from Reddit |
| `mkt-analytics` | Answer business questions with SQL across sources |
| `mkt-dashboard` | Build a shareable, private live dashboard |
| `mkt-linkedin-to-outbound` | Turn LinkedIn post engagers into a verified email list |
| `mkt-seo-keywords` | Research "vs" keywords, page-two opportunities and keyword expansion |
| `mkt-seo-publish` | Research, write and publish a blog post for a keyword |
| `mkt-ugc-scripts` | Write UGC / AI-avatar ad scripts and optionally render them |
| `mkt-competitor-ads` | Monitor competitors' ad libraries |
