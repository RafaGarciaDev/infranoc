"use client";

import { useEffect, useState } from "react";
import { PlantMap } from "@/components/plant-map";
import { OeeGauges } from "@/components/oee-gauges";
import { connectNoc, type NocPayload, type NocStatus } from "@/lib/noc-ws";

type View = "planta" | "ti";
const ROTATION_MS = 20_000;

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high:     "bg-orange-600 text-white",
  warning:  "bg-yellow-500 text-slate-900",
  info:     "bg-blue-600 text-white",
};

const STATUS_LABEL: Record<NocStatus, { text: string; color: string }> = {
  connecting:   { text: "conectando",    color: "bg-slate-400" },
  ok:           { text: "ao vivo",       color: "bg-emerald-500" },
  reconnecting: { text: "reconectando",  color: "bg-yellow-400" },
  polling:      { text: "fallback HTTP", color: "bg-orange-400" },
  error:        { text: "erro",          color: "bg-red-500" },
};

export default function NocTvPage() {
  const [data, setData] = useState<NocPayload | null>(null);
  const [status, setStatus] = useState<NocStatus>("connecting");
  const [view, setView] = useState<View>("planta");
  const [clock, setClock] = useState<string>("");
  const [needsFullscreen, setNeedsFullscreen] = useState(false);

  // Conexao com o backend
  useEffect(() => {
    const cleanup = connectNoc({ onData: setData, onStatus: setStatus });
    return cleanup;
  }, []);

  // Rotacao planta <-> TI (nao recria o WS!)
  useEffect(() => {
    const t = setInterval(() => {
      setView((v) => (v === "planta" ? "ti" : "planta"));
    }, ROTATION_MS);
    return () => clearInterval(t);
  }, []);

  // Relogio grande
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  // Fullscreen automatico com fallback pra botao (navegador exige gesto)
  useEffect(() => {
    const el = document.documentElement;
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => setNeedsFullscreen(true));
    } else {
      setNeedsFullscreen(true);
    }
  }, []);

  async function activateFullscreen() {
    try {
      await document.documentElement.requestFullscreen();
      setNeedsFullscreen(false);
    } catch {
      /* usuario recusou - deixa o botao la */
    }
  }

  const st = STATUS_LABEL[status];
  const today = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 text-lg p-6">
      {/* Header fixo */}
      <header className="flex items-center justify-between mb-6 border-b border-slate-700 pb-4">
        <div>
          <div className="text-3xl font-bold text-emerald-400">Vale Verde S/A</div>
          <div className="text-sm text-slate-400 capitalize">{today}</div>
        </div>
        <div className="text-6xl font-mono font-bold tabular-nums">{clock}</div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2">
            <span className={`inline-block h-3 w-3 rounded-full ${st.color}`} />
            <span className="text-base">{st.text}</span>
          </div>
          
          <a
            href="/noc"
            className="rounded-lg bg-slate-700 hover:bg-slate-600 px-4 py-2 text-base text-white"
          >
            Sair TV
          </a>
        </div>
      </header>

      {needsFullscreen && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-yellow-600/40 bg-yellow-900/20 px-4 py-2">
          <span className="text-sm text-yellow-200">Ative o modo tela cheia para melhor visualizacao.</span>
          <button
            onClick={activateFullscreen}
            className="rounded bg-yellow-500 hover:bg-yellow-400 text-slate-900 px-3 py-1 text-sm font-semibold"
          >
            Ativar Fullscreen
          </button>
        </div>
      )}

      {/* Indicador de rotacao */}
      <div className="mb-4 flex items-center gap-3">
        <span className="text-2xl font-semibold uppercase tracking-widest text-slate-300">
          {view === "planta" ? "Visao Planta" : "Visao TI"}
        </span>
        <div className="flex gap-1">
          <span className={`h-2 w-8 rounded ${view === "planta" ? "bg-emerald-400" : "bg-slate-700"}`} />
          <span className={`h-2 w-8 rounded ${view === "ti" ? "bg-emerald-400" : "bg-slate-700"}`} />
        </div>
      </div>

      {data === null ? (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16 text-center text-slate-400 text-xl">
          Conectando ao NOC...
        </div>
      ) : view === "planta" ? (
        <PlantaView data={data} />
      ) : (
        <TIView data={data} />
      )}
    </div>
  );
}

function PlantaView({ data }: { data: NocPayload }) {
  return (
    <div className="grid grid-cols-3 gap-6">
      <section className="col-span-2 rounded-xl border border-slate-700 bg-slate-900/40 p-6">
        <h2 className="text-lg font-semibold text-slate-300 mb-4 uppercase tracking-wide">
          Mapa da planta
        </h2>
        <PlantMap areas={data.plant} />
      </section>
      <aside className="rounded-xl border border-slate-700 bg-slate-900/40 p-6 flex flex-col justify-around">
        <BigKpi label="Ativos on-line" value={data.assets_up} color="text-emerald-400" />
        <BigKpi label="Ativos off-line" value={data.assets_down} color="text-red-400" />
        <BigKpi label="Producao hoje (un)" value={data.output_units.toLocaleString("pt-BR")} color="text-slate-100" />
        <BigKpi label="Alertas ativos" value={data.alerts_active_total} color="text-yellow-400" />
      </aside>
      <section className="col-span-3 rounded-xl border border-slate-700 bg-slate-900/40 p-6">
        <h2 className="text-lg font-semibold text-slate-300 mb-4 uppercase tracking-wide">
          OEE por linha
        </h2>
        <OeeGauges lines={data.oee} />
      </section>
    </div>
  );
}

function TIView({ data }: { data: NocPayload }) {
  const alerts = data.top_ti_alerts ?? [];
  return (
    <div className="grid grid-cols-3 gap-6">
      <aside className="rounded-xl border border-slate-700 bg-slate-900/40 p-6 flex flex-col justify-around">
        <BigKpi label="Ativos on-line" value={data.assets_up} color="text-emerald-400" />
        <BigKpi label="Ativos off-line" value={data.assets_down} color="text-red-400" />
        <BigKpi label="Total de alertas TI" value={alerts.length} color="text-yellow-400" />
      </aside>
      <section className="col-span-2 rounded-xl border border-slate-700 bg-slate-900/40 p-6">
        <h2 className="text-lg font-semibold text-slate-300 mb-4 uppercase tracking-wide">
          Top alertas de TI ({alerts.length})
        </h2>
        {alerts.length === 0 ? (
          <div className="text-slate-400 italic text-center py-8">
            Nenhum alerta de TI ativo.
          </div>
        ) : (
          <ul className="space-y-2 max-h-[540px] overflow-y-auto pr-2">
            {alerts.map((a) => {
              const badge = SEV_BADGE[a.severity] ?? "bg-slate-600 text-white";
              return (
                <li
                  key={a.id}
                  className="rounded-lg border border-slate-700 bg-slate-900/60 p-3"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`rounded px-2 py-0.5 text-xs font-bold uppercase ${badge}`}>
                      {a.severity}
                    </span>
                    <span className="text-sm text-slate-100 flex-1 truncate">
                      {a.summary ?? "(sem summary)"}
                    </span>
                  </div>
                  {a.asset && (
                    <div className="text-xs text-slate-400 font-mono">{a.asset}</div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

function BigKpi({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-6xl font-bold tabular-nums ${color}`}>{value}</div>
      <div className="text-sm text-slate-400 uppercase tracking-wide mt-1">{label}</div>
    </div>
  );
}