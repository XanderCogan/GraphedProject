import assert from "node:assert/strict";
import { test } from "node:test";

import { deterministicBrief, thinNote } from "./brief";
import type { MetaAdsClientConfig } from "./config";
import { evaluate } from "./rules";
import type { Snapshot, WeeklyAdRow } from "./warehouse";

// Run: npm test (node --test through tsx). No database, no warehouse, no LLM.

const config: MetaAdsClientConfig = {
  client_key: "test",
  display_name: "Test Co",
  product_one_liner: "",
  scope: { include_campaign_prefixes: ["[P] "], exclude_campaign_prefixes: ["[R] "] },
  thresholds: {
    frequency_max: 3.5,
    ctr_floor_vs_launch: 0.6,
    baseline_weeks: 4,
    cpa_drift_multiple: 1.5,
    min_weekly_spend: 250,
    lookback_weeks: 8,
  },
  agent: { model: "test/model", max_recommendations: 8 },
  notes: { cpa_caveat: "" },
  writes: { enabled: false },
};

const weeks = ["2026-09-02", "2026-09-09", "2026-09-16", "2026-09-23", "2026-09-30", "2026-10-07", "2026-10-14"];

function row(adId: string, adName: string, i: number, o: Partial<WeeklyAdRow> = {}): WeeklyAdRow {
  return {
    adId,
    adName,
    adsetName: "Broad",
    campaignName: "[P] Prospecting | Broad",
    weekStart: weeks[i],
    weekEnd: weeks[i],
    spend: 3000,
    impressions: 200000,
    reach: 100000,
    clicks: 2400, // 1.2% CTR, equal to the baseline below
    frequency: 2.0,
    purchases: 60,
    purchaseValue: 4000,
    ...o,
  };
}

function snapshot(weekly: WeeklyAdRow[]): Snapshot {
  const ids = [...new Set(weekly.map((r) => r.adId))];
  return {
    asOf: "2026-10-23",
    weekly,
    baselines: new Map(ids.map((id) => [id, { adId: id, launchWeek: "2026-06-01", baselineCtr: 0.012, weeks: 4 }])),
    campaigns: [
      { campaignName: "[P] Prospecting | Broad", spend: 40000, purchases: 800, inScope: true },
      { campaignName: "[R] Retargeting | Warm", spend: 9000, purchases: 400, inScope: false },
    ],
  };
}

test("a healthy ad produces no finding", () => {
  const { summary, findings } = evaluate(config, snapshot(weeks.map((_, i) => row("B", "Healthy", i))));
  assert.equal(findings.length, 0);
  assert.equal(summary.adsEvaluated, 1);
  assert.equal(summary.fatiguedAds, 0);
  assert.equal(summary.latestWeek, "2026-10-14");
  assert.equal(summary.priorWeek, "2026-10-07");
});

test("fatigue with rising spend is high severity and asks to cap and rotate", () => {
  const rows = weeks.map((_, i) =>
    row("A", "Tired Ad", i, i >= 5 ? { frequency: 4.1, clicks: 900, spend: i === 6 ? 5000 : 3200 } : {}),
  );
  const { summary, findings } = evaluate(config, snapshot(rows));
  const f = findings.find((x) => x.kind === "scaling_into_fatigue");
  assert.ok(f, "expected a scaling_into_fatigue finding");
  assert.equal(f.severity, "high");
  assert.equal(f.action, "cap_and_rotate");
  assert.equal(f.evidence.first_fatigued_week, "2026-10-07");
  assert.equal(f.evidence.weeks_fatigued, 2);
  assert.equal(summary.fatiguedAds, 1);
});

test("fatigue without a spend increase asks to rotate creative, high after two weeks", () => {
  const rows = weeks.map((_, i) => row("A", "Tired Ad", i, i >= 4 ? { frequency: 4.0, clicks: 1000 } : {}));
  const { findings } = evaluate(config, snapshot(rows));
  const f = findings.find((x) => x.kind === "fatigue");
  assert.ok(f);
  assert.equal(f.action, "rotate_creative");
  assert.equal(f.severity, "high");
  assert.equal(f.evidence.weeks_fatigued, 3);
});

test("frequency creeping toward the limit is a low-severity watch", () => {
  const rows = weeks.map((_, i) => row("C", "Creeping", i, i === 6 ? { frequency: 3.1 } : {}));
  const { findings } = evaluate(config, snapshot(rows));
  assert.equal(findings.length, 1);
  assert.equal(findings[0].kind, "watch");
  assert.equal(findings[0].severity, "low");
});

test("cost per purchase above 1.5x the prior median is a cpa_drift finding", () => {
  const rows = weeks.map((_, i) => row("D", "Pricey", i, i === 6 ? { purchases: 20 } : {}));
  const { findings } = evaluate(config, snapshot(rows));
  const f = findings.find((x) => x.kind === "cpa_drift");
  assert.ok(f);
  assert.equal(f.evidence.prior_median_cpa, 50);
  assert.equal(f.evidence.reported_cpa, 150);
});

test("ads under the weekly spend floor are ignored even when they look terrible", () => {
  const rows = weeks.map((_, i) => row("E", "Tiny", i, { spend: 100, frequency: 9, clicks: 10 }));
  const { summary, findings } = evaluate(config, snapshot(rows));
  assert.equal(findings.length, 0);
  assert.equal(summary.adsEvaluated, 0);
});

test("a partial trailing week is never the week evaluated when only full buckets are loaded", () => {
  // loadSnapshot only returns full buckets; evaluate must then pick the last one with spend.
  const rows = weeks.slice(0, 6).map((_, i) => row("B", "Healthy", i));
  const { summary } = evaluate(config, snapshot(rows));
  assert.equal(summary.latestWeek, "2026-10-07");
});

test("excluded campaigns are reported, not evaluated", () => {
  const { summary } = evaluate(config, snapshot(weeks.map((_, i) => row("B", "Healthy", i))));
  assert.deepEqual(
    summary.excludedCampaigns.map((c) => c.name),
    ["[R] Retargeting | Warm"],
  );
});

test("findings are ordered by severity then spend and capped by max_recommendations", () => {
  const rows = [
    ...weeks.map((_, i) => row("A", "Tired Big", i, i >= 5 ? { frequency: 4.1, clicks: 900, spend: i === 6 ? 6000 : 3200 } : {})),
    ...weeks.map((_, i) => row("C", "Creeping", i, i === 6 ? { frequency: 3.1 } : {})),
  ];
  const { findings } = evaluate({ ...config, agent: { ...config.agent, max_recommendations: 1 } }, snapshot(rows));
  assert.equal(findings.length, 1);
  assert.equal(findings[0].kind, "scaling_into_fatigue");
});

test("thinNote rejects a note that drops the week, an ad, or every number", () => {
  const rows = weeks.map((_, i) => row("A", "Tired Ad", i, i >= 5 ? { frequency: 4.1, clicks: 900 } : {}));
  const { summary, findings } = evaluate(config, snapshot(rows));
  assert.equal(thinNote("Rotate creative on Tired Ad, frequency 4.1.", summary, findings), "does not name the week reviewed");
  assert.equal(thinNote("Week of 2026-10-14: rotate creative, frequency 4.1.", summary, findings), "does not mention Tired Ad");
  assert.equal(thinNote("Week of October 14: Tired Ad is fatigued. Rotate creative.", summary, findings), "contains no numbers");
  assert.equal(thinNote("Week of October 14: Tired Ad is at frequency 4.1. Rotate creative.", summary, findings), null);
});

test("the deterministic brief names the week, every ad, and the excluded campaigns", () => {
  const rows = weeks.map((_, i) => row("A", "Tired Ad", i, i >= 5 ? { frequency: 4.1, clicks: 900 } : {}));
  const { summary, findings } = evaluate(config, snapshot(rows));
  const text = deterministicBrief(summary, findings);
  assert.match(text, /week of 2026-10-14/);
  assert.match(text, /Tired Ad/);
  assert.match(text, /Retargeting \| Warm/);
  assert.equal(thinNote(text, summary, findings), null);
});
