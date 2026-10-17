"use client";

import { Bar, BarChart as RBarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/** Simple horizontal bar chart for {label, value} rows (feature importance, missing values, aggregates). */
export function BarChart({ data, labelKey, valueKey, height }: {
  data: Record<string, unknown>[];
  labelKey: string;
  valueKey: string;
  height?: number;
}) {
  const h = height ?? Math.max(160, data.length * 30 + 40);
  return (
    <div style={{ width: "100%", height: h }}>
      <ResponsiveContainer>
        <RBarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="#f0f0f0" />
          <XAxis type="number" tick={{ fontSize: 12, fill: "#7a7a7a" }} axisLine={false} tickLine={false} />
          <YAxis
            type="category"
            dataKey={labelKey}
            width={150}
            tick={{ fontSize: 12, fill: "#333333" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            contentStyle={{ borderRadius: 11, border: "1px solid #e0e0e0", fontSize: 13 }}
          />
          <Bar dataKey={valueKey} fill="#0066cc" radius={[0, 6, 6, 0]} maxBarSize={18} />
        </RBarChart>
      </ResponsiveContainer>
    </div>
  );
}
