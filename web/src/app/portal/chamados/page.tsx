"use client";

import React, { useCallback, useEffect, useState } from "react";
import PortalShell from "@/components/PortalShell";
import { listMyTickets, createMyTicket, PortalTicket } from "@/lib/api";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function PortalChamadosPage() {
  const [tickets, setTickets] = useState<PortalTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [detail, setDetail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listMyTickets();
      setTickets(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !detail.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createMyTicket(title, detail);
      setTitle("");
      setDetail("");
      setShowForm(false);
      await load();
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao abrir chamado.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PortalShell title="Meus Chamados">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      {!showForm ? (
        <button className="logout-btn" style={{ marginBottom: 16 }} onClick={() => setShowForm(true)}>
          + Abrir novo chamado
        </button>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 24 }}>
          <label className="field">
            <span className="field-label">Titulo</span>
            <input className="field-select" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label className="field">
            <span className="field-label">Descreva o problema</span>
            <textarea className="field-select" rows={4} value={detail} onChange={(e) => setDetail(e.target.value)} required />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" className="logout-btn" disabled={submitting}>
              {submitting ? "Enviando..." : "Enviar"}
            </button>
            <button type="button" className="logout-btn" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="empty">carregando...</div>
      ) : tickets.length === 0 ? (
        <div className="empty">Voce ainda nao abriu nenhum chamado.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {tickets.map((t) => (
            <div key={t.id} style={{ background: "var(--panel)", padding: 12, borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <strong>{t.title}</strong>
                <span className={t.status === "open" ? "badge-status-firing" : "badge-status-resolved"}>{t.status}</span>
              </div>
              <div style={{ fontSize: 13, color: "var(--fg-2)", marginBottom: 6 }}>{t.detail}</div>
              <div style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(t.created_at)}</div>
            </div>
          ))}
        </div>
      )}
    </PortalShell>
  );
}
