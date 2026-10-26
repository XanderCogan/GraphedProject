import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

import { projectRoot } from "../config";

// Per-client configuration for the Meta ads agent. One file per client under
// clients/meta-ads/. Everything the agent is allowed to look at or say is
// decided here, not in the prompt.
const configSchema = z.object({
  client_key: z.string().min(1),
  display_name: z.string().min(1),
  product_one_liner: z.string().default(""),
  scope: z.object({
    // The agent only evaluates campaigns whose name starts with one of these.
    include_campaign_prefixes: z.array(z.string().min(1)).min(1),
    // Named explicitly so the brief can say what it is ignoring and why.
    exclude_campaign_prefixes: z.array(z.string().min(1)).default([]),
  }),
  thresholds: z.object({
    frequency_max: z.number().positive(),
    ctr_floor_vs_launch: z.number().gt(0).lt(1),
    baseline_weeks: z.number().int().min(1).max(8),
    cpa_drift_multiple: z.number().gt(1),
    min_weekly_spend: z.number().nonnegative(),
    lookback_weeks: z.number().int().min(2).max(26),
  }),
  agent: z.object({
    model: z.string().min(1),
    max_recommendations: z.number().int().min(1).max(50),
  }),
  notes: z
    .object({
      // Appended to every CPA finding. Client-specific context the rules
      // should not hard-code, e.g. a known over-count in Meta's purchases.
      cpa_caveat: z.string().default(""),
    })
    .default({}),
  writes: z.object({
    // Always false for now: there is no Meta Marketing API credential on this
    // project, so every recommendation is for the media buyer to apply.
    enabled: z.boolean(),
  }),
});

export type MetaAdsClientConfig = z.infer<typeof configSchema>;

export function metaAdsConfigPath(): string {
  return join(projectRoot(), "clients", "meta-ads", "client.config.json");
}

export function loadMetaAdsConfig(): MetaAdsClientConfig {
  const raw = readFileSync(metaAdsConfigPath(), "utf8");
  return configSchema.parse(JSON.parse(raw));
}

/** True when a campaign is one the agent may evaluate. */
export function inScope(campaignName: string, config: MetaAdsClientConfig): boolean {
  const name = campaignName.trim();
  if (config.scope.exclude_campaign_prefixes.some((p) => name.startsWith(p))) return false;
  return config.scope.include_campaign_prefixes.some((p) => name.startsWith(p));
}
