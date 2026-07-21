"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listBackupJobs, listRestorePoints, getBackupKpis, BackupJob, RestorePoint, BackupKpis } from "@/lib/api";

function statusColor(job: BackupJob): string {
  if (job.last_status === "failed") return "badge-status-firing";
  if (job.rpo_exceeded) return "badge badge-cat";
  return "badge-status-resolved";
}

function fmtDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function BackupPage() {
  const [kpis, setKpis] = useState<BackupKpis | null>(null);
  const [jobs, setJobs] = useState<BackupJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openJobId, setOpenJobId] = useState<string | null>(null);
  const [points, setPoints] = useState<RestorePoint[]>([]);
  const [pointsLoading, setPointsLoading] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [k, j] = await Promise.all([getBackupKpis(), listBackupJobs()]);
      setKpis(k);
      setJobs(j);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleToggle(job: BackupJob) {
    if (openJobId === job.id) {
      setOpenJobId(null);
      return;
    }
    setOpenJobId(job.id);
    setPointsLoading(true);
    try {
      const data = await listRestorePoints(job.id);
      setPoints(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao buscar restore points.");
    } finally {
      setPointsLoading(false);
    }
  }

  if (loading) return <Shell title="Painel de Backup"><div className="empty">carregando...</div></Shell>;

  return (
    <Shell title="Painel de Backup (simulado)">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      {kpis && (
        <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
          <div style={{ background: "var(--panel)", padding: 16, borderRadius: 8, border: "1px solid var(--border)", flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>Total de jobs</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{kpis.total_jobs}</div>
          </div>
          <div style={{ background: "var(--panel)", padding: 16, borderRadius: 8, border: "1px solid var(--border)", flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>OK</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#22c55e" }}>{kpis.jobs_ok}</div>
          </div>
          <div style={{ background: "var(--panel)", padding: 16, borderRadius: 8, border: "1px solid var(--border)", flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>Falharam</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#ef4444" }}>{kpis.jobs_failed}</div>
          </div>
          <div style={{ background: "var(--panel)", padding: 16, borderRadius: 8, border: "1px solid var(--border)", flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>RPO excedido</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#f59e0b" }}>{kpis.jobs_rpo_exceeded}</div>
          </div>
        </div>
      )}

      <table className="alerts-table">
        <thead>
          <tr>
            <th>Job</th>
            <th>Origem</th>
            <th>Destino</th>
            <th>Agenda</th>
            <th>Status</th>
            <th>RPO (atual / meta)</th>
            <th>Pontos</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <React.Fragment key={j.id}>
              <tr onClick={() => handleToggle(j)} style={{ cursor: "pointer" }}>
                <td className="alert-name">{j.name}</td>
                <td style={{ fontSize: 12 }}>{j.source}</td>
                <td style={{ fontSize: 12 }}>{j.target}</td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{j.schedule}</td>
                <td><span className={statusColor(j)}>{j.last_status}{j.rpo_exceeded ? " (RPO)" : ""}</span></td>
                <td style={{ fontSize: 12 }}>{j.actual_rpo_hours ?? "-"}h / {j.rpo_target_hours}h</td>
                <td>{j.restore_point_count}</td>
              </tr>
              {openJobId === j.id && (
                <tr>
                  <td colSpan={7} style={{ background: "var(--panel)", padding: 12 }}>
                    {pointsLoading ? (
                      <span>carregando...</span>
                    ) : (
                      <table style={{ width: "100%" }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: "left" }}>Timestamp</th>
                            <th style={{ textAlign: "left" }}>Tamanho</th>
                            <th style={{ textAlign: "left" }}>Status</th>
                            <th style={{ textAlign: "left" }}>Expira em</th>
                          </tr>
                        </thead>
                        <tbody>
                          {points.map((p, i) => (
                            <tr key={i}>
                              <td>{fmtDate(p.timestamp)}</td>
                              <td>{p.size_gb.toFixed(2)} GB</td>
                              <td>
                                <span className={p.status === "success" ? "badge-status-resolved" : "badge-status-firing"}>
                                  {p.status}
                                </span>
                              </td>
                              <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(p.expires_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}
