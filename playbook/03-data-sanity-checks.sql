-- Data sanity checks: run these before building any dashboard or trusting any number.
-- Dialect: ClickHouse (Graphed warehouse). Replace {s} with the warehouse schema name that
-- `graphed sources list` reports for the customer's Postgres / Shopify / Meta sources.
-- For the Halcyon work sample every table is in one schema.

-- ---------------------------------------------------------------------------
-- 0. Row counts by month, per source. Gaps here invalidate everything below.
-- ---------------------------------------------------------------------------
SELECT 'shopify_orders' AS src, toStartOfMonth(created_at) AS month, count() AS rows FROM {s}.shopify_orders GROUP BY month
UNION ALL SELECT 'meta_ads_insights', toStartOfMonth(date_start), count() FROM {s}.meta_ads_insights GROUP BY 2
UNION ALL SELECT 'ga4', toStartOfMonth(date), count() FROM {s}.ga4_traffic_acquisition GROUP BY 2
UNION ALL SELECT 'klaviyo', toStartOfMonth(date), count() FROM {s}.klaviyo_message_performance GROUP BY 2
ORDER BY src, month;

-- ---------------------------------------------------------------------------
-- 1. Platform-reported purchases vs Shopify orders. A step change = a tracking event.
--    Healthy: ratio stable month to month. Halcyon: ~0.44 through May, ~0.58 in June, ~0.67 in July.
-- ---------------------------------------------------------------------------
WITH shop AS (
  SELECT toStartOfMonth(created_at) AS month, count() AS shop_orders, sum(total_price) AS shop_rev
  FROM {s}.shopify_orders WHERE cancelled_at IS NULL AND test = false GROUP BY month
), meta AS (
  SELECT toStartOfMonth(date_start) AS month, sum(spend) AS spend, sum(purchases) AS meta_purch, sum(purchase_value) AS meta_val
  FROM {s}.meta_ads_insights GROUP BY month
)
SELECT month, shop_orders, meta_purch, round(meta_purch / shop_orders, 2) AS meta_over_shop,
       round(meta_val / spend, 2) AS ads_manager_roas, round(spend, 0) AS spend
FROM shop JOIN meta USING month ORDER BY month;

-- Daily version to pin the exact date the ratio stepped.
WITH shop AS (SELECT toDate(created_at) AS d, count() AS o FROM {s}.shopify_orders GROUP BY d),
     meta AS (SELECT date_start AS d, sum(purchases) AS p FROM {s}.meta_ads_insights GROUP BY d)
SELECT d, o, p, round(p / o, 2) AS ratio,
       round(avg(p / o) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS ratio_7d
FROM shop JOIN meta USING d ORDER BY d;

-- ---------------------------------------------------------------------------
-- 2. New vs returning. The CAC that matters is spend / NEW customers from the channel.
--    Halcyon: Meta new-customer CAC ~36 in April -> 60+ by September while Ads Manager ROAS holds.
-- ---------------------------------------------------------------------------
WITH firsts AS (
  SELECT customer_id, min(created_at) AS first_at FROM {s}.shopify_orders GROUP BY customer_id
), orders AS (
  SELECT o.*, (o.created_at = f.first_at) AS is_first,
         positionCaseInsensitive(o.landing_site, 'utm_source=facebook') > 0 AS from_meta
  FROM {s}.shopify_orders o JOIN firsts f USING customer_id
), m AS (
  SELECT toStartOfMonth(date_start) AS month, sum(spend) AS spend FROM {s}.meta_ads_insights GROUP BY month
)
SELECT toStartOfMonth(created_at) AS month,
       countIf(is_first) AS new_customers,
       countIf(is_first AND from_meta) AS new_from_meta,
       countIf(NOT is_first) AS returning_orders,
       countIf(source_name = 'subscription_contract') AS renewals,
       round(any(m.spend) / countIf(is_first AND from_meta), 1) AS meta_new_cac,
       round(any(m.spend) / countIf(is_first), 1) AS blended_new_cac
FROM orders JOIN m ON toStartOfMonth(orders.created_at) = m.month
GROUP BY month ORDER BY month;

-- ---------------------------------------------------------------------------
-- 3. Retargeting claiming renewals. Compare warm-adset claimed purchases with
--    orders that actually landed with a Meta click and were first orders.
-- ---------------------------------------------------------------------------
SELECT toStartOfMonth(date_start) AS month, adset_name, round(sum(spend)) AS spend, sum(purchases) AS claimed,
       round(sum(spend) / sum(purchases), 2) AS reported_cpa
FROM {s}.meta_ads_insights GROUP BY month, adset_name ORDER BY adset_name, month;

-- ---------------------------------------------------------------------------
-- 4. Campaign name continuity (UTM rename). A campaign that "ends" the week another
--    "starts" with the same spend profile is one campaign. Build a mapping table.
-- ---------------------------------------------------------------------------
SELECT toStartOfMonth(date) AS month, session_campaign, sum(sessions) AS sessions, sum(ecommerce_purchases) AS purchases
FROM {s}.ga4_traffic_acquisition WHERE session_medium = 'paid_social'
GROUP BY month, session_campaign ORDER BY session_campaign, month;

-- The same from Shopify landing_site, which is the source of truth for what the ad actually sent.
-- Landing sites are URL-encoded; after the rename the buyer switched to a {{campaign.name}} template,
-- so the value is the Meta campaign name with brackets and pipes (%5BP%5D%20Prospecting%20%7C%20Broad).
SELECT toStartOfMonth(created_at) AS month,
       decodeURLComponent(extractAll(landing_site, 'utm_campaign=([^&]+)')[1]) AS utm_campaign, count() AS orders
FROM {s}.shopify_orders WHERE landing_site LIKE '%utm_campaign=%'
GROUP BY month, utm_campaign ORDER BY utm_campaign, month;

-- Mapping used for Halcyon (old -> current). Keep this in a project table, not in the chart code.
-- prospecting_broad_v1      -> [P] Prospecting | Broad
-- prospecting_interests_v1  -> [P] Prospecting | Interests
-- retargeting_warm_v1       -> [R] Retargeting | Warm
-- retargeting_cart_v1       -> [R] Retargeting | Cart
-- Meta's own insights tables report the CURRENT name for all history, so join on campaign_id there.

-- ---------------------------------------------------------------------------
-- 5. Discount code leakage. Redemptions, AOV and referrer per code per month.
-- ---------------------------------------------------------------------------
SELECT toStartOfMonth(created_at) AS month, discount_code, count() AS orders,
       round(avg(total_price), 2) AS aov, round(sum(total_discounts), 0) AS discount_given,
       countIf(multiSearchAny(referring_site, ['retailmenot', 'couponfollow', 'dealspotr', 'slickdeals'])) AS coupon_site_referrals,
       countIf(referring_site = '' OR referring_site IS NULL) AS direct
FROM {s}.shopify_orders WHERE discount_code != '' AND discount_code IS NOT NULL
GROUP BY month, discount_code ORDER BY discount_code, month;

-- ---------------------------------------------------------------------------
-- 6. Creative fatigue. Weekly frequency and CTR per ad vs the ad's first four weeks.
--    Reach is not additive across days, so daily rows cannot give you a 7-day frequency
--    (daily frequency on prospecting sits near 1.1 to 1.9 and tells you nothing). Use the
--    weekly insights pull (time_increment=7), which the connector lands as meta_ads_insights_weekly.
-- ---------------------------------------------------------------------------
WITH weekly AS (
  SELECT ad_id, ad_name, week_start AS week, spend, impressions AS imps, clicks, frequency AS freq, purchases
  FROM {s}.meta_ads_insights_weekly
), base AS (
  SELECT ad_id, avg(clicks / imps) AS base_ctr FROM (
    SELECT ad_id, week, clicks, imps, row_number() OVER (PARTITION BY ad_id ORDER BY week) AS rn FROM weekly
  ) WHERE rn <= 4 GROUP BY ad_id
)
SELECT w.ad_name, w.week, round(w.spend) AS spend, round(100 * w.clicks / w.imps, 2) AS ctr_pct,
       round(100 * (w.clicks / w.imps) / b.base_ctr - 100, 0) AS ctr_vs_launch_pct, round(w.freq, 2) AS frequency,
       round(w.spend / w.purchases, 1) AS reported_cpa,
       if(w.freq > 3.5 AND (w.clicks / w.imps) < 0.6 * b.base_ctr, 'FATIGUED', '') AS flag
FROM weekly w JOIN base b USING ad_id ORDER BY w.ad_name, w.week;

-- ---------------------------------------------------------------------------
-- 7. The founder's spreadsheet vs the warehouse. Where exactly do they diverge?
-- ---------------------------------------------------------------------------
WITH truth AS (
  SELECT toStartOfWeek(created_at, 1) AS week_of, count() AS orders, sum(total_price) AS rev FROM {s}.shopify_orders GROUP BY week_of
)
-- Their "new customer CAC" divides Meta spend by ALL new customers, including organic and the
-- coupon-leak buyers, which is why it barely moves while the Meta-only figure doubles.
SELECT f.week_of, f.meta_spend, f.meta_purchases_reported, f.blended_cac_their_calc, f.meta_cac_new_their_calc,
       t.orders AS shopify_orders_true, f.shopify_orders AS shopify_orders_sheet,
       round(f.meta_spend / f.meta_purchases_reported, 2) AS their_cac_recomputed, f.notes
FROM {s}.founder_monday_sheet f LEFT JOIN truth t ON t.week_of = f.week_of ORDER BY f.week_of;
