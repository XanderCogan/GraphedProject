import type { Generated } from "kysely";

import type { MetaAdsRecommendationsTable, MetaAdsRunsTable } from "../meta-ads/tables";

export interface ExampleHeartbeatsTable {
  id: Generated<number>;
  message: string;
  created_at: Generated<Date>;
}

// The single source of truth for table types — dashboard pages and jobs both
// query through this. Add a row type per migration (plugins do this too).
// (Applied migrations are tracked in kysely's own kysely_migration table,
// which is intentionally not part of this schema.)
export interface Database {
  example_heartbeats: ExampleHeartbeatsTable;
  meta_ads_runs: MetaAdsRunsTable;
  meta_ads_recommendations: MetaAdsRecommendationsTable;
}
