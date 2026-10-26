import { destroyDb } from "@app/core";
import { runMetaAdsAgent } from "@app/core/meta-ads/run";

// Entrypoint for the meta-ads-daily cron job in graphed.yaml.
// Local: `graphed dev run -- npm run job:meta-ads-daily` (needs compose Postgres).
// Cloud: `graphed jobs run meta-ads-daily`.
async function main(): Promise<void> {
  const result = await runMetaAdsAgent();
  console.log(result.report);
  await destroyDb();
  if (result.status === "failed") process.exit(1);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exit(1);
});
