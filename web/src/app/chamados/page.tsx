"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listTicketLinks, TicketLink, TicketLinkStatus } from "@/lib/api";

const REFRESH_MS = 15000;

function statusBadge(status: TicketLinkStatus) {
  const cls = status === "open" ? "badge badge-status-firing" : "badge badge-status-resolved";
  return <span className={cls}>{status === "open" ? "aberto" : "fechado"}</span>;
}

function severityBadge(sev: string) {
  const known = ["critical", "high", "warning", "info"];
  const cls = known.includes(sev.toLowerCase())
    ? `badge badge-sev-${sev.toLowerCase()}`
    : "badge badge-cat";
  return <span className={cls}>{sev}</span>;
}

function fmtDateTime(iso: string | null) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChamadosPage() {
  const [links, setLinks] = useState<TicketLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fStatus, setFStatus] = useState<"" | TicketLinkStatus>("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listTicketLinks({ status: fStatus || undefined, limit: 200 });
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setLinks(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [fStatus]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  return (
    <Shell title="Chamados">
      <div className="alerts-toolbar">
        <label className="field">
          <span className="field-label">Status</span>
          <select
            className="field-select"
            value={fStatus}
            onChange={(e) => setFStatus(e.target.value as "" | TicketLinkStatus)}
          >
            <option value="">todos</option>
            <option value="open">aberto</option>
            <option value="closed">fechado</option>
          </select>
        </label>

        <span className="alerts-count">
          {loading ? "carregando..." : `${links.length} chamado(s)`}
        </span>
      </div>

      {error && (
        <div className="login-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!loading && links.length === 0 ? (
        <div className="empty">Nenhum chamado com esses filtros.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Alerta</th>
              <th>Ativo</th>
              <th>Severity</th>
              <th>Ticket</th>
              <th>Status</th>
              <th>Aberto</th>
              <th>Fechado</th>
            </tr>
          </thead>
          <tbody>
            {links.map((l) => {
              const linkTag = "a";
              return (
                <tr key={l.id}>
                  <td className="alert-name">{l.alertname}</td>
                  <td className="alert-asset">{l.asset ?? "-"}</td>
                  <td>{severityBadge(l.severity ?? "info")}</td>
                  <td>
                    <a href={l.ticket_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent-strong)" }}>#{l.ticket_id}</a>
                  </td>
                  <td>{statusBadge(l.status)}</td>
                  <td className="alert-time">{fmtDateTime(l.created_at)}</td>
                  <td className="alert-time">{fmtDateTime(l.closed_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Shell>
  );
}