"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import {
  getLinuxSnapshot, listLinuxUsers, listSystemdUnits, systemdAction, getLinuxDisk,
  toolkitPortCheck, toolkitSs,
  LinuxSnapshot, LinuxUser, SystemdUnit, DiskUsage, PortCheckResult,
} from "@/lib/api";

export default function LinuxToolkitPage() {
  const [snapshot, setSnapshot] = useState<LinuxSnapshot | null>(null);
  const [users, setUsers] = useState<LinuxUser[]>([]);
  const [units, setUnits] = useState<SystemdUnit[]>([]);
  const [unitFilter, setUnitFilter] = useState("");
  const [disk, setDisk] = useState<DiskUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyUnit, setBusyUnit] = useState<string | null>(null);

  const [pcHost, setPcHost] = useState("192.168.56.30");
  const [pcPort, setPcPort] = useState("22");
  const [pcResult, setPcResult] = useState<PortCheckResult | null>(null);
  const [pcBusy, setPcBusy] = useState(false);

  const [ssOutput, setSsOutput] = useState<string | null>(null);
  const [ssBusy, setSsBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [snap, us, un, dk] = await Promise.all([
        getLinuxSnapshot(), listLinuxUsers(), listSystemdUnits(unitFilter || undefined), getLinuxDisk(),
      ]);
      setSnapshot(snap);
      setUsers(us);
      setUnits(un);
      setDisk(dk);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [unitFilter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function handleUnitAction(unit: string, action: "start" | "stop" | "restart") {
    if (!confirm(`Confirma ${action} em ${unit}?`)) return;
    setBusyUnit(unit);
    setError(null);
    try {
      await systemdAction(unit, action);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro na acao.");
    } finally {
      setBusyUnit(null);
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

  async function handleSs() {
    setSsBusy(true);
    setSsOutput(null);
    setError(null);
    try {
      const out = await toolkitSs();
      setSsOutput(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao executar ss.");
    } finally {
      setSsBusy(false);
    }
  }

  if (loading) return <Shell title="Linux Ops + Toolkit"><div className="loading">carregando...</div></Shell>;

  return (
    <Shell title="Linux Ops + Toolkit de Diagnostico">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      <h2 className="section-title">Snapshot (MES01)</h2>
      {snapshot && (
        <pre className="code-block" style={{ marginBottom: 24 }}>
{snapshot.uptime}
{"\n"}
{snapshot.who}
        </pre>
      )}

      <h2 className="section-title">Disco</h2>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Mount</th><th>Tamanho</th><th>Usado</th><th>Livre</th><th>%</th></tr></thead>
        <tbody>
          {disk.length === 0 ? (
            <tr><td colSpan={5} className="empty">Nenhuma particao encontrada.</td></tr>
          ) : disk.map((d) => (
            <tr key={d.mount}>
              <td className="alert-name">{d.mount}</td>
              <td>{d.size}</td><td>{d.used}</td><td>{d.avail}</td>
              <td><span className="badge badge-cat">{d.percent}</span></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Usuarios locais ({users.length})</h2>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Usuario</th><th>UID</th><th>Home</th><th>Shell</th></tr></thead>
        <tbody>
          {users.length === 0 ? (
            <tr><td colSpan={4} className="empty">Nenhum usuario local encontrado.</td></tr>
          ) : users.map((u) => (
            <tr key={u.username}>
              <td className="alert-name">{u.username}</td>
              <td>{u.uid}</td><td className="text-sm">{u.home}</td><td className="text-sm">{u.shell}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Servicos systemd</h2>
      <div className="alerts-toolbar">
        <input
          className="field-select"
          placeholder="filtrar por nome..."
          value={unitFilter}
          onChange={(e) => setUnitFilter(e.target.value)}
        />
        <span className="alerts-count">{units.length} servico(s)</span>
      </div>
      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead><tr><th>Unidade</th><th>Status</th><th>Descricao</th><th>Acoes</th></tr></thead>
        <tbody>
          {units.length === 0 ? (
            <tr><td colSpan={4} className="empty">Nenhum servico encontrado.</td></tr>
          ) : units.map((u) => (
            <tr key={u.unit}>
              <td className="alert-name text-sm">{u.unit}</td>
              <td><span className={u.active === "active" ? "badge badge-status-resolved" : "badge badge-status-firing"}>{u.active}</span></td>
              <td className="text-sm text-muted">{u.description}</td>
              <td>
                <div style={{ display: "flex", gap: 6 }}>
                  <button className="logout-btn" disabled={busyUnit === u.unit} onClick={() => handleUnitAction(u.unit, "restart")}>Restart</button>
                  <button className="logout-btn" disabled={busyUnit === u.unit} onClick={() => handleUnitAction(u.unit, "stop")}>Stop</button>
                  <button className="logout-btn" disabled={busyUnit === u.unit} onClick={() => handleUnitAction(u.unit, "start")}>Start</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="section-title">Toolkit - Port Check</h2>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 12 }}>
        <label className="field">
          <span className="field-label">Host</span>
          <input className="field-select" value={pcHost} onChange={(e) => setPcHost(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Porta</span>
          <input className="field-select" value={pcPort} onChange={(e) => setPcPort(e.target.value)} style={{ width: 80 }} />
        </label>
        <button className="logout-btn" disabled={pcBusy} onClick={handlePortCheck}>
          {pcBusy ? "Testando..." : "Testar"}
        </button>
      </div>
      {pcResult && (
        <div style={{ marginBottom: 24 }}>
          <span className={pcResult.reachable ? "badge badge-status-resolved" : "badge badge-status-firing"}>
            {pcResult.reachable ? `Acessivel (${pcResult.latency_ms}ms)` : "Inacessivel"}
          </span>
        </div>
      )}

      <h2 className="section-title">Toolkit - Portas em escuta (ss -tulpn)</h2>
      <button className="logout-btn" disabled={ssBusy} onClick={handleSs} style={{ marginBottom: 12 }}>
        {ssBusy ? "Executando..." : "Executar"}
      </button>
      {ssOutput && (
        <pre className="code-block text-xs">
          {ssOutput}
        </pre>
      )}
    </Shell>
  );
}
