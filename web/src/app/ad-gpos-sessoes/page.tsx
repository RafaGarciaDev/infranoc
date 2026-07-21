"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listGPOs, listRdpSessions, GPO, RdpSession } from "@/lib/api";

export default function GposSessoesPage() {
  const [gpos, setGpos] = useState<GPO[]>([]);
  const [sessions, setSessions] = useState<RdpSession[]>([]);
  const [gposError, setGposError] = useState<string | null>(null);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listGPOs();
      setGpos(data);
      setGposError(null);
    } catch (e) {
      setGposError(e instanceof Error ? e.message : "Erro ao carregar GPOs.");
    }
    try {
      const data = await listRdpSessions();
      setSessions(data);
      setSessionsError(null);
    } catch (e) {
      setSessionsError(e instanceof Error ? e.message : "Erro ao carregar sessoes RDP.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Shell title="GPOs e Sessoes RDP">
      <h2 style={{ marginBottom: 12 }}>Group Policy Objects</h2>
      {gposError && <div className="login-error" style={{ marginBottom: 12 }}>{gposError}</div>}
      {loading ? (
        <div className="empty">carregando...</div>
      ) : gpos.length === 0 && !gposError ? (
        <div className="empty">Nenhuma GPO encontrada.</div>
      ) : !gposError && (
        <table className="alerts-table" style={{ marginBottom: 32 }}>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Status</th>
              <th>Criada em</th>
              <th>Modificada em</th>
            </tr>
          </thead>
          <tbody>
            {gpos.map((g) => (
              <tr key={g.id}>
                <td className="alert-name">{g.name}</td>
                <td><span className="badge badge-cat">{g.status}</span></td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{g.created}</td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{g.modified}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2 style={{ marginBottom: 12 }}>Sessoes RDP Ativas</h2>
      {sessionsError && <div className="login-error" style={{ marginBottom: 12 }}>{sessionsError}</div>}
      {loading ? (
        <div className="empty">carregando...</div>
      ) : sessions.length === 0 && !sessionsError ? (
        <div className="empty">Nenhuma sessao ativa no momento.</div>
      ) : !sessionsError && (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Sessao</th>
              <th>Estado</th>
              <th>Ocioso</th>
              <th>Logon</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s, i) => (
              <tr key={i}>
                <td className="alert-name">{s.username}</td>
                <td>{s.session_name || "-"}</td>
                <td><span className="badge badge-cat">{s.state}</span></td>
                <td>{s.idle_time}</td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{s.logon_time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
