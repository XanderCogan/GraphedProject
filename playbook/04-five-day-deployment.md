# Five-day deployment runbook

Graphed promises "marketing agents live in 5 business days." This is the day-by-day that makes it true, and the version of it that gets a second deployment done in two days once the first one has been through it.

The rule underneath all of it: **find what's wrong with the numbers before you touch the marketing.** A customer who watches you catch a double-fired pixel on day two trusts the agent you turn on day five. A customer whose agent optimizes toward a doubled ROAS fires you in month two.

## Day 1: kickoff and access

- Run the kickoff call (01). Leave with Shopify and Meta access in motion.
- Connect Shopify and Meta in Graphed the moment access lands. Backfill runs overnight.
- Write the dated hypothesis list from "what changed in the last six months."
- Create the project: `graphed init <customer-slug> --yes`. Commit. Nothing deployed yet.

**Done when:** `graphed sources list` shows Shopify and Meta with schema names, and the hypothesis list has at least three dated entries.

## Day 2: reconcile

- Run every query in 03 against the synced data. Paste results into the deployment log with the query.
- For each disagreement between sources, find the date it started and match it to the hypothesis list.
- Connect GA4, Klaviyo, Google Ads, and the founder's spreadsheet as a Google Sheets source.
- Draft the findings note (05). Numbers only from queries you ran.

**Done when:** you can say in one sentence what the customer's real new-customer CAC is, how far it is from the number they quoted, and why.

## Day 3: dashboard

- Build the dashboard route in the project, following the Graphed analytics-dashboard skill. Query the warehouse through the SDK, inline SVG charts, no chart library.
- Panels, in this order, because this is the order the founder will read:
  1. New-customer CAC by week, true, with their old number as a second line.
  2. Meta-reported purchases vs Shopify orders, with the step change marked.
  3. New vs returning vs subscription renewal orders.
  4. Spend and new customers by campaign, with renamed campaigns merged.
  5. Discount code redemptions and AOV.
  6. Creative fatigue table: frequency, CTR vs launch, flag.
- Deploy: `graphed deploy`. Private by default behind the Graphed gateway. Send the launch URL.

**Done when:** the founder has opened it. Not when it's deployed. Ask them to open it on the call.

## Day 4: findings call and agent scope

- Thirty minutes. Walk the dashboard top to bottom. Each panel is one finding and one fix.
- Agree the scope for the first agent in writing. For a Meta-heavy DTC brand that's almost always the Facebook Ads agent, read-only, scoped to prospecting campaigns, with a frequency ceiling and a CTR floor taken from the fatigue table.
- Agree what the agent is not allowed to touch. Retargeting, budgets above a cap, anything with the subscription offer.
- Send the fix list to the media buyer: remove the duplicate pixel, add event deduplication, stop scaling the fatigued ad, kill the leaked code and reissue.

**Done when:** scope is in writing and the founder has replied "yes."

## Day 5: first agent live

- `graphed plugins add <agent>` and follow the staged `AGENT.md`. Set secrets with `graphed secrets set`. Never in files.
- Run read-only for the first week: the agent writes recommendations to the dashboard, a human applies them.
- Schedule the daily job. Confirm the first run in `graphed logs`.
- Send the one-page findings note (05) with the dashboard link and the agent's first recommendation.

**Done when:** the daily job has run once on schedule and the founder has seen its output.

## Week 2 onward

- Flip the agent from recommend to act, one permission at a time, starting with pausing fatigued ads.
- Add the static-ads skill against the angles the current creative doesn't cover.
- Weekly fifteen-minute check-in. Dashboard first, then what the agent did, then what broke.
- Feed every platform gap back: `graphed feedback`. The FDE is the only person who sees what breaks at customers.

## Why the second deployment takes two days

- Kickoff script is written. Access checklist is written. Both reused as is.
- The seven sanity queries run in ten minutes against any Shopify + Meta customer.
- The dashboard route is a template: swap the schema name, keep the panels.
- Agent scope template exists. Only the thresholds change.
- What's left is the part that can't be templated: reading the customer's data and finding what's actually wrong. That's the job.
