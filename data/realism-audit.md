# Realism audit of the Halcyon synthetic data

Steelman: "this data is fake and a skeptical FDE or founder would notice." Every item was checked against the CSVs in `data/out/`, not inferred from the generator. The v2 column is what the 2026-10-24 generator produced; the v3 column is what the current generator produces. Numbers are measured from the files.

Severity: **A** breaks a check a real onboarding would run or contradicts how the source system works. **B** a statistical fingerprint a careful reviewer would catch in minutes. **C** brief-vs-data mismatch.

## A. Breaks a real check or contradicts the source system

| # | Flaw in v2 | v3 |
|---|---|---|
| 1 | Orders started 2026-04-01 but 13,800 customers carried ~25,000 historical orders that did not exist. `count(orders) = orders_count` failed for 60% of customers. | Simulated from launch (2024-10-02). 48.6k orders, 20.7k customers, every `orders_count` and `total_spent` reconciles. Platform exports start 2026-04-01 (connector backfill window). |
| 2 | Meta `purchases > initiate_checkout` in 75% of rows. Pixel double-fire inflated purchases only. | Checkout and add-to-cart derived from purchases with noise; zero inverted rows. The Jun 12 double-fire multiplies ATC and IC too, as the Shopify channel would. |
| 3 | GA4 recorded subscription renewals (server-side Recharge charges) as sessions and purchases; GA4 captured 93% of all Shopify orders. | Renewals never reach GA4. GA4 purchases are 93% of non-renewal orders, about 52% of all orders. |
| 4 | GA4 paid-social sessions were 3.6x Meta link clicks; per-medium CVR was a hard-coded constant. | Paid sessions are 84% of Meta link clicks with noise (660 vs 790 per day). CVR falls out: paid social 3.6%, organic 1.9%, direct 1.0%, brand cpc 8%. |
| 5 | Customer `created_at` was after `first_order_at` for 3,464 customers. | Customer is created seconds before the first order, always. |
| 6 | Flat 8.25% tax everywhere including Oregon; 54 distinct order totals. | Per-state combined rates with a per-city offset, zero in OR/MT/NH/DE. 6,100+ distinct totals. |
| 7 | 15 cities at a uniform share each. | 240 cities weighted by metro population with a mild coastal skew. Top states CA 20%, NY 17%, TX 12.5%. An online brand's geography follows ad delivery, not its HQ; "Brooklyn, NY" is kept because that is how Shopify stores it. |

## B. Statistical fingerprints

| # | Flaw in v2 | v3 |
|---|---|---|
| 8 | Zero refunds, cancellations, voids. | 1.5% refunded, 0.7% partially refunded, 0.5% cancelled (voided or refunded, `cancelled_at` set, no fulfillment). Fulfillment lags 0.3 to 5 days; last 3 days unfulfilled. Platforms still count refunded orders, as they do in reality. |
| 9 | Flat SKU mix (27.8 / 27.9 / 28.0%). | Hero SKU: Rosemary Fig 48% of bottle lines, Citrus 30%, Pear 22%. |
| 10 | No promotions. Web AOV within $1.40 every month. | WELCOME10, SAVE10 (abandoned cart), two BFCMs, two Dry Januarys, Memorial Day, July 4, Labor Day sales with lifted demand and bigger baskets. |
| 11 | No seasonality; a straight-line order count. | Summer high, Dry January spike (it is a non-alcoholic brand), late-December lull, BFCM steps. |
| 12 | Klaviyo sent a campaign every day to a randomly sized 14k to 19.5k list; four flows at identical 180 to 420 recipients/day. | Campaigns Tue/Fri plus promo days with real subject lines. List grows from 9.8k to 17.7k and shrinks with every send's unsubscribes. Flow recipients come from triggers: welcome = that day's opt-ins (~47), renewal reminder = renewals due in 3 days (~57), winback = customers crossing day 45 (~32), abandoned cart = estimated abandoners with email (~61). Campaigns claim orders from openers who bought via any channel, the way Klaviyo's 5-day attribution does. Klaviyo claims ~34% of revenue. |
| 13 | Daily per-ad frequency reached 4.9 (a window metric, not a daily one). | Daily rows carry daily frequency (prospecting 1.1 to 1.9, retargeting 1.5 to 2.0). A new `meta_ads_insights_weekly` table (time_increment=7) carries the 7-day frequency; Golden Hour goes 2.0 → 4.9 and crosses 4.0 the week of Aug 17. |
| 14 | Eight ads, all live every day for 206 days; a linear budget ramp. | Seventeen ads with launch and pause dates: six launches and four pauses inside the window. Delivery share jitters daily (lognormal 0.3). Budget is revised on Mondays in steps, with promo boosts. |
| 15 | Funnel columns were fixed multiples of link clicks. | Each ratio drawn per row. |
| 16 | Before the pixel bug Meta claimed only real last-click orders. | Meta also claims 15% of organic/brand/email new customers and some repeats via view-through, so April's 0.44 purchases-per-order ratio already includes ordinary over-attribution. |
| 17 | Repeat hazard never decayed with recency. | Hazard 0.49%/day at day 14 decaying with an 80-day half-life to a 0.024% floor; promo and send-day lifts; subscribers at 35%. April cohort non-subscriber 6-month repeat: ~26%. |
| 18 | Renewals timed like web checkouts. | Recharge batch at ~05:00 store time, so 08:00 to 11:00 UTC. Web checkouts are bimodal (early afternoon and evening local). |
| 19 | Flat 767 customers/month for 18 months, then a step. | Acquisition ramps with the budget from launch; monthly orders grow 284 → 4,028. |
| 20 | Half of time-consecutive orders had a lower order number; `updated_at` always +2h; no timezone. | Numbers strictly increase with time (ties only at the same second). `updated_at` is the fulfillment or refund time. All timestamps UTC. |
| 21 | Lifetime value below any sellable price for 4 customers. | `total_spent` is net of refunds, so a refunded single order is $0, which is what Shopify shows. |
| 22 | 5-digit fbclid; Honey (a browser extension) sending referral traffic. | 61-character fbclid. Coupon referrers are RetailMeNot, CouponFollow, Dealspotr and Slickdeals. Customer `state` is 66% disabled, 31% enabled, 3% invited, as in a real Shopify store. |
| 23 | GA4 `new_users/sessions` exactly 0.71 or 0.33; same engagement for every medium. | Per-medium baselines with per-row noise. |
| 24 | Google conversions exactly 0.94x orders; cost a linear function of time. | Brand search impressions follow trailing-30-day Meta spend, season and promos; CTR, CPC and conversion ratio are drawn per day. |
| 25 | Orders flat across weekdays despite a Sunday-heavy intent. | Web orders and new customers are weekday-weighted; renewals are schedule-driven, which is correct, so the blended weekday curve is mild. |

## C. Brief vs data (brief updated to match v3)

| # | v2 mismatch | Now |
|---|---|---|
| 26 | Founder quoted a $36 → $60 CAC that appeared nowhere in their spreadsheet. | The sheet has `shopify_new_customers` and `meta_cac_new_their_calc` (Meta spend / all new customers), which moves $26 → $30 because organic and coupon-leak buyers dilute it. The founder quotes that. The true Meta-only figure, $37 → $60 by September, is what the FDE finds. |
| 27 | "Redemptions tripled, AOV dropped" vs 14x and flat AOV. | Brief says 25/month → 200 to 300, $12 lower AOV on those orders, blended AOV drifting down. Data: 19 to 31 → 213, 312, 280; $80 vs $93; blended AOV 73.9 → 71.1. |
| 28 | "Frequency crossed 4.0 in August" vs Sept 4. | Weekly frequency crosses 4.0 the week of Aug 17. Brief says second half of August and names the weekly pull. |
| 29 | Rename to `[P] Prospecting \| Broad` but UTMs became `p_prospecting_broad`; sheet was said to split spend but had no campaign rows. | UTMs are the real campaign names via a `{{campaign.name}}` template, URL-encoded in Shopify landing sites, decoded in GA4. The spreadsheet clause is gone. |
| 30 | $3.2M run rate vs $3.49M. | Brief says $3.4M; data annualizes Jul to Sep at $3.38M. |
| 31 | Influencer spend at 13% of mix had no data. | The sheet has an `influencer_spend` column the founder fills in most weeks. |

## What still identifies it as synthetic

- Emails are `customer{id}@example.com`. Deliberate: no real-looking PII.
- One variant per product, no price changes in two years, no wholesale or POS orders.
- Meta has no placement, age or country breakdowns, and no ad-set budget history.
- GA4 has no landing-page or device dimension.
- Order ids are sequential with random gaps rather than Shopify's global 13-digit ids.

## Measured calibration (v3, window months)

| | Apr | May | Jun | Jul | Aug | Sep | Oct (to 23rd) |
|---|---|---|---|---|---|---|---|
| Shopify orders | 2,638 | 3,072 | 3,280 | 3,705 | 3,931 | 4,028 | 3,142 |
| AOV incl. tax and shipping | 74.5 | 73.2 | 73.3 | 73.9 | 72.7 | 71.1 | 72.2 |
| Renewal share | 44% | 43% | 43% | 43% | 44% | 45% | 45% |
| Meta spend | 28.9k | 33.4k | 34.6k | 43.2k | 42.9k | 42.8k | 37.2k |
| True Meta new-customer CAC | 38.9 | 35.8 | 39.9 | 44.4 | 50.1 | 59.7 | 74.5 |
| Ads Manager ROAS | 3.02 | 2.98 | 4.14 | 4.26 | 4.02 | 3.57 | 3.16 |
| New-customer ROAS (first-order revenue) | 2.12 | 2.14 | 2.09 | 1.81 | 1.61 | 1.31 | 1.06 |
| Meta purchases / Shopify orders | 0.43 | 0.45 | 0.58 | 0.67 | 0.60 | 0.54 | 0.53 |
| FERN20 redemptions | 19 | 22 | 28 | 27 | 213 | 312 | 280 |
