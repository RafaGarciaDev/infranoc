"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listComputers, setComputerEnabled, moveComputer, deleteComputer, ADComputer } from "@/lib/api";

export default function ComputersPage() {
  const [computers, setComputers] = useState<ADComputer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listComputers();
      data.sort((a, b) => a.name.localeCompare(b.name));
      setComputers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function handleToggle(dn: string, currentlyDisabled: boolean) {
    setBusy(dn);
    setError(null);
    try {
      await setComputerEnabled(dn, currentlyDisabled);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao alterar status.");
    } finally {
      setBusy(null);
    }
  }

  async function handleMove(dn: string) {
    const newParentDn = window.prompt("DN completo do novo pai:");
    if (!newParentDn) return;
    setBusy(dn);
    setError(null);
    try {
      await moveComputer(dn, newParentDn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao mover computador.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(dn: string, name: string) {
    if (!confirm(`Excluir o computador "${name}"?`)) return;
    setBusy(dn);
    setError(null);
    try {
      await deleteComputer(dn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir computador.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell title="Computadores (Active Directory)">
      <div className="alerts-toolbar">
        <span className="alerts-count">
          {loading ? "carregando..." : `${computers.length} computador(es)`}
        </span>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      {!loading && computers.length === 0 ? (
        <div className="empty">Nenhum computador encontrado.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Sistema Operacional</th>
              <th>Status</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {computers.map((cpt) => (
              <tr key={cpt.dn}>
                <td className="alert-name">{cpt.name}</td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{cpt.os || "-"}</td>
                <td>
                  <span className={cpt.disabled ? "badge badge-status-firing" : "badge badge-status-resolved"}>
                    {cpt.disabled ? "desabilitado" : "ativo"}
                  </span>
                </td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="logout-btn" disabled={busy === cpt.dn} onClick={() => handleToggle(cpt.dn, cpt.disabled)}>
                      {cpt.disabled ? "Habilitar" : "Desabilitar"}
                    </button>
                    <button className="logout-btn" disabled={busy === cpt.dn} onClick={() => handleMove(cpt.dn)}>
                      Mover
                    </button>
                    <button className="logout-btn" disabled={busy === cpt.dn} onClick={() => handleDelete(cpt.dn, cpt.name)}>
                      Excluir
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
