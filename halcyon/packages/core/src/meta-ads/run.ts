import { warehouseConfigured } from "../warehouse";
import { writeBrief } from "./brief";
import { loadMetaAdsConfig } from "./config";
import { ACTION_LABELS, evaluate, type Finding } from "./rules";
import { createRun, finishRun, insertRecommendations } from "./store";
import { loadSnapshot } from "./warehouse";

export interface MetaAdsRunResult {
  runId: string;
  status: "succeeded" | "failed";
  report: string;
  llmUsed: boolean;
}

// One agent session: read the warehouse, apply the rules, have the LLM write
// the note and order the actions, persist everything. Writes to Meta are
// never attempted; `dry_run` is recorded so a future credential cannot
// silently change that.
export async function runMetaAdsAgent(): Promise<MetaAdsRunResult> {
  const config = loadMetaAdsConfig();
  const dryRun = !config.writes.enabled;
  const runId = await createRun({ clientKey: config.client_key, dryRun, scope: config.scope });

  try {
    if (!warehouseConfigured()) {
      throw new Error(
        "Graphed warehouse credentials are not injected (GRAPHED_TOKEN). Run in the cloud or through `graphed dev run`.",
      );
    }
    const snapshot = await loadSnapshot(config);
    const { summary, findings } = evaluate(config, snapshot);
    const brief = await writeBrief(config, summary, findings);
    const byId = new Map(findings.map((f) => [f.id, f]));
    const ordered = brief.order
      .map((id) => byId.get(id))
      .filter((f): f is Finding => f !== undefined);
    await insertRecommendations(runId, config.client_key, ordered);
    await finishRun({
      id: runId,
      status: "succeeded",
      summary,
      brief: brief.text,
      model: brief.model,
      llmUsed: brief.llmUsed,
      error: brief.error,
    });
    const report = [
      brief.text,
      "",
      ...ordered.map((f, i) => `${i + 1}. [${f.severity}] ${ACTION_LABELS[f.action]}: ${f.adName}`),
      "",
      `run ${runId}: ${ordered.length} recommendation(s), llm=${brief.llmUsed ? brief.model : "fallback"}` +
        (brief.error ? ` (${brief.error})` : ""),
    ].join("\n");
    return { runId, status: "succeeded", report, llmUsed: brief.llmUsed };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await finishRun({
      id: runId,
      status: "failed",
      summary: null,
      brief: null,
      model: null,
      llmUsed: false,
      error: message,
    });
    return { runId, status: "failed", report: `run ${runId} failed: ${message}`, llmUsed: false };
  }
}
