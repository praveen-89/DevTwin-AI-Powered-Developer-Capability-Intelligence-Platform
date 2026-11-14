"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { BarChart3 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/card";
import { useReducedMotion } from "motion/react";

export interface BreakdownDatum {
  label: string;
  value: number;
  color?: string;
}

const DEFAULT_COLOR = "#06b6d4";

interface BreakdownChartProps {
  title: string;
  icon?: React.ReactNode;
  data: BreakdownDatum[];
  emptyMessage?: string;
  valueLabel?: string;
  className?: string;
}

/** Horizontal bar chart summarizing counts by category — reused across dashboard pages. */
export function BreakdownChart({
  title,
  icon,
  data,
  emptyMessage = "No data yet. Run an analysis to see this breakdown.",
  valueLabel = "Count",
  className,
}: BreakdownChartProps) {
  const reduceMotion = useReducedMotion();
  const hasData = data.some((d) => d.value > 0);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle as="h3" className="flex items-center gap-2">
          {icon ?? <BarChart3 className="h-4 w-4 text-slate-400" aria-hidden="true" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardBody>
        {!hasData ? (
          <div className="h-40 flex items-center justify-center text-center">
            <p className="text-xs text-slate-500 max-w-xs">{emptyMessage}</p>
          </div>
        ) : (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={11} fontFamily="monospace" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="label"
                  stroke="#64748b"
                  fontSize={11}
                  fontFamily="monospace"
                  width={110}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const d = payload[0].payload as BreakdownDatum;
                    return (
                      <div className="rounded-lg bg-[#0b1120] border border-slate-700/80 p-2.5 shadow-xl text-xs backdrop-blur-md">
                        <span className="text-slate-300 font-semibold">{d.label}</span>
                        <span className="text-slate-500">: </span>
                        <span className="font-mono text-cyan-400">{d.value}</span>
                        <span className="text-slate-500"> {valueLabel.toLowerCase()}</span>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={!reduceMotion} animationDuration={600}>
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.color ?? DEFAULT_COLOR} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

/** Pie chart summarizing proportional composition (e.g. language bytes) — used by SkillGraph. */
export function CompositionPieChart({
  title,
  icon,
  data,
  emptyMessage = "No composition data available.",
  className,
}: BreakdownChartProps) {
  const reduceMotion = useReducedMotion();
  const hasData = data.some((d) => d.value > 0);
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle as="h3" className="flex items-center gap-2">
          {icon ?? <BarChart3 className="h-4 w-4 text-slate-400" aria-hidden="true" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardBody>
        {!hasData ? (
          <div className="h-40 flex items-center justify-center text-center">
            <p className="text-xs text-slate-500 max-w-xs">{emptyMessage}</p>
          </div>
        ) : (
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  isAnimationActive={!reduceMotion}
                  animationDuration={600}
                >
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.color ?? DEFAULT_COLOR} stroke="#090d16" strokeWidth={1} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const d = payload[0].payload as BreakdownDatum;
                    const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : "0.0";
                    return (
                      <div className="rounded-lg bg-[#0b1120] border border-slate-700/80 p-2.5 shadow-xl text-xs backdrop-blur-md">
                        <span className="text-slate-300 font-semibold">{d.label}</span>
                        <span className="text-slate-500">: </span>
                        <span className="font-mono text-cyan-400">{pct}%</span>
                      </div>
                    );
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11, fontFamily: "monospace", color: "#94a3b8" }}
                  iconSize={8}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
