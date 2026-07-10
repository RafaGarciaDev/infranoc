"use client";

import ReactECharts from "echarts-for-react";
import type { NocPayload } from "@/lib/noc-ws";

type OeeLine = NocPayload["oee"][number];

function gaugeOption(line: OeeLine) {
  // Cores por faixa: vermelho <60, amarelo 60-75, verde >=75
  const value = Math.max(0, Math.min(100, line.value));
  return {
    series: [
      {
        type: "gauge",
        min: 0,
        max: 100,
        splitNumber: 5,
        radius: "88%",
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [0.6,  "#ef4444"],
              [0.75, "#eab308"],
              [1,    "#22c55e"],
            ],
          },
        },
        pointer: { itemStyle: { color: "#f8fafc" }, width: 4, length: "60%" },
        axisTick: { distance: -14, length: 6, lineStyle: { color: "#0f172a", width: 1 } },
        splitLine: { distance: -14, length: 10, lineStyle: { color: "#0f172a", width: 2 } },
        axisLabel: { color: "#94a3b8", distance: 14, fontSize: 10 },
        title: { show: false },
        detail: {
          valueAnimation: true,
          formatter: "{value}%",
          color: "#f8fafc",
          fontSize: 20,
          fontWeight: 600,
          offsetCenter: [0, "70%"],
        },
        data: [{ value }],
      },
    ],
  };
}

type Props = { lines: OeeLine[] };

export function OeeGauges({ lines }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {lines.map((line) => (
        <div
          key={line.line}
          className="relative rounded-lg border border-slate-700 bg-slate-900/40 p-2"
        >
          <div className="text-sm font-medium text-slate-200 text-center mb-1">
            {line.name}
          </div>
          {line.stopped && (
            <span className="absolute right-2 top-2 rounded bg-red-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
              Parada
            </span>
          )}
          <ReactECharts
            option={gaugeOption(line)}
            style={{ height: 180 }}
            opts={{ renderer: "svg" }}
            notMerge
            lazyUpdate
          />
        </div>
      ))}
    </div>
  );
}