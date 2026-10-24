# Customer brief: Halcyon Botanicals (fictional)

Modeled on Graphed's own customer archetype: a founder-led Shopify DTC brand running most of its growth on Meta, like the sunflowersober.com testimonial ("deployed four agents in under an hour... paid ads, content, and SEO"). Halcyon is invented. Nothing here describes a real company.

## Who they are

- **What they sell:** non-alcoholic functional aperitifs (adaptogens, no sugar). Three SKUs at $38 to $42 per bottle, a 3-pack at $99, and a monthly subscription through Recharge at 15% off.
- **Where:** Austin, TX. Ships US only. Shopify (not Plus). Launched October 2024, so 24 months ago. Customers are wherever the ads deliver: California, New York and Texas lead, then a long tail of a couple hundred cities.
- **Size:** about $3.4M annualized run rate. Between 2,600 and 4,000 orders a month, growing. AOV around $72 including tax and shipping. Roughly 43% of orders are subscription renewals.
- **Team:** founder (ex-CPG brand manager), one marketing manager who runs email and content, and a freelance media buyer who manages Meta for a flat monthly fee. No one technical in-house.
- **Stack:** Shopify, Meta Ads, Google Ads (small, branded search only), GA4, Klaviyo, Recharge, Stripe via Shopify Payments, a Google Sheet the founder updates by hand every Monday.

## Channel mix (last 90 days, their numbers)

| Channel | Share of spend | What they believe it does |
|---|---|---|
| Meta Ads | 78% | Nearly all new customers |
| Google Ads (brand) | 9% | Catches people who saw a Meta ad |
| Klaviyo | fixed cost | Repeat purchases and subscription saves |
| Influencer seeding | 13% | Awareness, untracked |

## The problem, in the founder's words

"We're spending 50% more on Meta than in April. Same creative team, same media buyer. My spreadsheet says cost per new customer only went from about $26 to about $30, and the media buyer says ROAS in Ads Manager is 3.5 to 4 so it's fine. But our bank account disagrees. Shopify says we're growing, Meta says we're growing, and I'm making less money. I don't know which number to trust and I don't have time to learn SQL. Can you just tell me what's actually happening and then make it stop?"

(The founder's spreadsheet divides Meta spend by all new customers in Shopify, including organic buyers and, since August, the coupon-code buyers. Meta spend divided by customers Meta actually brought in went from about $37 in April to about $60 in September.)

## What they asked for on the discovery call

1. One place where Shopify, Meta and Klaviyo numbers agree.
2. Know the real cost of a new customer, not a repeat buyer the pixel re-counted.
3. Stop guessing which creative angles to test next.
4. The marketing manager wants to spend less time building the Monday spreadsheet.

## What's actually wrong (planted for the work sample)

These are the issues an FDE would find in the first week. Each one is seeded into the synthetic data so the dashboard and onboarding checks can catch it.

1. **Double-counted purchases in Meta.** On June 12 the media buyer installed the Shopify Meta sales channel while the old manual pixel was still live. Meta-reported purchases, purchase value, add-to-carts and checkouts all jump about 60% from that date forward with no change in Shopify orders. Ads Manager ROAS near 4 is really about 2.5, and on new customers alone it is near 1.
2. **Retargeting counts subscribers as conversions.** The "Retargeting - Warm" ad set serves to past purchasers. Their renewals get attributed to Meta, so blended CAC looks fine while new-customer CAC climbs.
3. **UTM naming changed in July.** On July 15 campaigns were renamed from `prospecting_broad_v1` style to `[P] Prospecting | Broad` style and the UTM template was switched to `{{campaign.name}}`. GA4 and Shopify landing sites show the same campaign as two. Meta's own reports show only the new name for all history.
4. **A discount code leaked.** The influencer code `FERN20` landed on coupon sites around August 10. Redemptions went from about 25 a month to 200 to 300, AOV on those orders is about $12 lower and blended AOV drifted down, and most of those orders show up as "direct" or coupon-site referral in Shopify, inflating organic.
5. **Creative fatigue on the top prospecting ad.** Seven-day frequency on the best-performing ad crossed 4.0 in the second half of August and its CTR fell by half, but spend kept rising because the media buyer scaled the winner. Daily frequency in the daily insights rows never gets near 4; the signal is only in the weekly pull.

## Data notes

- Shopify tables carry the full history since launch, so `orders_count` and `total_spent` on customers reconcile to the orders table. Meta, Google, GA4, Klaviyo and the Monday sheet start at 2026-04-01, the connector backfill window.
- Timestamps are UTC. The store runs on America/Chicago. Subscription renewals batch-charge around 05:00 store time.
- Emails are anonymized to `customer{id}@example.com`. Everything else (cities, tax, refunds, promos, creative rotation, list growth) is simulated to look like a real account. `data/realism-audit.md` lists what was checked.

## What a successful deployment looks like

- Shopify, Meta, GA4 and Klaviyo synced into the Graphed warehouse.
- A dashboard the founder opens on Monday instead of the spreadsheet: true new-customer CAC, blended vs new ROAS, Meta-reported vs Shopify-verified purchases, subscription vs one-time split, discount code leakage.
- Facebook Ads agent deployed and scoped to prospecting campaigns only, with the frequency and CTR thresholds from issue 5.
- Static-ads skill run against the three angles their current creative doesn't cover.
- A one-page "what we found" note to the founder, plus a fix list for the media buyer.
