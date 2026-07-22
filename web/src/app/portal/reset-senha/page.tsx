"use client";

import React, { useState } from "react";
import { useSearchParams } from "next/navigation";
import { requestPasswordReset, confirmPasswordReset } from "@/lib/api";

export default function PortalResetSenhaPage() {
  const searchParams = useSearchParams();
  const tokenFromUrl = searchParams.get("token") || "";

  const [sam, setSam] = useState("");
  const [resetUrl, setResetUrl] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [token, setToken] = useState(tokenFromUrl);
  const [newPassword, setNewPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSolicitar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await requestPasswordReset(sam);
      setResetUrl(r.reset_url);
      setAviso(r.aviso);
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao solicitar reset.");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmar(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await confirmPasswordReset(token, newPassword);
      setConfirmed(true);
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao confirmar reset.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <div style={{ width: 360, display: "flex", flexDirection: "column", gap: 16 }}>
        <h1 style={{ fontSize: 20, textAlign: "center", color: "var(--fg)" }}>Recuperar senha</h1>

        {error && <div className="login-error">{error}</div>}

        {confirmed ? (
          <div className="empty">Senha alterada com sucesso. Volte ao <a href="/portal/login" style={{ color: "var(--accent-strong)" }}>login</a>.</div>
        ) : tokenFromUrl || resetUrl ? (
          <form onSubmit={handleConfirmar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {aviso && <div className="login-error" style={{ fontSize: 12 }}>{aviso}</div>}
            {resetUrl && !tokenFromUrl && (
              <div style={{ fontSize: 12, color: "var(--fg-2)", wordBreak: "break-all" }}>
                Link de reset (ambiente de lab, sem e-mail real): {resetUrl}
              </div>
            )}
            <label className="field">
              <span className="field-label">Token</span>
              <input className="field-select" value={token} onChange={(e) => setToken(e.target.value)} required />
            </label>
            <label className="field">
              <span className="field-label">Nova senha</span>
              <input className="field-select" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            </label>
            <button type="submit" className="logout-btn" disabled={busy}>
              {busy ? "Confirmando..." : "Confirmar nova senha"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSolicitar} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label className="field">
              <span className="field-label">Usuario (sAMAccountName)</span>
              <input className="field-select" value={sam} onChange={(e) => setSam(e.target.value)} required />
            </label>
            <button type="submit" className="logout-btn" disabled={busy}>
              {busy ? "Enviando..." : "Solicitar reset"}
            </button>
          </form>
        )}

        <a href="/portal/login" style={{ textAlign: "center", fontSize: 13, color: "var(--accent-strong)" }}>
          Voltar ao login
        </a>
      </div>
    </div>
  );
}
