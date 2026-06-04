import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useByDimension, useDistribution, usePayEquity, useSummary } from "@/api/hooks";
import type { Dimension } from "@/api/types";
import { StatCard } from "@/components/StatCard";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { formatCount, formatMoney, formatSignedPercent } from "@/lib/format";

const DIMENSIONS: Dimension[] = ["department", "country", "level"];

/** Landing dashboard answering "how do we pay people?" with cards and charts. */
export function DashboardPage() {
  const [dimension, setDimension] = useState<Dimension>("department");
  const summary = useSummary();
  const byDimension = useByDimension(dimension);
  const distribution = useDistribution();
  const payEquity = usePayEquity(dimension);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">How we pay people</h1>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Group by
          <Select
            value={dimension}
            onChange={(event) => setDimension(event.target.value as Dimension)}
            className="w-40"
            aria-label="Group analytics by dimension"
          >
            {DIMENSIONS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Headcount" value={summary.data ? formatCount(summary.data.headcount) : "—"} />
        <StatCard
          label="Total payroll"
          value={summary.data ? formatMoney(summary.data.total_payroll_usd) : "—"}
          hint="USD-normalized"
        />
        <StatCard
          label="Average salary"
          value={summary.data ? formatMoney(summary.data.average_salary_usd) : "—"}
          hint="USD-normalized"
        />
        <StatCard
          label="Median salary"
          value={summary.data ? formatMoney(summary.data.median_salary_usd) : "—"}
          hint="USD-normalized"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Median pay by {dimension}</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {byDimension.data && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={byDimension.data.groups.map((group) => ({
                    key: group.key,
                    median: group.median_usd.minor_units / 100,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="key" tick={{ fontSize: 12 }} interval={0} angle={-20} height={60} textAnchor="end" />
                  <YAxis tickFormatter={(value) => `$${(Number(value) / 1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => `$${Number(value).toLocaleString()}`} />
                  <Bar dataKey="median" fill="hsl(222.2 47.4% 11.2%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Salary distribution (USD)</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {distribution.data && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={distribution.data.buckets.map((bucket) => ({
                    band: bucket.upper_usd
                      ? `$${bucket.lower_usd / 1000}–${bucket.upper_usd / 1000}k`
                      : `$${bucket.lower_usd / 1000}k+`,
                    count: bucket.count,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="band" tick={{ fontSize: 11 }} interval={0} angle={-20} height={60} textAnchor="end" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Pay equity by {dimension}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {payEquity.data?.groups.map((group) => (
              <div key={group.key} className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <div className="font-medium">{group.key}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatCount(group.count)} people · median {formatMoney(group.median_usd)}
                  </div>
                </div>
                <Badge variant={group.gap_vs_overall_pct >= 0 ? "positive" : "negative"}>
                  {formatSignedPercent(group.gap_vs_overall_pct)}
                </Badge>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Gap is each group's median versus the org-wide median of{" "}
            {payEquity.data ? formatMoney(payEquity.data.overall_median_usd) : "—"}.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
