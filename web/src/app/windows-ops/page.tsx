"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import Tooltip from "@/components/Tooltip";
import {
  getWindowsSnapshot, listWindowsUsers, listWindowsServices, windowsServiceAction,
  getWindowsDisk, windowsNetstat, toolkitPortCheck,
  WindowsSnapshot, WindowsUser, WindowsService, WindowsDiskUsage, PortCheckResult,
} from "@/lib/api";

export default function WindowsOpsPage() {
  const [snapshot, setSnapshot] = useState<WindowsSnapshot | null>(null);
  const [users, setUsers] = useState<WindowsUser[]>([]);
  const [services, setServices] = useState<WindowsService[]>([]);
  const [serviceFilter, setServiceFilter] = useState("");
  const [disk, setDisk] = useState<WindowsDiskUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyService, setBusyService] = useState<string | null>(null);

  const [pcHost, setPcHost] = useState("192.168.56.10");
  const [pcPort, setPcPort] = useState("5985");
  const [pcResult, setPcResult] = useState<PortCheckResult | null>(null);
  const [pcBusy, setPcBusy] = useState(false);

  const [netstatOutput, setNetstatOutput] = useState<string | null>(null);
  const [netstatBusy, setNetstatBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [snap, us, sv, dk] = await Promise.all([
        getWindowsSnapshot(), listWindowsUsers(), listWindowsServices(serviceFilter || undefined), getWindowsDisk(),
      ]);
      setSnapshot(snap);
      setUsers(us);
      setServices(sv);
      setDisk(dk);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [serviceFilter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function handleServiceAction(name: string, action: "start" | "stop" | "restart") {
    if (!confirm(`Confirma ${action} em ${name}?`)) return;
    setBusyService(name);
    setError(null);
    try {
      await windowsServiceAction(name, action);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro na acao.");
    } finally {
      setBusyService(null);
    }
  }

  async function handlePortCheck() {
    setPcBusy(true);
    setPcResult(null);
    setError(null);
    try {
      const r = await toolkitPortCheck(pcHost, parseInt(pcPort, 10));
      setPcResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro no port-check.");
    } finally {
      setPcBusy(false);
    }
  }

  async function handleNetstat() {
    setNetstatBusy(true);
    setNetstatOutput(null);
    setError(null);
    try {
      const out = await windowsNetstat();
      setNetstatOutput(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao executar netstat.");
    } finally {
      setNetstatBusy(false);
    }
  }

  if (loading) return <Shell title="Windows Server Ops"><div className="empty">carregando...</div></Shell>;

  return (
    <Shell title="Windows Server Ops">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      <h2 style={{ marginBottom: 8 }}>Snapshot (DC01)</h2>
      {snapshot && (
        <div style={{ marginBottom: 24 }}>
          <pre style={{
            whiteSpace: "pre-wrap", background: "var(--bg-1)", padding: 12, borderRadius: 8,
            border: "1px solid var(--border)", fontSize: 12, marginBottom: 12,
          }}>
{snapshot.caption} ({snapshot.hostname})
{"\n"}Ultimo boot: {snapshot.last_boot}
          </pre>
          <table className="alerts-table">
            <thead><tr><th>Usuario</th><th>Sessao</th><th>Estado</th><th>Ocioso</th><th>Logon</th></tr></thead>
            <tbody>
              {snapshot.sessions.length === 0 ? (
                <tr><td colSpan={5} className="empty">nenhuma sessao ativa</td></tr>
              ) : (
                snapshot.sessions.map((s, i) => (
                  <tr key={i}>
                    <td className="alert-name">{s.username}</td>
                    <td>{s.session_name}</td>
                    <td><span className="badge badge-status-resolved">{s.state}</span></td>
                    <td>{s.idle_time}</td>
                    <td style={{ fontSize: 12 }}>{s.logon_time}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <h2 style={{ marginBottom: 8 }}>Disco</h2>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Drive</th><th>Tamanho</th><th>Livre</th><th>% usado</th></tr></thead>
        <tbody>
          {disk.map((d) => (
            <tr key={d.drive}>
              <td className="alert-name">{d.drive}</td>
              <td>{d.size_gb} GB</td><td>{d.free_gb} GB</td>
              <td><span className="badge badge-cat">{d.percent_used}%</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginBottom: 8 }}>Usuarios locais ({users.length})</h2>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Usuario</th><th>Status</th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.name}>
              <td className="alert-name">{u.name}</td>
              <td>
                <span className={u.enabled ? "badge badge-status-resolved" : "badge badge-cat"}>
                  {u.enabled ? "habilitado" : "desabilitado"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginBottom: 8 }}>Servicos Windows</h2>
      <div className="alerts-toolbar">
        <input
          className="field-select"
          placeholder="filtrar por nome..."
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
        />
        <span className="alerts-count">{services.length} servico(s)</span>
      </div>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Nome</th><th>Status</th><th>Inicializacao</th><th>Acoes</th></tr></thead>
        <tbody>
          {services.map((s) => (
            <tr key={s.name}>
              <td className="alert-name" style={{ fontSize: 12 }}>{s.display_name}</td>
              <td><span className={s.status === "Running" ? "badge badge-status-resolved" : "badge badge-status-firing"}>{s.status}</span></td>
              <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{s.start_type}</td>
              <td>
                <div style={{ display: "flex", gap: 6 }}>
                  <Tooltip label={`Reinicia o servico ${s.display_name} (para e inicia via WinRM)`}>
                    <button className="logout-btn" disabled={busyService === s.name} onClick={() => handleServiceAction(s.name, "restart")}>Restart</button>
                  </Tooltip>
                  <Tooltip label={`Para o servico ${s.display_name} - pode afetar outros sistemas que dependem dele`}>
                    <button className="logout-btn" disabled={busyService === s.name} onClick={() => handleServiceAction(s.name, "stop")}>Stop</button>
                  </Tooltip>
                  <Tooltip label={`Inicia o servico ${s.display_name}`}>
                    <button className="logout-btn" disabled={busyService === s.name} onClick={() => handleServiceAction(s.name, "start")}>Start</button>
                  </Tooltip>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginBottom: 8 }}>Toolkit - Port Check</h2>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label className="field">
          <span className="field-label">Host</span>
          <input className="field-select" value={pcHost} onChange={(e) => setPcHost(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Porta</span>
          <input className="field-select" value={pcPort} onChange={(e) => setPcPort(e.target.value)} style={{ width: 80 }} />
        </label>
        <Tooltip label="Testa se a porta esta acessivel a partir do backend, sem precisar de SSH/WinRM">
          <button className="logout-btn" disabled={pcBusy} onClick={handlePortCheck}>
            {pcBusy ? "Testando..." : "Testar"}
          </button>
        </Tooltip>
      </div>
      {pcResult && (
        <div style={{ marginBottom: 24 }}>
          <span className={pcResult.reachable ? "badge badge-status-resolved" : "badge badge-status-firing"}>
            {pcResult.reachable ? `Acessivel (${pcResult.latency_ms}ms)` : "Inacessivel"}
          </span>
        </div>
      )}

      <h2 style={{ marginBottom: 8 }}>Toolkit - Portas em escuta (Get-NetTCPConnection)</h2>
      <Tooltip label="Lista as portas TCP em estado de escuta no servidor, via WinRM">
        <button className="logout-btn" disabled={netstatBusy} onClick={handleNetstat} style={{ marginBottom: 12 }}>
          {netstatBusy ? "Executando..." : "Executar"}
        </button>
      </Tooltip>
      {netstatOutput && (
        <pre style={{
          whiteSpace: "pre-wrap", background: "var(--bg-1)", padding: 12, borderRadius: 8,
          border: "1px solid var(--border)", fontSize: 11, overflowX: "auto",
        }}>
          {netstatOutput}
        </pre>
      )}
    </Shell>
  );
}
