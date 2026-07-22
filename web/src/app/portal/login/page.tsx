"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { portalLogin, saveToken } from "@/lib/api";

export default function PortalLoginPage() {
  const router = useRouter();
  const [sam, setSam] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await portalLogin(sam, password);
      saveToken(result.access_token);
      sessionStorage.setItem("infranoc.portal_display_name", result.display_name);
      router.push("/portal/home");
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
      <form onSubmit={handleSubmit} style={{ width: 320, display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ fontSize: 20, textAlign: "center", marginBottom: 8, color: "var(--fg)" }}>Portal InfraNOC</h1>
        <label className="field">
          <span className="field-label">Usuario (sAMAccountName)</span>
          <input className="field-select" value={sam} onChange={(e) => setSam(e.target.value)} autoFocus />
        </label>
        <label className="field">
          <span className="field-label">Senha</span>
          <input className="field-select" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <div className="login-error">{error}</div>}
        <button type="submit" className="logout-btn" disabled={busy}>
          {busy ? "Entrando..." : "Entrar"}
        </button>
        <a href="/portal/reset-senha" style={{ textAlign: "center", fontSize: 13, color: "var(--accent-strong)" }}>
          Esqueci minha senha
        </a>
      </form>
    </div>
  );
}
