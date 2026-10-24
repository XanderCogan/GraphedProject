# Access and connector checklist

Send this to the customer during the kickoff call. Each item says who does it, how long it takes, and what blocks if it's missing. Order matters: Shopify and Meta gate everything else, so start those first.

## For the customer

| # | Platform | What to do | Time | Blocks |
|---|----------|------------|------|--------|
| 1 | Shopify | Settings → Users → Collaborators → add Graphed's collaborator request code. Permissions: Orders, Customers, Products, Analytics, Apps. | 5 min, instant | Everything. No Shopify, no revenue truth. |
| 2 | Meta | Business Settings → People → add FDE email as Employee → assign Ad Account (Analyst is enough for sync) and Pixel/Dataset (view). | 10 min, instant | Ads data, pixel audit. |
| 3 | Google Analytics 4 | Admin → Property Access → add FDE email as Viewer. Send the property ID (starts with `properties/`). | 3 min | Session and attribution reconciliation. |
| 4 | Google Ads | Tools → Access → invite FDE email, Read only. Send the 10-digit customer ID. | 5 min, needs email accept | Brand spend. Low priority if under 10% of spend. |
| 5 | Klaviyo | Settings → Users → add FDE as Analyst. Send the account's attribution window setting (Settings → Attribution). | 5 min | Email revenue overlap. |
| 6 | Subscription app (Recharge, Skio, etc.) | Usually readable through Shopify orders by `source_name` or tags. Only needed directly if renewals aren't tagged in Shopify. | 5 min if needed | Renewal split. |
| 7 | The spreadsheet | Share the actual Google Sheet with view access. | 1 min | Reconciling what they believe against what's true. |
| 8 | Media buyer | Intro email to the buyer or agency. Ask them to forward their last three reports. | 2 min | Their methodology, which is usually where the number went wrong. |

## For the FDE: connect in Graphed

Each source: Graphed → Warehouse → Add source → pick connector → OAuth or paste credentials. Sync starts on connect and lands in its own warehouse schema, which `graphed sources list` reports once ready.

```sh
graphed --format json sources list --account <account_id>
graphed sources catalog --query shopify
graphed warehouse schema <schema_name>
```

Connect in this order and don't move on until the row shows a schema name:

1. Shopify (orders, customers, products, line items). Initial backfill can take an hour for 50k+ orders.
2. Meta Ads (insights at ad level, daily). Pull 13 months if the account allows it.
3. GA4 (traffic acquisition by source/medium/campaign, daily).
4. Klaviyo.
5. Google Ads.
6. Google Sheets, pointed at the founder's spreadsheet. Yes, really. Loading their spreadsheet into the warehouse is how you show them, in one query, exactly where their number diverges from the truth.

For a customer whose data isn't in a supported source yet, or for a sandbox, the Postgres connector takes any table you can write. That's how this work sample's Halcyon data was loaded.

## First hour after sync: five checks before you trust any number

Run these before building anything. The SQL is in `03-data-sanity-checks.sql`.

1. **Row counts by month, per source.** A month with half the rows is a sync gap or a reconnect. Fix before analysis.
2. **Shopify orders vs platform-reported purchases.** Meta plus Google plus Klaviyo claimed purchases should land between 80% and 180% of Shopify orders. Above that something fires twice. A sudden step change in the ratio is a dated event: find out what was installed that week.
3. **Campaign name continuity.** Pull distinct `utm_campaign` values by month from Shopify landing sites and from GA4. A set that changes mid-period means renames. Build a mapping table before any campaign-level chart.
4. **Discount code concentration.** Redemptions per code per month, with AOV and referrer. A code that triples with falling AOV and coupon-site referrers has leaked.
5. **Frequency and CTR by ad, by week.** Any ad with frequency above 3.5 and CTR down more than 40% from its first four weeks is fatigued, regardless of what its reported CPA says.

Write what you find into the deployment log with the query used. The customer will ask how you know.

## What never to ask for

Passwords, card details, export files emailed around. If a platform has no collaborator role, the customer runs the export themselves on a call with you.
