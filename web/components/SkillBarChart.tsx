"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * Mastery par compétence — épuré, lisible, pas de 3D (Brief §5/§9).
 * Le graphe quantitatif ne se miroite PAS en RTL (convention data, Brief §6) → wrapper LTR.
 */
export function SkillBarChart({
  data,
}: {
  data: { label: string; rate: number; n: number }[];
}) {
  return (
    <div data-ltr className="h-[340px] w-full">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
          <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} fontSize={11} stroke="#9a9489" />
          <YAxis
            type="category"
            dataKey="label"
            width={170}
            fontSize={11}
            stroke="#736e64"
            tickLine={false}
            axisLine={false}
            interval={0}
            tickFormatter={(v: string) => (v.length > 26 ? v.slice(0, 25) + "…" : v)}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.03)" }}
            formatter={(v: number) => [`${Math.round(v * 100)}%`, "mastery"]}
            contentStyle={{ borderRadius: 12, border: "1px solid #dcd8cf", fontSize: 12 }}
          />
          <Bar dataKey="rate" radius={[0, 6, 6, 0]} barSize={16} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.rate >= 0.7 ? "#2f9e6b" : d.rate >= 0.4 ? "#dc9a2c" : "#1f4d8a"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
