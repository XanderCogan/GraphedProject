import type { MetaAdsClientConfig } from "./config";
import type { Snapshot, WeeklyAdRow } from "./warehouse";

// The agent's judgement lives here, as plain functions over warehouse rows.
// The LLM never sees raw data and never invents a finding: it only explains
// and orders what these rules produced. That keeps every recommendation
// traceable to a number the media buyer can check in Ads Manager.

export type FindingKind = "scaling_into_fatigue" | "fatigue" | "cpa_drift" | "watch";
export type Severity = "high" | "medium" | "low";
export type Action = "cap_and_rotate" | "rotate_creative" | "review_cpa" | "watch";

export interface Finding {
  id: string;
  kind: FindingKind;
  severity: Severity;
  action: Action;
  adId: string;
  adName: string;
  adsetName: string;
  campaignName: string;
  week: string;
  rationale: string;
  evidence: Record<string, number | string | boolean | null>;
}

export interface AccountSummary {
  asOf: string;
  latestWeek: string | null;
  priorWeek: string | null;
  spend: number;
  priorSpend: number | null;
  purchases: number;
  cpa: number;
  adsEvaluated: number;
  fatiguedAds: number;
  inScopeCampaigns: string[];
  excludedCampaigns: { name: string; spend: number }[];
}

export const ACTION_LABELS: Record<Action, string> = {
  cap_and_rotate: "Stop scaling this ad and rotate in a replacement",
  rotate_creative: "Rotate in new creative for this ad",
  review_cpa: "Review this ad's cost per purchase before the next budget change",
  watch: "Watch this ad next week",
};

const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

function ctrOf(row: WeeklyAdRow): number {
  return row.impressions > 0 ? row.clicks / row.impressions : 0;
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function round(value: number, digits = 2): number {
  const f = 10 ** digits;
  return Math.round(value * f) / f;
}

export function evaluate(
  config: MetaAdsClientConfig,
  snapshot: Snapshot,
): { summary: AccountSummary; findings: Finding[] } {
  const t = config.thresholds;
  const weeks = [...new Set(snapshot.weekly.filter((r) => r.spend > 0).map((r) => r.weekStart))].sort();
  const latestWeek = weeks.at(-1) ?? null;
  const priorWeek = weeks.at(-2) ?? null;

  const byAd = new Map<string, WeeklyAdRow[]>();
  for (const row of snapshot.weekly) {
    const list = byAd.get(row.adId) ?? [];
    list.push(row);
    byAd.set(row.adId, list);
  }

  const findings: Finding[] = [];
  let adsEvaluated = 0;
  let fatiguedAds = 0;

  const isFatigued = (row: WeeklyAdRow): boolean => {
    const base = snapshot.baselines.get(row.adId);
    if (!base || base.baselineCtr <= 0 || row.impressions === 0) return false;
    return row.frequency > t.frequency_max && ctrOf(row) < t.ctr_floor_vs_launch * base.baselineCtr;
  };

  for (const [adId, rows] of byAd) {
    rows.sort((a, b) => a.weekStart.localeCompare(b.weekStart));
    const latest = rows.find((r) => r.weekStart === latestWeek);
    if (!latest || latest.impressions === 0 || latest.spend < t.min_weekly_spend) continue;
    adsEvaluated += 1;

    const prior = rows.find((r) => r.weekStart === priorWeek) ?? null;
    const base = snapshot.baselines.get(adId) ?? null;
    const ctr = ctrOf(latest);
    const ctrVsLaunch = base && base.baselineCtr > 0 ? ctr / base.baselineCtr : null;
    const fatiguedWeeks = rows.filter(isFatigued).map((r) => r.weekStart);
    const fatigued = isFatigued(latest);
    const spendUp = prior !== null && prior.spend > 0 && latest.spend > prior.spend * 1.1;
    const cpa = latest.spend / Math.max(latest.purchases, 1);

    const common = {
      adId,
      adName: latest.adName,
      adsetName: latest.adsetName,
      campaignName: latest.campaignName,
      week: latest.weekStart,
    };
    const evidence = {
      spend: round(latest.spend),
      prior_spend: prior ? round(prior.spend) : null,
      frequency_7d: round(latest.frequency),
      frequency_max: t.frequency_max,
      ctr_pct: round(100 * ctr, 3),
      launch_ctr_pct: base ? round(100 * base.baselineCtr, 3) : null,
      ctr_vs_launch_pct: ctrVsLaunch === null ? null : round(100 * ctrVsLaunch),
      purchases: latest.purchases,
      reported_cpa: round(cpa),
      launch_week: base?.launchWeek ?? null,
      first_fatigued_week: fatiguedWeeks[0] ?? null,
      weeks_fatigued: fatiguedWeeks.length,
    };

    if (fatigued) {
      fatiguedAds += 1;
      const launchPct = evidence.ctr_vs_launch_pct ?? 0;
      if (spendUp) {
        findings.push({
          id: `${adId}:scaling_into_fatigue`,
          kind: "scaling_into_fatigue",
          severity: "high",
          action: "cap_and_rotate",
          ...common,
          rationale:
            `Spend rose ${round(100 * (latest.spend / (prior?.spend || 1) - 1), 0)}% week over week on an ad ` +
            `whose 7-day frequency is ${round(latest.frequency)} (limit ${t.frequency_max}) and whose CTR is ` +
            `${launchPct}% of its launch level. More budget here buys repeat impressions, not new customers.`,
          evidence,
        });
      } else {
        findings.push({
          id: `${adId}:fatigue`,
          kind: "fatigue",
          severity: fatiguedWeeks.length >= 2 ? "high" : "medium",
          action: "rotate_creative",
          ...common,
          rationale:
            `7-day frequency ${round(latest.frequency)} is above ${t.frequency_max} and CTR is ${launchPct}% of launch ` +
            `(floor ${round(100 * t.ctr_floor_vs_launch, 0)}%). Fatigued for ${fatiguedWeeks.length} ` +
            `week${fatiguedWeeks.length === 1 ? "" : "s"}, first on ${fatiguedWeeks[0]}.`,
          evidence,
        });
      }
    } else if (
      latest.frequency > 0.85 * t.frequency_max ||
      (ctrVsLaunch !== null && ctrVsLaunch < 0.75)
    ) {
      findings.push({
        id: `${adId}:watch`,
        kind: "watch",
        severity: "low",
        action: "watch",
        ...common,
        rationale:
          `Not fatigued yet: frequency ${round(latest.frequency)} against a limit of ${t.frequency_max}` +
          (ctrVsLaunch === null ? "." : `, CTR at ${round(100 * ctrVsLaunch, 0)}% of launch.`),
        evidence,
      });
    }

    const priorCpas = rows
      .filter((r) => r.weekStart !== latestWeek && r.purchases > 0 && r.spend >= t.min_weekly_spend)
      .map((r) => r.spend / r.purchases);
    const med = median(priorCpas);
    if (med !== null && priorCpas.length >= 3 && cpa > t.cpa_drift_multiple * med) {
      findings.push({
        id: `${adId}:cpa_drift`,
        kind: "cpa_drift",
        severity: "medium",
        action: "review_cpa",
        ...common,
        rationale:
          `Reported cost per purchase is $${round(cpa, 0)} this week against a median of $${round(med, 0)} ` +
          `over the prior ${priorCpas.length} weeks (${t.cpa_drift_multiple}x limit). Meta's purchase count ` +
          `includes the duplicate pixel since Jun 12, so the true number is worse.`,
        evidence: { ...evidence, prior_median_cpa: round(med) },
      });
    }
  }

  findings.sort((a, b) => {
    const s = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    return s !== 0 ? s : Number(b.evidence.spend ?? 0) - Number(a.evidence.spend ?? 0);
  });

  const latestRows = snapshot.weekly.filter((r) => r.weekStart === latestWeek);
  const priorRows = snapshot.weekly.filter((r) => r.weekStart === priorWeek);
  const spend = latestRows.reduce((a, r) => a + r.spend, 0);
  const purchases = latestRows.reduce((a, r) => a + r.purchases, 0);

  const summary: AccountSummary = {
    asOf: snapshot.asOf,
    latestWeek,
    priorWeek,
    spend: round(spend),
    priorSpend: priorWeek ? round(priorRows.reduce((a, r) => a + r.spend, 0)) : null,
    purchases,
    cpa: round(spend / Math.max(purchases, 1)),
    adsEvaluated,
    fatiguedAds,
    inScopeCampaigns: snapshot.campaigns.filter((c) => c.inScope).map((c) => c.campaignName),
    excludedCampaigns: snapshot.campaigns
      .filter((c) => !c.inScope)
      .map((c) => ({ name: c.campaignName, spend: round(c.spend) })),
  };

  return { summary, findings: findings.slice(0, config.agent.max_recommendations) };
}
