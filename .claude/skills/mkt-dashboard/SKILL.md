---
name: mkt-dashboard
description: Build a shareable, team-only dashboard or review page (live warehouse metrics, ad creative approval boards) and iterate on it - chart types, date-range pickers, filters. Use when the user asks for a dashboard, report page, artifact, shareable view, or a page to review/approve ads.
---

# Shareable dashboard

Read `.claude/skills/mkt-foundations/SKILL.md` first. The data comes from `mkt-analytics` queries.

## Pick the hosting
- **Live and team-only (default for real use):** a Graphed project service. `graphed init <dir> --yes` creates a Next.js dashboard, Postgres and a cron job. Services are private behind the Graphed login, so only the team can open them. Data is queried live with the SDK (`new Graphed()` → warehouse), so it stays current with the hourly sync.
- **Quick snapshot to look at or share once:** a single static HTML page with the query results embedded, published as a Claude artifact (private by default) or uploaded with `graphed storage upload` plus `graphed storage url` (the link expires within an hour). Say plainly that it doesn't update itself.

Ask which one only if it's unclear. A one-off question → snapshot. "For the team" or "keep updated" → live.

## Steps (live)
1. Collect the queries (from `mkt-analytics` or new ones). Each chart gets one SQL query that takes date-range parameters.
2. Scaffold or reuse a Graphed project. Add a page with:
   - A KPI row (spend, sign-ups, revenue, CAC)
   - A time-series chart with a date-range picker (default last 30 days)
   - Breakdown tables (by channel, campaign, ad)
   Query server-side through the SDK and never expose SQL to the browser.
3. Test locally with `graphed dev run -- npm run dev`.
4. Deploy: `graphed deploy --dry-run`, then `graphed deploy`. Get the URL with `graphed --format json services list`. Tell the user teammates need Graphed access to open it.

## Steps (creative review board)
A page showing each generated ad (image from storage, headline, angle, prompt) with Approve/Reject buttons. In a Graphed project, decisions go into a Postgres table, so `mkt-meta-ads-manage` can upload only approved ads.

## Iterating
Handle requests like "make spend by month a line chart," "add a date-range picker" or "split by campaign" as small edits. Redeploy or republish, and confirm the same URL still works.

## Chart choices
- Line: trends over time.
- Bar: comparing categories.
- Table: anything with more than 6 categories or exact values.
- Keep units visible ($, %, counts). Note the data's freshness (last sync time) on the page.
