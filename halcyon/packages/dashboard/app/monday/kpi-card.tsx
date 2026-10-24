import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { Sparkline, type Tone } from "./monday-charts";

export function KpiCard({
  label,
  value,
  hint,
  delta,
  deltaVariant = "secondary",
  spark,
  sparkTone = "primary",
  sparkId,
}: {
  label: string;
  value: string;
  hint: string;
  delta?: string;
  deltaVariant?: "success" | "warning" | "destructive" | "secondary" | "info";
  spark?: number[];
  sparkTone?: Tone;
  sparkId: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-end justify-between gap-3">
        <div className="space-y-1">
          <div className="text-3xl font-semibold tabular-nums">{value}</div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {delta ? <Badge variant={deltaVariant}>{delta}</Badge> : null}
            <span>{hint}</span>
          </div>
        </div>
        {spark ? <Sparkline data={spark} tone={sparkTone} id={sparkId} /> : null}
      </CardContent>
    </Card>
  );
}
