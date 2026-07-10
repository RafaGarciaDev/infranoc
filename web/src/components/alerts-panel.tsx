"use client";

import { useState } from "react";
import { ackAlert } from "@/lib/api";
import type { NocPayload } from "@/lib/noc-ws";

type TopAlert = NocPayload["top_alerts"][number];

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high:     "bg-orange-600 text-white",
  warning:  "bg-yellow-500 text-slate-900",
  info:     "bg-blue-600 text-white",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60_000);
  if (min < 1)  return "agora";
  if (min < 60) return `${min}min atras`;
  const hr = Math.floor(min / 60);
  if (hr < 24)  return `${hr}h atras`;
  const days = Math.floor(hr / 24);
  return `${days}d atras`;
}

type Props = { alerts: TopAlert[] };

export function AlertsPanel({ alerts }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [acked, setAcked] = useState<Set<string>>(new Set());

  async function handleAck(id: string) {
    setBusy(id);
    setErrors((e) => ({ ...e, [id]: "" }));
    try {
      await ackAlert(id);
      setAcked((s) => new Set(s).add(id));
    } catch (err) {
      setErrors((e) => ({ ...e, [id]: err instanceof Error ? err.message : "Falha" }));
    } finally {
      setBusy(null);
    }
  }

  if (alerts.length === 0) {
    return (
      <div className="text-sm text-slate-400 italic">
        Nenhum alerta ativo.
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {alerts.map((a) => {
        const badge = SEV_BADGE[a.severity] ?? "bg-slate-600 text-white";
        const isAcked = acked.has(a.id);
        return (
          <li
            key={a.id}
            className={`rounded-lg border border-slate-700 bg-slate-900/50 p-3 ${isAcked ? "opacity-50" : ""}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${badge}`}>
                    {a.severity}
                  </span>
                  {a.categoria && (
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">
                      {a.categoria}
                    </span>
                  )}
                  <span className="text-[10px] text-slate-500 ml-auto">
                    {timeAgo(a.starts_at)}
                  </span>
                </div>
                <div className="text-sm text-slate-100 truncate" title={a.summary ?? ""}>
                  {a.summary ?? "(sem summary)"}
                </div>
                {a.asset && (
                  <div className="text-xs text-slate-400 mt-0.5 font-mono">
                    {a.asset}
                  </div>
                )}
                {a.impacto_negocio && (
                  <div className="text-xs text-slate-300 mt-1 italic border-l-2 border-slate-600 pl-2">
                    {a.impacto_negocio}
                  </div>
                )}
                {errors[a.id] && (
                  <div className="text-xs text-red-400 mt-1">{errors[a.id]}</div>
                )}
              </div>
              <button
                onClick={() => handleAck(a.id)}
                disabled={busy === a.id || isAcked}
                className="shrink-0 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed px-2 py-1 text-xs text-white"
              >
                {isAcked ? "Acked" : busy === a.id ? "..." : "Ack"}
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}