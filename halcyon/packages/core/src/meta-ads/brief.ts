import { Graphed } from "@graphed-inc/sdk";
import OpenAI from "openai";
import { z } from "zod";

import type { MetaAdsClientConfig } from "./config";
import { ACTION_LABELS, type AccountSummary, type Finding } from "./rules";

// The LLM's whole job: turn the rules' findings into a short note the media
// buyer will read, and order the actions. It gets the findings as JSON, is told
// it cannot change anything, and is asked not to introduce numbers that are
// not in the input. If the proxy is unavailable or the reply is malformed the
// run still succeeds with a deterministic brief, and the dashboard says so.

export interface BriefResult {
  text: string;
  order: string[];
  model: string;
  llmUsed: boolean;
  error: string | null;
}

const replySchema = z.object({
  brief: z.string().min(1),
  order: z.array(z.string()).default([]),
});

function money(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

export function deterministicBrief(summary: AccountSummary, findings: Finding[]): string {
  const lines: string[] = [];
  const wow =
    summary.priorSpend && summary.priorSpend > 0
      ? ` (${summary.spend >= summary.priorSpend ? "+" : ""}${Math.round(100 * (summary.spend / summary.priorSpend - 1))}% vs prior week)`
      : "";
  lines.push(
    `Prospecting week of ${summary.latestWeek ?? "n/a"}, data through ${summary.asOf}: ` +
      `${money(summary.spend)} spend${wow}, ${summary.purchases} Meta-reported purchases, ` +
      `reported CPA ${money(summary.cpa)}. ${summary.adsEvaluated} ads evaluated, ${summary.fatiguedAds} fatigued.`,
  );
  if (findings.length === 0) {
    lines.push("No action needed this week. Thresholds held on every ad with meaningful spend.");
  } else {
    lines.push("");
    findings.forEach((f, i) => {
      lines.push(`${i + 1}. ${ACTION_LABELS[f.action]}: ${f.adName} (${f.adsetName}). ${f.rationale}`);
    });
  }
  if (summary.excludedCampaigns.length > 0) {
    lines.push("");
    lines.push(
      `Out of scope by design: ${summary.excludedCampaigns
        .map((c) => `${c.name} (${money(c.spend)} over 28 days)`)
        .join(", ")}. Retargeting purchases are mostly subscription renewals and are reviewed separately.`,
    );
  }
  return lines.join("\n");
}

function extractJson(text: string): unknown {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) throw new Error("no JSON object in reply");
  return JSON.parse(text.slice(start, end + 1));
}

export async function writeBrief(
  config: MetaAdsClientConfig,
  summary: AccountSummary,
  findings: Finding[],
): Promise<BriefResult> {
  const fallback = deterministicBrief(summary, findings);
  const graphed = new Graphed();
  if (!graphed.isConfigured()) {
    return {
      text: fallback,
      order: findings.map((f) => f.id),
      model: config.agent.model,
      llmUsed: false,
      error: "GRAPHED_TOKEN not injected; run through `graphed dev run` or in the cloud",
    };
  }

  const openai = new OpenAI({ baseURL: graphed.openRouter.baseUrl(), apiKey: graphed.token });
  const system = [
    `You are the Meta ads agent for ${config.display_name}. ${config.product_one_liner}`.trim(),
    `You only review prospecting campaigns (names starting with ${config.scope.include_campaign_prefixes
      .map((p) => JSON.stringify(p))
      .join(", ")}).`,
    "You cannot change anything in Ads Manager. Every action is a recommendation the media buyer applies by hand.",
    "You receive findings produced by fixed rules. Do not add findings, do not change their numbers, do not invent numbers.",
    "Write for a freelance media buyer who has five minutes. Plain language, no hype, at most 180 words.",
    'Reply with one JSON object: {"brief": "<the note>", "order": ["<finding id>", ...]} with every finding id, most urgent first.',
  ].join("\n");
  const user = JSON.stringify(
    {
      summary,
      findings: findings.map((f) => ({
        id: f.id,
        kind: f.kind,
        severity: f.severity,
        action: ACTION_LABELS[f.action],
        ad: f.adName,
        adset: f.adsetName,
        campaign: f.campaignName,
        week: f.week,
        rationale: f.rationale,
        evidence: f.evidence,
      })),
    },
    null,
    1,
  );

  try {
    const completion = await openai.chat.completions.create({
      model: config.agent.model,
      temperature: 0.2,
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
    });
    const text = completion.choices[0]?.message?.content ?? "";
    const reply = replySchema.parse(extractJson(text));
    const known = new Set(findings.map((f) => f.id));
    const order = reply.order.filter((id) => known.has(id));
    for (const f of findings) if (!order.includes(f.id)) order.push(f.id);
    return { text: reply.brief.trim(), order, model: config.agent.model, llmUsed: true, error: null };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { text: fallback, order: findings.map((f) => f.id), model: config.agent.model, llmUsed: false, error: message };
  }
}
