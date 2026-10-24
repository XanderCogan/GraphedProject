# Halcyon Botanicals on Graphed: a forward-deployed engineer work sample

One customer taken from kickoff call to live dashboard on Graphed, plus the playbook that makes the next customer take two days instead of five.

Built in a day for Graphed's first FDE role. The customer is fictional. The pipes are real: Graphed CLI, Graphed warehouse (ClickHouse), a Graphed Cloud project deployed from `graphed.yaml`, and `@graphed-inc/sdk` for every query.

## The customer

[Halcyon Botanicals](customer/brief.md) is a founder-led Shopify brand selling non-alcoholic aperitifs, about $3.4M a year, 78% of spend on Meta. The founder's complaint: "We're spending 50% more on Meta than in April and I'm making less money, but Ads Manager says ROAS is fine and my spreadsheet says CAC barely moved."

Five things are wrong with their numbers, each planted in the data on a specific date so the dashboard and the sanity checks can catch them:

1. A duplicate Meta pixel from June 12 inflating every Ads Manager number by about 60%.
2. A retargeting ad set that counts subscription renewals as conversions.
3. A July 15 campaign rename that split every campaign in two in GA4 and the spreadsheet.
4. An influencer discount code that leaked to coupon sites on August 10.
5. The top prospecting ad fatiguing in August while its budget kept rising.

The founder's spreadsheet is in the data too, with their arithmetic, so the dashboard can show exactly where their number diverges from the truth.

## What's here

| Path | What it is |
|---|---|
| `customer/brief.md` | The customer, their stack, their complaint in their words, and the answer key. |
| `playbook/01-kickoff-call.md` | Thirty-minute kickoff script. Leave with access and the real problem. |
| `playbook/02-access-and-connectors.md` | What to ask the customer for, in what order, and the five checks to run before trusting any number. |
| `playbook/03-data-sanity-checks.sql` | Seven ClickHouse queries that find each planted problem. Reusable on any Shopify + Meta customer. |
| `playbook/04-five-day-deployment.md` | Day-by-day runbook, and why deployment two takes two days. |
| `playbook/05-findings-note-template.md` | The one-page note to the founder, blank and filled in for Halcyon. |
| `data/generator/generate.py` | Deterministic generator for 24 months of Shopify history and 7 months of Meta, Google Ads, GA4, Klaviyo and spreadsheet exports. |
| `data/realism-audit.md` | 31 ways the first version would have been spotted as synthetic, and what changed. |
| `data/load_supabase.py` | Loads the CSVs into Postgres, which Graphed's Postgres connector syncs into the warehouse. |
| `halcyon/` | The Graphed Cloud project. `packages/core/src/warehouse.ts` holds every query. `packages/dashboard/app/monday/` is the board. |

## The Monday board

Six panels in the order the founder will read them, each naming the table it came from:

1. True new-customer CAC by week against the spreadsheet's number.
2. Meta-reported purchases per Shopify order, 7-day average, with the June 12 step marked.
3. Orders split into new, returning and renewal, next to reported CPA by ad set.
4. Creative fatigue table from the weekly insights pull, because 7-day frequency can't be computed from daily rows.
5. FERN20 redemptions per week with coupon-site referrals.
6. Orders by utm_campaign showing each campaign under two names.

## Run it

```bash
# Data
python data/generator/generate.py
cp .env.example .env            # SUPABASE_DB_URL, GRAPHED_TOKEN
python data/load_supabase.py --drop

# Graphed: connect the Supabase Postgres as a source in the Graphed app, then
graphed sources list            # note the schema_name for the halcyon tables
graphed secrets set WAREHOUSE_SCHEMA --project halcyon-botanicals

# Dashboard
cd halcyon && npm install
graphed dev run -- npm run dev  # local, with warehouse credentials injected
graphed deploy                  # cloud, private behind the Graphed gateway
```

## What I'd do next with a real customer

- Flip the Facebook Ads agent from recommend to act, one permission at a time, starting with pausing fatigued ads.
- Run the static-ads skill against the three angles the current creative doesn't cover.
- Load the founder's actual Google Sheet through the Sheets connector so the reconciliation panel runs on their live spreadsheet.
- Send `graphed feedback` for the gaps I hit: no 7-day frequency without a separate weekly pull, and no campaign-rename history in the Meta tables.
