"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import {
  listDeviceAssets, listDeviceCommands, executeDeviceCommand, listDeviceExecutions,
  DeviceAsset, DeviceCommandItem, DeviceExecutionItem,
} from "@/lib/api";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function statusBadgeClass(status: string): string {
  if (status === "success") return "badge-status-resolved";
  if (status === "error") return "badge-status-firing";
  return "badge badge-cat";
}

function DispositivosContent() {
  const searchParams = useSearchParams();
  const assetIdFromUrl = searchParams.get("asset");

  const [assets, setAssets] = useState<DeviceAsset[]>([]);
  const [selected, setSelected] = useState<DeviceAsset | null>(null);
  const [commands, setCommands] = useState<DeviceCommandItem[]>([]);
  const [executions, setExecutions] = useState<DeviceExecutionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ commandName: string; status: string; output: string | null } | null>(null);
  const [pendingValues, setPendingValues] = useState<Record<string, string>>({});

  useEffect(() => {
    (async () => {
      setError(null);
      try {
        const a = await listDeviceAssets();
        setAssets(a);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro inesperado.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const loadAssetDetail = useCallback(async (asset: DeviceAsset) => {
    setSelected(asset);
    setLastResult(null);
    setError(null);
    try {
      const [cmds, execs] = await Promise.all([
        listDeviceCommands(asset.asset_id),
        listDeviceExecutions(asset.asset_id),
      ]);
      setCommands(cmds);
      setExecutions(execs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar detalhes do ativo.");
    }
  }, []);

  useEffect(() => {
    if (!assetIdFromUrl || loading) return;
    const found = assets.find((a) => a.asset_id === assetIdFromUrl);
    if (found) loadAssetDetail(found);
  }, [assetIdFromUrl, loading, assets, loadAssetDetail]);

  async function handleExecute(cmd: DeviceCommandItem) {
    if (!selected) return;
    if (cmd.kind === "action" && !confirm(`Executar "${cmd.name}" em ${selected.asset_name}?`)) return;
    setBusy(cmd.id);
    setError(null);
    try {
      const value = cmd.value_type ? pendingValues[cmd.id] : undefined;
      const result = await executeDeviceCommand(selected.asset_id, cmd.id, value);
      setLastResult({ commandName: result.command_name, status: result.status, output: result.output });
      const execs = await listDeviceExecutions(selected.asset_id);
      setExecutions(execs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao executar comando.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell title="Dispositivos">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div style={{ display: "flex", gap: 24 }}>
        <div style={{ flex: "0 0 320px" }}>
          <h2 style={{ marginBottom: 8 }}>Ativos</h2>
          <div className="alerts-toolbar">
            <span className="alerts-count">{loading ? "carregando..." : `${assets.length} ativo(s)`}</span>
          </div>
          <table className="alerts-table">
            <thead>
              <tr><th>Nome</th><th>Protocolo</th></tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr
                  key={a.asset_id}
                  onClick={() => loadAssetDetail(a)}
                  style={{ cursor: "pointer", background: selected?.asset_id === a.asset_id ? "var(--bg-1)" : undefined }}
                >
                  <td className="alert-name">
                    {a.asset_name}{" "}
                    <span className={a.is_real ? "badge-status-resolved" : "badge badge-cat"} style={{ marginLeft: 6, fontSize: 10 }}>
                      {a.is_real ? "real" : "simulado"}
                    </span>
                  </td>
                  <td style={{ fontFamily: "monospace", fontSize: 12 }}>{a.protocol}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ flex: 1 }}>
          {!selected ? (
            <p style={{ color: "var(--fg-2)" }}>Selecione um ativo para ver os comandos disponiveis.</p>
          ) : (
            <>
              <h2 style={{ marginBottom: 4 }}>
                {selected.asset_name}{" "}
                <span className={selected.is_real ? "badge-status-resolved" : "badge badge-cat"} style={{ fontSize: 11 }}>
                  {selected.is_real ? "real" : "simulado"}
                </span>
              </h2>
              <p style={{ color: "var(--fg-2)", fontSize: 13, marginBottom: 16 }}>
                {selected.asset_type} via {selected.protocol}{selected.port ? `:${selected.port}` : ""}
              </p>

              <h3 style={{ marginBottom: 8 }}>Comandos</h3>
              {commands.length === 0 ? (
                <p style={{ color: "var(--fg-2)" }}>Nenhum comando cadastrado para este tipo de ativo ainda.</p>
              ) : (
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
                  {commands.map((c) => (
                    <div key={c.id} style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      {c.value_type && (
                        <input
                          placeholder="valor"
                          value={pendingValues[c.id] ?? ""}
                          onChange={(e) => setPendingValues((p) => ({ ...p, [c.id]: e.target.value }))}
                          style={{ width: 70 }}
                        />
                      )}
                      <button
                        className="logout-btn"
                        disabled={busy === c.id}
                        onClick={() => handleExecute(c)}
                      >
                        {busy === c.id ? "Executando..." : c.name}
                        {c.kind === "action" ? " \u26a0" : ""}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {lastResult && (
                <div className="alerts-toolbar" style={{ marginBottom: 16, flexDirection: "column", alignItems: "flex-start" }}>
                  <strong>{lastResult.commandName}</strong>
                  <span className={statusBadgeClass(lastResult.status)}>{lastResult.status}</span>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, marginTop: 8 }}>{lastResult.output}</pre>
                </div>
              )}

              <h3 style={{ marginBottom: 8 }}>Historico</h3>
              <table className="alerts-table">
                <thead>
                  <tr><th>Comando</th><th>Status</th><th>Quando</th><th>Por</th></tr>
                </thead>
                <tbody>
                  {executions.map((e, i) => (
                    <tr key={i}>
                      <td className="alert-name">{e.command_name}</td>
                      <td><span className={statusBadgeClass(e.status)}>{e.status}</span></td>
                      <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(e.executed_at)}</td>
                      <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{e.executed_by ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}

export default function DispositivosPage() {
  return (
    <Suspense fallback={null}>
      <DispositivosContent />
    </Suspense>
  );
}
