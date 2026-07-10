"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import { PlantMap } from "@/components/plant-map";
import { OeeGauges } from "@/components/oee-gauges";
import { AlertsPanel } from "@/components/alerts-panel";
import { connectNoc, type NocPayload, type NocStatus } from "@/lib/noc-ws";

const STATUS_LABEL: Record<NocStatus, { text: string; color: string }> = {
  connecting:   { text: "conectando",       color: "bg-slate-400" },
  ok:           { text: "ao vivo",          color: "bg-emerald-500" },
  reconnecting: { text: "reconectando",     color: "bg-yellow-400" },
  polling:      { text: "fallback HTTP",    color: "bg-orange-400" },
  error:        { text: "erro de conexao",  color: "bg-red-500" },
};

export default function NocPage() {
  const [data, setData] = useState<NocPayload | null>(null);
  const [status, setStatus] = useState<NocStatus>("connecting");

  useEffect(() => {
    const cleanup = connectNoc({ onData: setData, onStatus: setStatus });
    return cleanup;
  }, []);

  const st = STATUS_LABEL[status];

  return (
    <Shell title="NOC">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-400">
          Monitoramento em tempo real da planta e da infraestrutura de TI/OT.
        </p>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-1.5">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${st.color}`} />
            <span className="text-sm text-slate-200">{st.text}</span>
          </div>
          <Link
            href="/noc/tv"
            className="rounded-lg bg-slate-700 hover:bg-slate-600 px-3 py-1.5 text-sm text-white"
          >
            Modo TV
          </Link>
        </div>
      </div>

      {data === null ? (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-8 text-center text-slate-400">
          Conectando ao NOC...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <section className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-900/40 p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wide">
              Mapa da planta
            </h2>
            <PlantMap areas={data.plant} />
          </section>

          <aside className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wide">
              Top alertas ({data.alerts_active_total} ativos)
            </h2>
            <AlertsPanel alerts={data.top_alerts} />
          </aside>

          <section className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-900/40 p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wide">
              OEE por linha
            </h2>
            <OeeGauges lines={data.oee} />
          </section>

          <aside className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wide">
              KPIs
            </h2>
            <div className="space-y-3">
              <Kpi label="Ativos on-line" value={data.assets_up} color="text-emerald-400" />
              <Kpi label="Ativos off-line" value={data.assets_down} color="text-red-400" />
              <Kpi label="Producao hoje (un)" value={data.output_units.toLocaleString("pt-BR")} color="text-slate-100" />
            </div>
          </aside>
        </div>
      )}
    </Shell>
  );
}

function Kpi({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-slate-700/60 pb-2 last:border-b-0 last:pb-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`text-2xl font-semibold ${color}`}>{value}</span>
    </div>
  );
}