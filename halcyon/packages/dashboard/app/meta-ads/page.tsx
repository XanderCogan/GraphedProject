import {
  latestMetaAdsRun,
  listMetaAdsRuns,
  loadMetaAdsConfig,
  type AccountSummary,
} from "@app/core";
import { Bot, ShieldCheck } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { KpiCard } from "../monday/kpi-card";
import { money } from "../monday/monday-charts";

export const dynamic = "force-dynamic";

type Severity = "high" | "medium" | "low";

const severityVariant: Record<Severity, "destructive" | "default" | "secondary"> = {
  high: "destructive",
  medium: "default",
  low: "secondary",
};

function asSeverity(value: string): Severity {
  return value === "high" || value === "medium" ? value : "low";
}

function when(value: Date | null): string {
  if (!value) return "";
  return value.toLocaleString("en-US", { timeZone: "America/Chicago", dateStyle: "medium", timeStyle: "short" });
}

function pctDelta(from: number | null, to: number): string {
  if (!from) return "";
  const delta = ((to - from) / from) * 100;
  return `${delta >= 0 ? "+" : ""}${delta.toFixed(0)}%`;
}

export default async function MetaAdsPage() {
  const config = loadMetaAdsConfig();
  const [latest, runs] = await Promise.all([
    latestMetaAdsRun(config.client_key),
    listMetaAdsRuns(config.client_key, 20),
  ]);
  const summary = (latest?.run.summary ?? null) as AccountSummary | null;
  const t = config.thresholds;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Meta ads agent</h1>
          <p className="text-sm text-muted-foreground">
            Runs every morning at 8:00 Central. Reads prospecting performance from the warehouse, applies the fatigue and
            cost rules below, and writes the media buyer a note. It recommends; it does not touch Ads Manager.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary" className="gap-1">
            <ShieldCheck className="size-3" /> recommend-only
          </Badge>
          <Badge variant="outline" className="gap-1">
            <Bot className="size-3" /> {config.agent.model}
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scope</CardTitle>
            <CardDescription>What the agent is allowed to look at.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Evaluated</div>
              <div className="flex flex-wrap gap-1">
                {(summary?.inScopeCampaigns ?? config.scope.include_campaign_prefixes).map((name) => (
                  <Badge key={name} variant="default">
                    {name}
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">Excluded on purpose</div>
              <div className="flex flex-wrap gap-1">
                {(summary?.excludedCampaigns ?? config.scope.exclude_campaign_prefixes.map((p) => ({ name: p, spend: 0 }))).map(
                  (c) => (
                    <Badge key={c.name} variant="outline">
                      {c.name}
                      {c.spend ? ` · ${money(c.spend)} / 28d` : ""}
                    </Badge>
                  ),
                )}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Retargeting serves past purchasers, so its reported purchases are mostly subscription renewals. Judging it
                by CPA would reward the double-counting the Monday board already flags.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rules</CardTitle>
            <CardDescription>Fixed thresholds from clients/meta-ads/client.config.json. The model cannot change them.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm">
            <ul className="flex flex-col gap-2">
              <li>
                <span className="font-medium">Fatigue:</span> 7-day frequency above {t.frequency_max} and CTR below{" "}
                {Math.round(100 * t.ctr_floor_vs_launch)}% of the ad&apos;s first {t.baseline_weeks} weeks.
              </li>
              <li>
                <span className="font-medium">Scaling into fatigue:</span> fatigued and weekly spend up more than 10%.
              </li>
              <li>
                <span className="font-medium">CPA drift:</span> reported cost per purchase above {t.cpa_drift_multiple}x the
                median of the ad&apos;s prior {t.lookback_weeks} weeks.
              </li>
              <li>
                <span className="font-medium">Ignored:</span> ads under {money(t.min_weekly_spend)} a week. Frequency comes
                from the weekly pull; daily rows cannot see it.
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {!latest || !summary ? (
        <Alert>
          <AlertTitle>No completed runs yet</AlertTitle>
          <AlertDescription>
            The first run happens at the next 8:00 Central schedule. Trigger one now with{" "}
            <code className="rounded bg-muted px-1">graphed jobs run meta-ads-daily</code>.
            {runs[0]?.status === "failed" && runs[0].error ? ` Last attempt failed: ${runs[0].error}` : ""}
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label="Prospecting spend"
              value={money(summary.spend)}
              delta={pctDelta(summary.priorSpend, summary.spend)}
              hint={`Week of ${summary.latestWeek}, data through ${summary.asOf}`}
              sparkId="meta-spend"
            />
            <KpiCard
              label="Meta-reported purchases"
              value={summary.purchases.toLocaleString("en-US")}
              hint="Includes the duplicate pixel since Jun 12"
              sparkId="meta-purchases"
            />
            <KpiCard label="Reported CPA" value={money(summary.cpa)} hint="Spend over Meta-reported purchases" sparkId="meta-cpa" />
            <KpiCard
              label="Fatigued ads"
              value={`${summary.fatiguedAds} / ${summary.adsEvaluated}`}
              hint="Of ads with meaningful spend this week"
              sparkId="meta-fatigued"
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">This morning&apos;s note</CardTitle>
              <CardDescription>
                {when(latest.run.finished_at)} ·{" "}
                {latest.run.llm_used
                  ? `written by ${latest.run.model} from the rule findings`
                  : `rule output only (model unavailable${latest.run.error ? `: ${latest.run.error}` : ""})`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-6">{latest.run.brief}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recommendations</CardTitle>
              <CardDescription>
                In the order the agent wants them done. Each one names the ad and the number behind it.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {latest.recommendations.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nothing to do this week. Every ad held its thresholds.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-8">#</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Ad</TableHead>
                      <TableHead className="text-right">Spend</TableHead>
                      <TableHead className="text-right">Freq</TableHead>
                      <TableHead className="text-right">CTR vs launch</TableHead>
                      <TableHead className="text-right">Rep. CPA</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {latest.recommendations.map((r) => {
                      const e = (r.evidence ?? {}) as Record<string, number | string | null>;
                      return (
                        <TableRow key={r.id}>
                          <TableCell className="align-top text-muted-foreground">{r.rank}</TableCell>
                          <TableCell className="align-top">
                            <div className="flex flex-col gap-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant={severityVariant[asSeverity(r.severity)]}>{r.severity}</Badge>
                                <span className="font-medium">{r.action_label}</span>
                              </div>
                              <p className="max-w-prose text-xs text-muted-foreground">{r.rationale}</p>
                            </div>
                          </TableCell>
                          <TableCell className="align-top">
                            <div className="font-medium">{r.ad_name}</div>
                            <div className="text-xs text-muted-foreground">
                              {r.adset_name} · {r.campaign_name}
                            </div>
                          </TableCell>
                          <TableCell className="align-top text-right tabular-nums">{money(Number(e.spend ?? 0))}</TableCell>
                          <TableCell className="align-top text-right tabular-nums">{Number(e.frequency_7d ?? 0).toFixed(2)}</TableCell>
                          <TableCell className="align-top text-right tabular-nums">
                            {e.ctr_vs_launch_pct === null || e.ctr_vs_launch_pct === undefined ? "" : `${e.ctr_vs_launch_pct}%`}
                          </TableCell>
                          <TableCell className="align-top text-right tabular-nums">{money(Number(e.reported_cpa ?? 0))}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runs</CardTitle>
          <CardDescription>Every session, including failures. Nothing is retried automatically.</CardDescription>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No runs recorded.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Note</TableHead>
                  <TableHead className="text-right">Fatigued</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => {
                  const s = (run.summary ?? null) as AccountSummary | null;
                  return (
                    <TableRow key={run.id}>
                      <TableCell className="tabular-nums">{when(run.started_at)}</TableCell>
                      <TableCell>
                        <Badge variant={run.status === "succeeded" ? "secondary" : "destructive"}>{run.status}</Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {run.status === "failed" ? run.error : run.llm_used ? run.model : "rule output only"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{s ? `${s.fatiguedAds} / ${s.adsEvaluated}` : ""}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
