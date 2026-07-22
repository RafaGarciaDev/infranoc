"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import {
  listVpnUsers, createVpnUser, revokeVpnUser, reactivateVpnUser, updateVpnUser, simulateHandshake, downloadVpnConfig, listVpnSessions,
  VpnUser, VpnSessionItem,
} from "@/lib/api";

function fmtDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtBytes(n: number): string {
  if (n > 1_000_000) return `${(n / 1_000_000).toFixed(1)} MB`;
  if (n > 1_000) return `${(n / 1_000).toFixed(1)} KB`;
  return `${n} B`;
}

export default function VpnPage() {
  const [users, setUsers] = useState<VpnUser[]>([]);
  const [sessions, setSessions] = useState<VpnSessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [editingUser, setEditingUser] = useState<VpnUser | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editAdSam, setEditAdSam] = useState("");
  const [editExpiresAt, setEditExpiresAt] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [u, s] = await Promise.all([listVpnUsers(), listVpnSessions()]);
      setUsers(u);
      setSessions(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setBusy("__new__");
    setError(null);
    try {
      await createVpnUser(name, email);
      setName("");
      setEmail("");
      setShowForm(false);
      await load();
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao criar usuario.");
    } finally {
      setBusy(null);
    }
  }

  async function handleRevoke(u: VpnUser) {
    if (!confirm(`Revogar o acesso VPN de "${u.name}"?`)) return;
    setBusy(u.id);
    setError(null);
    try {
      await revokeVpnUser(u.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao revogar.");
    } finally {
      setBusy(null);
    }
  }

  async function handleReactivate(u: VpnUser) {
    setBusy(u.id);
    setError(null);
    try {
      await reactivateVpnUser(u.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao reativar.");
    } finally {
      setBusy(null);
    }
  }

  async function handleSimulateHandshake(u: VpnUser) {
    setBusy(u.id);
    setError(null);
    try {
      await simulateHandshake(u.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao simular handshake.");
    } finally {
      setBusy(null);
    }
  }

  function handleOpenEdit(u: VpnUser) {
    setEditingUser(u);
    setEditName(u.name);
    setEditEmail(u.email);
    setEditAdSam(u.ad_sam ?? "");
    setEditExpiresAt(u.expires_at ? u.expires_at.slice(0, 10) : "");
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editingUser) return;
    setBusy(editingUser.id);
    setError(null);
    try {
      await updateVpnUser(editingUser.id, {
        name: editName,
        email: editEmail,
        ad_sam: editAdSam || null,
        expires_at: editExpiresAt ? new Date(editExpiresAt).toISOString() : null,
      });
      setEditingUser(null);
      await load();
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao editar usuario.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDownload(u: VpnUser) {
    try {
      await downloadVpnConfig(u.id, u.email.split("@")[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao baixar config.");
    }
  }

  return (
    <Shell title="VPN (simulado)">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      <h2 style={{ marginBottom: 8 }}>Usuarios</h2>
      <div className="alerts-toolbar">
        <span className="alerts-count">{loading ? "carregando..." : `${users.length} usuario(s)`}</span>
        <button className="logout-btn" style={{ marginLeft: "auto" }} onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancelar" : "+ Novo usuario"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16 }}>
          <label className="field">
            <span className="field-label">Nome</span>
            <input className="field-select" value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label className="field">
            <span className="field-label">E-mail</span>
            <input className="field-select" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <button type="submit" className="logout-btn" disabled={busy === "__new__"}>
            {busy === "__new__" ? "Criando..." : "Criar"}
          </button>
        </form>
      )}

      {editingUser && (
        <form onSubmit={handleUpdate} style={{ display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16 }}>
          <label className="field">
            <span className="field-label">Nome</span>
            <input className="field-select" value={editName} onChange={(e) => setEditName(e.target.value)} required />
          </label>
          <label className="field">
            <span className="field-label">E-mail</span>
            <input className="field-select" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} required />
          </label>
          <label className="field">
            <span className="field-label">AD SAM</span>
            <input className="field-select" value={editAdSam} onChange={(e) => setEditAdSam(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Expira em</span>
            <input type="date" className="field-select" value={editExpiresAt} onChange={(e) => setEditExpiresAt(e.target.value)} />
          </label>
          <button type="submit" className="logout-btn" disabled={busy === editingUser.id}>
            {busy === editingUser.id ? "Salvando..." : "Salvar"}
          </button>
          <button type="button" className="logout-btn" onClick={() => setEditingUser(null)}>
            Cancelar
          </button>
        </form>
      )}

      <table className="alerts-table" style={{ marginBottom: 24 }}>
        <thead>
          <tr><th>Nome</th><th>IP interno</th><th>Status</th><th>Expira em</th><th>Acoes</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td className="alert-name">{u.name}</td>
              <td style={{ fontFamily: "monospace", fontSize: 12 }}>{u.internal_ip}</td>
              <td>
                <span className={!u.active ? "badge-status-firing" : u.stale ? "badge badge-cat" : "badge-status-resolved"}>
                  {!u.active ? "revogado" : u.stale ? "inativa" : "ativo"}
                </span>
              </td>
              <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(u.expires_at)}</td>
              <td>
                <div style={{ display: "flex", gap: 6 }}>
                  <button className="logout-btn" onClick={() => handleDownload(u)}>Baixar config</button>
                  <button className="logout-btn" onClick={() => handleOpenEdit(u)}>Editar</button>
                  {u.active && u.stale && (
                    <button className="logout-btn" disabled={busy === u.id} onClick={() => handleSimulateHandshake(u)}>
                      Simular handshake
                    </button>
                  )}
                  {u.active ? (
                    <button className="logout-btn" disabled={busy === u.id} onClick={() => handleRevoke(u)}>
                      Revogar
                    </button>
                  ) : (
                    <button className="logout-btn" disabled={busy === u.id} onClick={() => handleReactivate(u)}>
                      Reativar
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginBottom: 8 }}>Sessoes ativas</h2>
      <table className="alerts-table">
        <thead>
          <tr><th>Usuario</th><th>Endpoint</th><th>Ultimo handshake</th><th>RX / TX</th><th>Status</th></tr>
        </thead>
        <tbody>
          {sessions.map((s, i) => (
            <tr key={i}>
              <td className="alert-name">{s.user_name}</td>
              <td style={{ fontFamily: "monospace", fontSize: 12 }}>{s.endpoint_publico}</td>
              <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(s.last_handshake)}</td>
              <td style={{ fontSize: 12 }}>{fmtBytes(s.bytes_rx)} / {fmtBytes(s.bytes_tx)}</td>
              <td>
                <span className={s.stale ? "badge badge-cat" : "badge-status-resolved"}>
                  {s.stale ? "sem handshake recente" : "ok"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}
