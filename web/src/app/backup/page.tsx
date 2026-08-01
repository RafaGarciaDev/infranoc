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

  if (loading) return <Shell title="Painel de Backup"><div className="loading">carregando...</div></Shell>;

  return (
    <Shell title="Painel de Backup (simulado)">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      {kpis && (
        <div className="stat-row">
          <div className="stat-card">
            <div className="stat-label">Total de jobs</div>
            <div className="stat-value">{kpis.total_jobs}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">OK</div>
            <div className="stat-value ok">{kpis.jobs_ok}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Falharam</div>
            <div className="stat-value critical">{kpis.jobs_failed}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">RPO excedido</div>
            <div className="stat-value warn">{kpis.jobs_rpo_exceeded}</div>
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
          {jobs.length === 0 ? (
            <tr><td colSpan={7} className="empty">Nenhum job de backup encontrado.</td></tr>
          ) : jobs.map((j) => (
            <React.Fragment key={j.id}>
              <tr onClick={() => handleToggle(j)}>
                <td className="alert-name">{j.name}</td>
                <td className="text-sm">{j.source}</td>
                <td className="text-sm">{j.target}</td>
                <td className="text-sm text-muted">{j.schedule}</td>
                <td><span className={statusColor(j)}>{j.last_status}{j.rpo_exceeded ? " (RPO)" : ""}</span></td>
                <td className="text-sm">{j.actual_rpo_hours ?? "-"}h / {j.rpo_target_hours}h</td>
                <td>{j.restore_point_count}</td>
              </tr>
              {openJobId === j.id && (
                <tr>
                  <td colSpan={7} style={{ background: "var(--bg-2)", padding: 12 }}>
                    {pointsLoading ? (
                      <span className="loading">carregando...</span>
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
                              <td className="text-sm text-muted">{fmtDate(p.expires_at)}</td>
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
