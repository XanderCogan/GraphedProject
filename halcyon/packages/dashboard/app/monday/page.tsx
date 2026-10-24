import {
  CODE_LEAK_DATE,
  PIXEL_STEP_DATE,
  UTM_RENAME_DATE,
  loadAdsetCpa,
  loadDailyRatio,
  loadFatigue,
  loadUtmCampaigns,
  loadWeeklyCac,
  loadWeeklyCode,
  loadWeeklyOrderMix,
  warehouseConfigured,
  type AdsetCpaRow,
  type DailyRatioRow,
  type FatigueRow,
  type UtmCampaignRow,
  type WeeklyCacRow,
  type WeeklyCodeRow,
  type WeeklyOrderMixRow,
} from "@app/core";
import { GraphedApiError, GraphedConfigError, GraphedTimeoutError } from "@graphed-inc/sdk";
import { KeyRound, TriangleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

import { KpiCard } from "./kpi-card";
import { BreakdownChart, TrendChart, money, shortDay } from "./monday-charts";

export const dynamic = "force-dynamic";

interface BoardData {
  cac: WeeklyCacRow[];
  ratio: DailyRatioRow[];
  mix: WeeklyOrderMixRow[];
  fatigue: FatigueRow[];
  fern: WeeklyCodeRow[];
  utm: UtmCampaignRow[];
  adsets: AdsetCpaRow[];
}

type Loaded = { kind: "ok"; data: BoardData } | { kind: "token" } | { kind: "error"; message: string };

async function loadBoard(): Promise<Loaded> {
  if (!warehouseConfigured()) return { kind: "token" };
  try {
    const [cac, ratio, mix, fatigue, fern, utm, adsets] = await Promise.all([
      loadWeeklyCac(),
      loadDailyRatio(),
      loadWeeklyOrderMix(),
      loadFatigue(),
      loadWeeklyCode("FERN20"),
      loadUtmCampaigns(),
      loadAdsetCpa(),
    ]);
    return { kind: "ok", data: { cac, ratio, mix, fatigue, fern, utm, adsets } };
  } catch (error) {
    if (error instanceof GraphedConfigError) return { kind: "token" };
    if (error instanceof GraphedApiError || error instanceof GraphedTimeoutError) {
      return { kind: "error", message: error.message };
    }
    throw error;
  }
}

function sum(values: number[]): number {
  return values.reduce((a, b) => a + b, 0);
}

function mean(values: number[]): number {
  return values.length ? sum(values) / values.length : 0;
}

function pct(from: number, to: number): string {
  if (!from) return "";
  const delta = ((to - from) / from) * 100;
  return `${delta >= 0 ? "+" : ""}${delta.toFixed(0)}%`;
}

export default async function MondayBoardPage() {
  const loaded = await loadBoard();

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Monday board</h1>
        <p className="text-sm text-muted-foreground">
          Shopify, Meta, GA4 and Klaviyo in one place, synced hourly. Open this instead of the spreadsheet. Every
          number names the table it came from.
        </p>
      </div>

      {loaded.kind === "token" ? (
        <Alert>
          <KeyRound className="h-4 w-4" />
          <AlertTitle>Warehouse credentials missing</AlertTitle>
          <AlertDescription>
            Start the dashboard with <code>graphed dev run -- npm run dev</code> so <code>GRAPHED_TOKEN</code> is
            present. In the cloud the runtime injects it.
          </AlertDescription>
        </Alert>
      ) : null}

      {loaded.kind === "error" ? (
        <Alert variant="destructive">
          <TriangleAlert className="h-4 w-4" />
          <AlertTitle>Warehouse query failed</AlertTitle>
          <AlertDescription>{loaded.message}</AlertDescription>
        </Alert>
      ) : null}

      {loaded.kind === "ok" ? <Board data={loaded.data} /> : null}
    </div>
  );
}

function Board({ data }: { data: BoardData }) {
  const { cac, ratio, mix, fatigue, fern, utm, adsets } = data;

  // Scorecards: last 4 full weeks vs the first 4 weeks of the window.
  const first4 = cac.slice(0, 4);
  const last4 = cac.slice(-4);
  const cacOf = (rows: WeeklyCacRow[]) => {
    const spend = sum(rows.map((r) => r.spend));
    const newMeta = sum(rows.map((r) => r.newFromMeta));
    return newMeta ? spend / newMeta : 0;
  };
  const cacNow = cacOf(last4);
  const cacThen = cacOf(first4);
  const sheetNow = mean(last4.map((r) => r.sheetCac ?? 0).filter((v) => v > 0));
  const amRoasNow = sum(last4.map((r) => r.spend)) ? sum(last4.map((r) => r.adsManagerRoas * r.spend)) / sum(last4.map((r) => r.spend)) : 0;
  const newRoasNow = sum(last4.map((r) => r.spend)) ? sum(last4.map((r) => r.newCustomerRoas * r.spend)) / sum(last4.map((r) => r.spend)) : 0;

  const ratioBefore = mean(ratio.filter((r) => r.day < PIXEL_STEP_DATE).map((r) => r.ratio));
  const ratioAfter = mean(ratio.filter((r) => r.day >= PIXEL_STEP_DATE).map((r) => r.ratio));
  const ratioLast28 = mean(ratio.slice(-28).map((r) => r.ratio));

  const fernLast4 = fern.slice(-4);
  const fernFirst = fern.filter((r) => r.week < CODE_LEAK_DATE);
  const fernWeeklyBefore = mean(fernFirst.map((r) => r.orders));
  const fernWeeklyNow = mean(fernLast4.map((r) => r.orders));
  const fernDiscountLast4 = sum(fernLast4.map((r) => r.discountGiven));

  const fatigued = fatigue.filter((r) => r.fatigued);
  const prospectingSpend = sum(fatigue.map((r) => r.spend));

  // 7-day rolling ratio for the step chart.
  const rolling = ratio.map((r, i) => {
    const window = ratio.slice(Math.max(0, i - 6), i + 1);
    return { x: r.day, y: mean(window.map((w) => w.ratio)) };
  });

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="True new-customer CAC (Meta)"
          value={money(cacNow)}
          hint={`${money(cacThen)} in April. Spreadsheet says ${money(sheetNow)}.`}
          delta={pct(cacThen, cacNow)}
          deltaVariant="destructive"
          spark={cac.map((r) => r.trueCac)}
          sparkTone="warn"
          sparkId="spark-cac"
        />
        <KpiCard
          label="Ads Manager ROAS vs new-customer ROAS"
          value={`${amRoasNow.toFixed(1)} / ${newRoasNow.toFixed(2)}`}
          hint="Last 4 weeks. The first number is what the media buyer quotes."
          delta={newRoasNow < 1.2 ? "below breakeven" : undefined}
          deltaVariant="warning"
          spark={cac.map((r) => r.newCustomerRoas)}
          sparkTone="primary"
          sparkId="spark-roas"
        />
        <KpiCard
          label="Meta purchases per Shopify order"
          value={ratioLast28.toFixed(2)}
          hint={`${ratioBefore.toFixed(2)} before ${shortDay(PIXEL_STEP_DATE)}, ${ratioAfter.toFixed(2)} after.`}
          delta={pct(ratioBefore, ratioAfter)}
          deltaVariant="destructive"
          spark={rolling.map((r) => r.y)}
          sparkTone="warn"
          sparkId="spark-ratio"
        />
        <KpiCard
          label="FERN20 redemptions per week"
          value={fernWeeklyNow.toFixed(0)}
          hint={`${fernWeeklyBefore.toFixed(0)} a week before ${shortDay(CODE_LEAK_DATE)}. ${money(fernDiscountLast4)} discounted in 4 weeks.`}
          delta={pct(fernWeeklyBefore, fernWeeklyNow)}
          deltaVariant="destructive"
          spark={fern.map((r) => r.orders)}
          sparkTone="warn"
          sparkId="spark-fern"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1. What a new customer actually costs</CardTitle>
          <CardDescription>
            Meta spend divided by first orders whose landing page carried a Meta click, by week. The spreadsheet divides
            the same spend by every new customer in Shopify, including organic and coupon-code buyers, which is why it
            barely moves. Tables: meta_ads_insights.spend, shopify_orders.landing_site, founder_monday_sheet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart
            gradientId="cac-fill"
            label="New-customer CAC by week"
            format={(v) => money(v)}
            markers={[{ x: CODE_LEAK_DATE, label: "FERN20 leaks" }]}
            series={[
              { label: "True CAC: Meta spend / customers Meta brought in", tone: "warn", data: cac.map((r) => ({ x: r.week, y: r.trueCac })) },
              { label: "Blended: Meta spend / all new customers", tone: "info", data: cac.map((r) => ({ x: r.week, y: r.blendedCac })) },
              { label: "Founder's spreadsheet", tone: "muted", dashed: true, data: cac.map((r) => ({ x: r.week, y: r.sheetCac })) },
            ]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Meta is counting purchases that Shopify never saw</CardTitle>
          <CardDescription>
            Meta-reported purchases divided by Shopify orders, 7-day average. A stable ratio is normal attribution
            overlap. A one-day step is a tracking change: on {shortDay(PIXEL_STEP_DATE)} the Shopify Meta sales channel
            went live while the manual pixel stayed on. Tables: meta_ads_insights.purchases, shopify_orders.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart
            gradientId="ratio-fill"
            label="Meta purchases per Shopify order"
            format={(v) => v.toFixed(2)}
            markers={[{ x: PIXEL_STEP_DATE, label: "Meta sales channel installed" }]}
            series={[{ label: "Meta purchases / Shopify orders (7-day avg)", tone: "primary", data: rolling }]}
          />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>3. Who is actually buying</CardTitle>
            <CardDescription>
              Weekly orders split into first orders, returning buyers and subscription renewals. Renewals are about
              40% of orders and were going to happen anyway. Tables: shopify_orders.source_name, customer first order.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              gradientId="mix-fill"
              label="Orders by type per week"
              series={[
                { label: "Subscription renewals", tone: "muted", data: mix.map((r) => ({ x: r.week, y: r.renewals })) },
                { label: "New customers", tone: "primary", data: mix.map((r) => ({ x: r.week, y: r.newCustomers })) },
                { label: "Returning, one-time", tone: "info", data: mix.map((r) => ({ x: r.week, y: r.returning })) },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retargeting claims those renewals</CardTitle>
            <CardDescription>
              Reported cost per claimed purchase by ad set, last 28 days. The Warm ad set serves past purchasers, so
              renewals land in its 7-day click window. Table: meta_ads_insights by adset_name.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BreakdownChart
              label="Reported CPA by ad set"
              format={(v) => money(v, 2)}
              highlight={(row) => (row.label ?? "").toLowerCase().includes("warm")}
              data={adsets.map((r) => ({
                label: r.adsetName,
                value: r.reportedCpa,
                note: `${money(r.spend)} spend, ${r.claimedPurchases.toLocaleString()} claimed`,
              }))}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>4. Creative fatigue</CardTitle>
          <CardDescription>
            Latest full week per active ad. Frequency is 7-day frequency from the weekly insights pull, because reach
            does not add across days. Flag: frequency above 3.5 and CTR down more than 40% from the ad&apos;s first four
            weeks. Table: meta_ads_insights_weekly.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {fatigue.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active ads in the last three weeks.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ad</TableHead>
                  <TableHead>Ad set</TableHead>
                  <TableHead className="text-right">Spend</TableHead>
                  <TableHead className="text-right">Share</TableHead>
                  <TableHead className="text-right">Frequency</TableHead>
                  <TableHead className="text-right">CTR</TableHead>
                  <TableHead className="text-right">vs launch</TableHead>
                  <TableHead className="text-right">Reported CPA</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fatigue.map((r) => (
                  <TableRow key={`${r.adName}-${r.week}`}>
                    <TableCell className="font-medium">{r.adName}</TableCell>
                    <TableCell className="text-muted-foreground">{r.adsetName}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.spend)}</TableCell>
                    <TableCell className="text-right tabular-nums">{prospectingSpend ? `${((100 * r.spend) / prospectingSpend).toFixed(0)}%` : ""}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.frequency.toFixed(1)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.ctrPct.toFixed(2)}%</TableCell>
                    <TableCell className="text-right tabular-nums">{`${r.ctrVsLaunchPct >= 0 ? "+" : ""}${r.ctrVsLaunchPct.toFixed(0)}%`}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.reportedCpa, 2)}</TableCell>
                    <TableCell>{r.fatigued ? <Badge variant="destructive">Fatigued</Badge> : null}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {fatigued.length > 0 ? (
            <p className="mt-3 text-sm text-muted-foreground">
              {fatigued.map((r) => r.adName).join(", ")} {fatigued.length === 1 ? "is" : "are"} fatigued and still
              scaling. The reported CPA looks fine only because of finding 2.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>5. FERN20 has leaked</CardTitle>
            <CardDescription>
              Weekly redemptions of the influencer code, with the share arriving from coupon sites. These orders show
              as direct in Shopify, which is what made organic look like it was growing. Tables:
              shopify_orders.discount_code, referring_site.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TrendChart
              gradientId="fern-fill"
              label="FERN20 redemptions per week"
              markers={[{ x: CODE_LEAK_DATE, label: "On coupon sites" }]}
              series={[
                { label: "Redemptions", tone: "warn", data: fern.map((r) => ({ x: r.week, y: r.orders })) },
                { label: "From coupon-site referrers", tone: "muted", data: fern.map((r) => ({ x: r.week, y: r.couponSiteReferrals })) },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>6. One campaign, two names</CardTitle>
            <CardDescription>
              Paid-social orders by the utm_campaign on the landing page. On {shortDay(UTM_RENAME_DATE)} campaigns were
              renamed and the UTM template changed, so GA4 and the spreadsheet see each campaign twice. Meta reports
              only the new name. Charts here merge on campaign id. Table: shopify_orders.landing_site.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BreakdownChart
              label="Orders by utm_campaign"
              highlight={(row) => (row.label ?? "").includes("_v1")}
              data={utm.map((r) => ({
                label: r.utmCampaign,
                value: r.orders,
                note: `${shortDay(r.firstSeen)} to ${shortDay(r.lastSeen)}`,
              }))}
            />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
