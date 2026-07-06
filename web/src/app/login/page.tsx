"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { login, saveToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const userRef = useRef<HTMLInputElement>(null);
  const passRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setError(null);
    const username = userRef.current?.value.trim() ?? "";
    const password = passRef.current?.value ?? "";
    if (!username || !password) {
      setError("Preencha usuario e senha.");
      return;
    }
    setLoading(true);
    try {
      const result = await login(username, password);
      saveToken(result.access_token);
      sessionStorage.setItem("infranoc.display_name", result.display_name);
      sessionStorage.setItem("infranoc.permissions", JSON.stringify(result.permissions));
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <div className="login-card">
        <div className="brand">
          <span className="brand-dot" />
          <span className="brand-name">InfraNOC</span>
          <span className="brand-sub">Centro de Operacoes - Vale Verde S/A</span>
        </div>
        <h1 className="login-title">Acesso ao painel</h1>
        <label className="field">
          <span className="field-label">Usuario</span>
          <input ref={userRef} className="field-input" type="text" autoComplete="username" onKeyDown={(e) => e.key === "Enter" && onSubmit()} placeholder="admin@valeverde.com" />
        </label>
        <label className="field">
          <span className="field-label">Senha</span>
          <input ref={passRef} className="field-input" type="password" autoComplete="current-password" onKeyDown={(e) => e.key === "Enter" && onSubmit()} placeholder="senha" />
        </label>
        {error && <div className="login-error">{error}</div>}
        <button className="login-btn" onClick={onSubmit} disabled={loading}>
          {loading ? "Autenticando..." : "Entrar"}
        </button>
        <p className="login-hint">Ambiente de laboratorio - autenticacao JWT contra a API FastAPI</p>
      </div>
    </main>
  );
}
