// Warehouse access for the Halcyon board. One Graphed client, read-only
// ClickHouse SQL through @graphed-inc/sdk. Credentials come from the Graphed
// runtime (hosted services, jobs, `graphed dev run`), never from this file.
//
// Every query references tables as {s}.<table>; {s} is replaced with the
// warehouse schema the Graphed Postgres connector assigned (WAREHOUSE_SCHEMA).

import { Graphed } from "@graphed-inc/sdk";
import { z } from "zod";

import { envSlice } from "./config";

const warehouseEnvSchema = z.object({
  WAREHOUSE_SCHEMA: z
    .string()
    .regex(/^[A-Za-z_][A-Za-z0-9_]*$/, "WAREHOUSE_SCHEMA must be a plain identifier")
    .default("halcyon"),
});

function schemaName(): string {
  return envSlice(warehouseEnvSchema).WAREHOUSE_SCHEMA;
}

const client = new Graphed();

export function warehouseConfigured(): boolean {
  return client.isConfigured();
}

// ClickHouse returns 64-bit integers as strings in JSON. Coerce everything numeric.
function n(value: unknown): number {
  if (value === null || value === undefined || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function run<T extends object>(
  sql: string,
  parameters: Record<string, string> = {},
): Promise<T[]> {
  const { results } = await client.warehouse.query<T>(
    sql.replaceAll("{s}", schemaName()),
    parameters,
  );
  return results;
}

// Window: the platform exports start on this date (connector backfill window).
export const WINDOW_START = "2026-04-01";
export const PIXEL_STEP_DATE = "2026-06-12";
export const UTM_RENAME_DATE = "2026-07-15";
export const CODE_LEAK_DATE = "2026-08-10";

// ---------------------------------------------------------------------------
// 1. Weekly new-customer CAC: what Meta actually brought in vs the spreadsheet.
// ---------------------------------------------------------------------------
export interface WeeklyCacRow {
  week: string;
  spend: number;
  newFromMeta: number;
  newAll: number;
  trueCac: number;
  blendedCac: number;
  sheetCac: number | null;
  adsManagerRoas: number;
  newCustomerRoas: number;
  metaPurchases: number;
}

export async function loadWeeklyCac(): Promise<WeeklyCacRow[]> {
  const rows = await run<Record<string, unknown>>(
    `WITH firsts AS (
       SELECT customer_id, min(created_at) AS first_at FROM {s}.shopify_orders GROUP BY customer_id
     ),
     newc AS (
       SELECT toStartOfWeek(o.created_at, 1) AS week,
              countIf(positionCaseInsensitive(ifNull(o.landing_site, ''), 'utm_source=facebook') > 0) AS new_from_meta,
              count() AS new_all,
              sumIf(o.total_price, positionCaseInsensitive(ifNull(o.landing_site, ''), 'utm_source=facebook') > 0) AS new_meta_rev
       FROM {s}.shopify_orders o
       JOIN firsts f ON f.customer_id = o.customer_id AND f.first_at = o.created_at
       WHERE o.created_at >= toDate(%(start)s) AND o.cancelled_at IS NULL
       GROUP BY week
     ),
     spend AS (
       SELECT toStartOfWeek(date_start, 1) AS week, sum(spend) AS spend,
              sum(purchase_value) AS meta_val, sum(purchases) AS meta_purch
       FROM {s}.meta_ads_insights GROUP BY week
     ),
     sheet AS (
       SELECT toStartOfWeek(week_of, 1) AS week, any(meta_cac_new_their_calc) AS sheet_cac
       FROM {s}.founder_monday_sheet GROUP BY week
     )
     SELECT toString(spend.week) AS week, spend.spend AS spend, newc.new_from_meta AS new_from_meta,
            newc.new_all AS new_all, newc.new_meta_rev AS new_meta_rev, spend.meta_val AS meta_val,
            spend.meta_purch AS meta_purch, sheet.sheet_cac AS sheet_cac
     FROM spend
     JOIN newc ON newc.week = spend.week
     LEFT JOIN sheet ON sheet.week = spend.week
     WHERE spend.week < toStartOfWeek(today(), 1)
     ORDER BY spend.week`,
    { start: WINDOW_START },
  );
  return rows.map((r) => {
    const spend = n(r.spend);
    const newFromMeta = n(r.new_from_meta);
    const newAll = n(r.new_all);
    const sheet = r.sheet_cac;
    return {
      week: String(r.week),
      spend,
      newFromMeta,
      newAll,
      trueCac: newFromMeta ? spend / newFromMeta : 0,
      blendedCac: newAll ? spend / newAll : 0,
      sheetCac: sheet === null || sheet === undefined ? null : n(sheet),
      adsManagerRoas: spend ? n(r.meta_val) / spend : 0,
      newCustomerRoas: spend ? n(r.new_meta_rev) / spend : 0,
      metaPurchases: n(r.meta_purch),
    };
  });
}

// ---------------------------------------------------------------------------
// 2. Daily Meta-reported purchases vs Shopify orders. A step = a tracking event.
// ---------------------------------------------------------------------------
export interface DailyRatioRow {
  day: string;
  shopifyOrders: number;
  metaPurchases: number;
  ratio: number;
}

export async function loadDailyRatio(): Promise<DailyRatioRow[]> {
  const rows = await run<Record<string, unknown>>(
    `WITH shop AS (
       SELECT toDate(created_at) AS d, count() AS o FROM {s}.shopify_orders
       WHERE created_at >= toDate(%(start)s) AND cancelled_at IS NULL GROUP BY d
     ),
     meta AS (
       SELECT toDate(date_start) AS d, sum(purchases) AS p FROM {s}.meta_ads_insights GROUP BY d
     )
     SELECT toString(shop.d) AS day, shop.o AS o, meta.p AS p
     FROM shop JOIN meta ON meta.d = shop.d
     WHERE shop.d < today()
     ORDER BY shop.d`,
    { start: WINDOW_START },
  );
  return rows.map((r) => {
    const o = n(r.o);
    const p = n(r.p);
    return { day: String(r.day), shopifyOrders: o, metaPurchases: p, ratio: o ? p / o : 0 };
  });
}

// ---------------------------------------------------------------------------
// 3. Weekly orders by type: new, returning, subscription renewal.
// ---------------------------------------------------------------------------
export interface WeeklyOrderMixRow {
  week: string;
  newCustomers: number;
  returning: number;
  renewals: number;
}

export async function loadWeeklyOrderMix(): Promise<WeeklyOrderMixRow[]> {
  const rows = await run<Record<string, unknown>>(
    `WITH firsts AS (
       SELECT customer_id, min(created_at) AS first_at FROM {s}.shopify_orders GROUP BY customer_id
     )
     SELECT toString(toStartOfWeek(o.created_at, 1)) AS week,
            countIf(o.source_name = 'subscription_contract') AS renewals,
            countIf(o.source_name != 'subscription_contract' AND o.created_at = f.first_at) AS new_customers,
            countIf(o.source_name != 'subscription_contract' AND o.created_at != f.first_at) AS returning
     FROM {s}.shopify_orders o JOIN firsts f ON f.customer_id = o.customer_id
     WHERE o.created_at >= toDate(%(start)s) AND o.cancelled_at IS NULL
       AND toStartOfWeek(o.created_at, 1) < toStartOfWeek(today(), 1)
     GROUP BY week ORDER BY week`,
    { start: WINDOW_START },
  );
  return rows.map((r) => ({
    week: String(r.week),
    newCustomers: n(r.new_customers),
    returning: n(r.returning),
    renewals: n(r.renewals),
  }));
}

// ---------------------------------------------------------------------------
// 4. Creative fatigue: latest full week per ad vs its first four weeks.
//    Reach is not additive across days, so 7-day frequency comes from the
//    weekly insights pull, not from daily rows.
// ---------------------------------------------------------------------------
export interface FatigueRow {
  adName: string;
  adsetName: string;
  week: string;
  spend: number;
  ctrPct: number;
  ctrVsLaunchPct: number;
  frequency: number;
  reportedCpa: number;
  fatigued: boolean;
}

export async function loadFatigue(): Promise<FatigueRow[]> {
  const rows = await run<Record<string, unknown>>(
    `WITH weekly AS (
       SELECT ad_id, ad_name, adset_name, toDate(week_start) AS week, spend, impressions AS imps, clicks,
              frequency AS freq, purchases
       FROM {s}.meta_ads_insights_weekly WHERE impressions > 0
     ),
     base AS (
       SELECT ad_id, avg(clicks / imps) AS base_ctr FROM (
         SELECT ad_id, week, clicks, imps, row_number() OVER (PARTITION BY ad_id ORDER BY week) AS rn FROM weekly
       ) WHERE rn <= 4 GROUP BY ad_id
     ),
     latest AS (
       SELECT ad_id, max(week) AS week FROM weekly WHERE spend > 0 GROUP BY ad_id
     )
     SELECT w.ad_name AS ad_name, w.adset_name AS adset_name, toString(w.week) AS week, w.spend AS spend,
            100 * w.clicks / w.imps AS ctr_pct,
            100 * (w.clicks / w.imps) / b.base_ctr - 100 AS ctr_vs_launch_pct,
            w.freq AS frequency, w.spend / greatest(w.purchases, 1) AS reported_cpa,
            (w.freq > 3.5 AND (w.clicks / w.imps) < 0.6 * b.base_ctr) AS fatigued
     FROM weekly w
     JOIN latest l ON l.ad_id = w.ad_id AND l.week = w.week
     JOIN base b ON b.ad_id = w.ad_id
     WHERE w.week >= today() - 21
     ORDER BY w.spend DESC`,
  );
  return rows.map((r) => ({
    adName: String(r.ad_name),
    adsetName: String(r.adset_name),
    week: String(r.week),
    spend: n(r.spend),
    ctrPct: n(r.ctr_pct),
    ctrVsLaunchPct: n(r.ctr_vs_launch_pct),
    frequency: n(r.frequency),
    reportedCpa: n(r.reported_cpa),
    fatigued: n(r.fatigued) === 1 || r.fatigued === true,
  }));
}

// ---------------------------------------------------------------------------
// 5. Discount code leakage: FERN20 by week, with coupon-site referrals.
// ---------------------------------------------------------------------------
export interface WeeklyCodeRow {
  week: string;
  orders: number;
  aov: number;
  discountGiven: number;
  couponSiteReferrals: number;
}

export async function loadWeeklyCode(code: string): Promise<WeeklyCodeRow[]> {
  const rows = await run<Record<string, unknown>>(
    `SELECT toString(toStartOfWeek(created_at, 1)) AS week, count() AS orders, avg(total_price) AS aov,
            sum(total_discounts) AS discount_given,
            countIf(multiSearchAny(lower(ifNull(referring_site, '')),
                    ['retailmenot', 'couponfollow', 'dealspotr', 'slickdeals', 'honey'])) AS coupon_refs
     FROM {s}.shopify_orders
     WHERE discount_code = %(code)s AND created_at >= toDate(%(start)s) AND cancelled_at IS NULL
       AND toStartOfWeek(created_at, 1) < toStartOfWeek(today(), 1)
     GROUP BY week ORDER BY week`,
    { code, start: WINDOW_START },
  );
  return rows.map((r) => ({
    week: String(r.week),
    orders: n(r.orders),
    aov: n(r.aov),
    discountGiven: n(r.discount_given),
    couponSiteReferrals: n(r.coupon_refs),
  }));
}

// ---------------------------------------------------------------------------
// 6. Campaign name continuity: orders by decoded utm_campaign, first and last month seen.
// ---------------------------------------------------------------------------
export interface UtmCampaignRow {
  utmCampaign: string;
  orders: number;
  firstSeen: string;
  lastSeen: string;
}

export async function loadUtmCampaigns(): Promise<UtmCampaignRow[]> {
  const rows = await run<Record<string, unknown>>(
    `SELECT decodeURLComponent(extractAll(ifNull(landing_site, ''), 'utm_campaign=([^&]+)')[1]) AS utm_campaign,
            count() AS orders, toString(min(toDate(created_at))) AS first_seen, toString(max(toDate(created_at))) AS last_seen
     FROM {s}.shopify_orders
     WHERE landing_site LIKE '%utm_medium=paid_social%' AND created_at >= toDate(%(start)s)
     GROUP BY utm_campaign HAVING orders > 20 ORDER BY first_seen, utm_campaign`,
    { start: WINDOW_START },
  );
  return rows.map((r) => ({
    utmCampaign: String(r.utm_campaign),
    orders: n(r.orders),
    firstSeen: String(r.first_seen),
    lastSeen: String(r.last_seen),
  }));
}

// ---------------------------------------------------------------------------
// 7. Retargeting ad sets: reported CPA over the last 28 days.
// ---------------------------------------------------------------------------
export interface AdsetCpaRow {
  adsetName: string;
  spend: number;
  claimedPurchases: number;
  reportedCpa: number;
}

export async function loadAdsetCpa(): Promise<AdsetCpaRow[]> {
  const rows = await run<Record<string, unknown>>(
    `SELECT adset_name, sum(spend) AS spend, sum(purchases) AS purchases
     FROM {s}.meta_ads_insights
     WHERE date_start >= today() - 28 AND date_start < today()
     GROUP BY adset_name ORDER BY spend DESC LIMIT 8`,
  );
  return rows.map((r) => {
    const spend = n(r.spend);
    const purchases = n(r.purchases);
    return {
      adsetName: String(r.adset_name),
      spend,
      claimedPurchases: purchases,
      reportedCpa: purchases ? spend / purchases : 0,
    };
  });
}
