// Public surface of @app/core. Jobs and dashboard import from here (or from
// subpaths like @app/core/db/types for types only).
export { coreEnv, envSlice, loadLocalEnv, projectRoot } from "./config";
export { destroyDb, getDb } from "./db/index";
export type { Database, ExampleHeartbeatsTable } from "./db/types";
export {
  loadAdsetCpa,
  loadDailyRatio,
  loadFatigue,
  loadUtmCampaigns,
  loadWeeklyCac,
  loadWeeklyCode,
  loadWeeklyOrderMix,
  warehouseConfigured,
  CODE_LEAK_DATE,
  PIXEL_STEP_DATE,
  UTM_RENAME_DATE,
  WINDOW_START,
} from "./warehouse";
export type {
  AdsetCpaRow,
  DailyRatioRow,
  FatigueRow,
  UtmCampaignRow,
  WeeklyCacRow,
  WeeklyCodeRow,
  WeeklyOrderMixRow,
} from "./warehouse";
export { loadMetaAdsConfig, inScope } from "./meta-ads/config";
export type { MetaAdsClientConfig } from "./meta-ads/config";
export { ACTION_LABELS } from "./meta-ads/rules";
export type { AccountSummary, Finding } from "./meta-ads/rules";
export { latestRun as latestMetaAdsRun, listRuns as listMetaAdsRuns } from "./meta-ads/store";
export { runMetaAdsAgent } from "./meta-ads/run";
