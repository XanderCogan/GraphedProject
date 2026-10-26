import { randomUUID } from "node:crypto";

import { getDb } from "../db/index";
import { ACTION_LABELS, type AccountSummary, type Finding } from "./rules";

export async function createRun(input: {
  clientKey: string;
  dryRun: boolean;
  scope: unknown;
}): Promise<string> {
  const id = `run_${randomUUID()}`;
  await getDb()
    .insertInto("meta_ads_runs")
    .values({
      id,
      client_key: input.clientKey,
      status: "running",
      dry_run: input.dryRun,
      scope: JSON.stringify(input.scope),
      llm_used: false,
    })
    .execute();
  return id;
}

export async function finishRun(input: {
  id: string;
  status: "succeeded" | "failed";
  summary: AccountSummary | null;
  brief: string | null;
  model: string | null;
  llmUsed: boolean;
  error: string | null;
}): Promise<void> {
  await getDb()
    .updateTable("meta_ads_runs")
    .set({
      status: input.status,
      finished_at: new Date(),
      summary: input.summary ? JSON.stringify(input.summary) : null,
      brief: input.brief,
      model: input.model,
      llm_used: input.llmUsed,
      error: input.error,
    })
    .where("id", "=", input.id)
    .execute();
}

export async function insertRecommendations(
  runId: string,
  clientKey: string,
  findings: Finding[],
): Promise<void> {
  if (findings.length === 0) return;
  await getDb()
    .insertInto("meta_ads_recommendations")
    .values(
      findings.map((f, i) => ({
        run_id: runId,
        client_key: clientKey,
        rank: i + 1,
        kind: f.kind,
        severity: f.severity,
        action: f.action,
        action_label: ACTION_LABELS[f.action],
        ad_id: f.adId,
        ad_name: f.adName,
        adset_name: f.adsetName,
        campaign_name: f.campaignName,
        week: f.week,
        rationale: f.rationale,
        evidence: JSON.stringify(f.evidence),
      })),
    )
    .execute();
}

export async function listRuns(clientKey: string, limit = 30) {
  return getDb()
    .selectFrom("meta_ads_runs")
    .select(["id", "started_at", "finished_at", "status", "dry_run", "model", "llm_used", "error", "summary"])
    .where("client_key", "=", clientKey)
    .orderBy("started_at", "desc")
    .limit(limit)
    .execute();
}

export async function latestRun(clientKey: string) {
  const run = await getDb()
    .selectFrom("meta_ads_runs")
    .selectAll()
    .where("client_key", "=", clientKey)
    .where("status", "=", "succeeded")
    .orderBy("started_at", "desc")
    .limit(1)
    .executeTakeFirst();
  if (!run) return null;
  const recommendations = await getDb()
    .selectFrom("meta_ads_recommendations")
    .selectAll()
    .where("run_id", "=", run.id)
    .orderBy("rank")
    .execute();
  return { run, recommendations };
}
