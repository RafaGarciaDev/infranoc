"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listSecurityEvents, getSecurityKpis, SecurityEvent, SecurityKpis } from "@/lib/api";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function levelBadge(level: number): string {
  if (level >= 12) return "badge badge-sev-critical";
  if (level >= 8) return "badge badge-sev-high";
  if (level >= 4) return "badge badge-sev-warning";
  return "badge badge-sev-info";
}

export default function SecurityPage() {
  const [kpis, setKpis] = useState<SecurityKpis | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [levelFilter, setLevelFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const levelMin = levelFilter ? parseInt(levelFilter, 10) : undefined;
      const [k, e] = await Promise.all([getSecurityKpis(), listSecurityEvents(levelMin)]);
      setKpis(k);
      setEvents(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [levelFilter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  if (loading) return <Shell title="Seguranca / SIEM (simulado)"><div className="loading">carregando...</div></Shell>;

  return (
    <Shell title="Seguranca / SIEM (simulado)">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      {kpis && (
        <div className="stat-row">
          <div className="stat-card">
            <div className="stat-label">Total de eventos (30d)</div>
            <div className="stat-value">{kpis.total_events}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Criticos (nivel 12+)</div>
            <div className="stat-value critical">{kpis.critical_count}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Altos (nivel 8-11)</div>
            <div className="stat-value warn">{kpis.high_count}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Hosts afetados</div>
            <div className="stat-value">{kpis.hosts_afetados}</div>
          </div>
        </div>
      )}

      {kpis && kpis.top_techniques.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2 className="section-title">Top tecnicas MITRE ATT&amp;CK</h2>
          <table className="alerts-table">
            <thead>
              <tr><th>Tecnica</th><th>Tatica</th><th>Ocorrencias</th></tr>
            </thead>
            <tbody>
              {kpis.top_techniques.map((t) => (
                <tr key={t.technique_id}>
                  <td className="alert-name">{t.technique_id} - {t.technique_name}</td>
                  <td><span className="badge badge-cat">{t.tactic}</span></td>
                  <td>{t.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="alerts-toolbar">
        <label className="field">
          <span className="field-label">Nivel minimo</span>
          <select className="field-select" value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}>
            <option value="">todos</option>
            <option value="8">8+ (alto)</option>
            <option value="12">12+ (critico)</option>
          </select>
        </label>
        <span className="alerts-count">{events.length} evento(s)</span>
      </div>

      <table className="alerts-table">
        <thead>
          <tr><th>Timestamp</th><th>Host</th><th>Regra</th><th>Nivel</th><th>Tecnica MITRE</th></tr>
        </thead>
        <tbody>
          {events.length === 0 ? (
            <tr><td colSpan={5} className="empty">Nenhum evento de seguranca encontrado.</td></tr>
          ) : events.map((ev, i) => (
            <tr key={i}>
              <td className="text-sm text-muted">{fmtDate(ev.timestamp)}</td>
              <td className="alert-name">{ev.source_host}</td>
              <td className="text-sm">{ev.rule_description}</td>
              <td><span className={levelBadge(ev.level)}>{ev.level}</span></td>
              <td className="text-sm">{ev.mitre_technique_id} - {ev.mitre_technique_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}
