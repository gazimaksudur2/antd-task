import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { JobSummary } from "../types";

interface Props {
  summary: JobSummary;
  filename: string;
}

const COLOR_BY_CLASS: Record<string, string> = {
  car: "#42a5f5",
  truck: "#ef5350",
  bus: "#ab47bc",
  motorcycle: "#66bb6a",
};

export function SummaryPanel({ summary, filename }: Props) {
  const chartData = useMemo(
    () =>
      Object.entries(summary.by_type)
        .filter(([, v]) => v >= 0)
        .map(([name, count]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          key: name,
          count,
        })),
    [summary.by_type],
  );

  const realTimeRatio =
    summary.duration_seconds > 0
      ? summary.processing_seconds / summary.duration_seconds
      : 0;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">Analysis complete</p>
          <h2 className="text-2xl font-semibold text-white">{filename}</h2>
        </div>
        <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-emerald-300">
          {summary.total_vehicles} vehicles detected
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Total vehicles" value={summary.total_vehicles.toString()} accent />
        <StatCard
          label="Processing time"
          value={`${summary.processing_seconds.toFixed(1)}s`}
          hint={`${realTimeRatio.toFixed(2)}× real-time`}
        />
        <StatCard
          label="Video duration"
          value={`${summary.duration_seconds.toFixed(1)}s`}
          hint={`${summary.fps.toFixed(1)} fps`}
        />
        <StatCard label="Frames" value={summary.frame_count.toString()} />
      </div>

      <div className="glass-card p-5">
        <h3 className="text-base font-semibold text-white">Breakdown by vehicle type</h3>
        <p className="mt-1 text-sm text-slate-400">
          Unique vehicles per class, counted exactly once on first line crossing.
        </p>
        <div className="mt-5 h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis allowDecimals={false} stroke="#94a3b8" fontSize={12} />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{
                  backgroundColor: "rgba(15,23,42,0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  color: "#e2e8f0",
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.key} fill={COLOR_BY_CLASS[entry.key] ?? "#64748b"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  accent?: boolean;
}

function StatCard({ label, value, hint, accent = false }: StatCardProps) {
  return (
    <div
      className={`glass-card p-5 ${
        accent ? "border-brand-500/40 bg-brand-500/10" : ""
      }`}
    >
      <p className="text-xs uppercase tracking-widest text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-bold text-white">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
