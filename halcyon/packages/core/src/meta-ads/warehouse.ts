import { warehouseQuery } from "../warehouse";
import { inScope, type MetaAdsClientConfig } from "./config";

// Everything the agent knows comes from these reads. Dates are anchored on the
// latest day the connector has synced, not on the wall clock, so a lagging
// sync reads as "data through Tuesday", never as a spend collapse. Only full
// seven-day buckets are evaluated: a bucket whose seventh day is after the
// sync date is in progress, whatever its week_end column says.

export function num(value: unknown): number {
  if (value === null || value === undefined || value === "") return 0;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export interface WeeklyAdRow {
  adId: string;
  adName: string;
  adsetName: string;
  campaignName: string;
  weekStart: string;
  weekEnd: string;
  spend: number;
  impressions: number;
  reach: number;
  clicks: number;
  frequency: number;
  purchases: number;
  purchaseValue: number;
}

export interface AdBaseline {
  adId: string;
  launchWeek: string;
  baselineCtr: number;
  weeks: number;
}

export interface CampaignSpend {
  campaignName: string;
  spend: number;
  purchases: number;
  inScope: boolean;
}

export interface Snapshot {
  asOf: string;
  weekly: WeeklyAdRow[];
  baselines: Map<string, AdBaseline>;
  campaigns: CampaignSpend[];
}

export async function loadSnapshot(config: MetaAdsClientConfig): Promise<Snapshot> {
  const [{ as_of }] = await warehouseQuery<{ as_of: string }>(
    `SELECT toString(max(toDate(date_start))) AS as_of FROM {s}.meta_ads_insights`,
  );
  const asOf = String(as_of);
  const lookbackDays = config.thresholds.lookback_weeks * 7;

  const weeklyRaw = await warehouseQuery<Record<string, unknown>>(
    `SELECT toString(ad_id) AS ad_id, ad_name, adset_name, campaign_name,
            toString(toDate(week_start)) AS week_start, toString(toDate(week_end)) AS week_end,
            spend, impressions, reach, clicks, frequency, purchases, purchase_value
     FROM {s}.meta_ads_insights_weekly
     WHERE toDate(week_start) + 6 <= toDate(%(asof)s)
       AND toDate(week_start) >= toDate(%(asof)s) - ${lookbackDays}
     ORDER BY week_start, spend DESC`,
    { asof: asOf },
  );
  const weekly: WeeklyAdRow[] = weeklyRaw
    .map((r) => ({
      adId: String(r.ad_id),
      adName: String(r.ad_name ?? ""),
      adsetName: String(r.adset_name ?? ""),
      campaignName: String(r.campaign_name ?? ""),
      weekStart: String(r.week_start),
      weekEnd: String(r.week_end),
      spend: num(r.spend),
      impressions: num(r.impressions),
      reach: num(r.reach),
      clicks: num(r.clicks),
      frequency: num(r.frequency),
      purchases: num(r.purchases),
      purchaseValue: num(r.purchase_value),
    }))
    .filter((r) => inScope(r.campaignName, config));

  const baselineRaw = await warehouseQuery<Record<string, unknown>>(
    `SELECT toString(ad_id) AS ad_id, toString(min(toDate(week_start))) AS launch_week,
            sum(clicks) / sum(impressions) AS baseline_ctr, count() AS weeks
     FROM (
       SELECT ad_id, week_start, clicks, impressions,
              row_number() OVER (PARTITION BY ad_id ORDER BY week_start) AS rn
       FROM {s}.meta_ads_insights_weekly WHERE impressions > 0
     )
     WHERE rn <= ${config.thresholds.baseline_weeks}
     GROUP BY ad_id`,
  );
  const baselines = new Map<string, AdBaseline>();
  for (const r of baselineRaw) {
    baselines.set(String(r.ad_id), {
      adId: String(r.ad_id),
      launchWeek: String(r.launch_week),
      baselineCtr: num(r.baseline_ctr),
      weeks: num(r.weeks),
    });
  }

  const campaignRaw = await warehouseQuery<Record<string, unknown>>(
    `SELECT campaign_name, sum(spend) AS spend, sum(purchases) AS purchases
     FROM {s}.meta_ads_insights
     WHERE toDate(date_start) > toDate(%(asof)s) - 28 AND toDate(date_start) <= toDate(%(asof)s)
     GROUP BY campaign_name ORDER BY spend DESC`,
    { asof: asOf },
  );
  const campaigns: CampaignSpend[] = campaignRaw.map((r) => ({
    campaignName: String(r.campaign_name ?? ""),
    spend: num(r.spend),
    purchases: num(r.purchases),
    inScope: inScope(String(r.campaign_name ?? ""), config),
  }));

  return { asOf, weekly, baselines, campaigns };
}
