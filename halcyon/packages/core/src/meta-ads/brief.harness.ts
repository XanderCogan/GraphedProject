// Local harness: run the real warehouse snapshot and rules, then ask the
// proxy for a note with a given model, without touching the database.
//   graphed dev run -- npx tsx packages/core/src/meta-ads/brief.harness.ts [model ...]
import { writeBrief } from "./brief";
import { loadMetaAdsConfig } from "./config";
import { evaluate } from "./rules";
import { loadSnapshot } from "./warehouse";

async function main(): Promise<void> {
  const config = loadMetaAdsConfig();
  const snapshot = await loadSnapshot(config);
  const { summary, findings } = evaluate(config, snapshot);
  console.log(`week ${summary.latestWeek}, data through ${summary.asOf}, ${findings.length} finding(s)`);
  const models = process.argv.slice(2);
  if (models.length === 0) models.push(config.agent.model);
  for (const model of models) {
    const started = Date.now();
    const brief = await writeBrief({ ...config, agent: { ...config.agent, model } }, summary, findings);
    console.log(`\n=== ${model} (${Math.round((Date.now() - started) / 100) / 10}s) llm=${brief.llmUsed}${brief.error ? ` error=${brief.error}` : ""}`);
    console.log(brief.text);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
