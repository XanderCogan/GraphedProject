import type { ColumnType, Generated } from "kysely";

// Row types for the Meta ads agent tables (migration 0002_meta_ads.ts).
// jsonb columns are written as JSON strings and read back as parsed values.

export interface MetaAdsRunsTable {
  id: string;
  client_key: string;
  started_at: Generated<Date>;
  finished_at: Date | null;
  status: string;
  dry_run: boolean;
  scope: ColumnType<unknown, string, string>;
  summary: ColumnType<unknown, string | null, string | null>;
  brief: string | null;
  model: string | null;
  llm_used: boolean;
  error: string | null;
}

export interface MetaAdsRecommendationsTable {
  id: Generated<string>;
  run_id: string;
  client_key: string;
  rank: number;
  kind: string;
  severity: string;
  action: string;
  action_label: string;
  ad_id: string;
  ad_name: string;
  adset_name: string;
  campaign_name: string;
  week: string;
  rationale: string;
  evidence: ColumnType<unknown, string, string>;
  applied: Generated<boolean>;
  created_at: Generated<Date>;
}
