"use client";

import React, { useState } from "react";
import Shell from "@/components/Shell";
import { bulkEnableUsers, bulkChangeGroup, bulkResetPassword, BulkResultItem } from "@/lib/api";

type Action = "enable" | "disable" | "group-add" | "group-remove" | "reset-password";

export default function BulkPage() {
  const [samsText, setSamsText] = useState("");
  const [action, setAction] = useState<Action>("enable");
  const [groupDn, setGroupDn] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const [results, setResults] = useState<BulkResultItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function parseSams(): string[] {
    return samsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const sams = parseSams();
    if (sams.length === 0) {
      setError("Cole ao menos um sAMAccountName (um por linha).");
      return;
    }
    setBusy(true);
    setError(null);
    setResults(null);
    try {
      let data: BulkResultItem[];
      if (action === "enable") {
        data = await bulkEnableUsers(sams, true);
      } else if (action === "disable") {
        data = await bulkEnableUsers(sams, false);
      } else if (action === "group-add") {
        if (!groupDn) { setError("Informe o DN do grupo."); setBusy(false); return; }
        data = await bulkChangeGroup(sams, groupDn, true);
      } else if (action === "group-remove") {
        if (!groupDn) { setError("Informe o DN do grupo."); setBusy(false); return; }
        data = await bulkChangeGroup(sams, groupDn, false);
      } else {
        if (!newPassword) { setError("Informe a nova senha."); setBusy(false); return; }
        data = await bulkResetPassword(sams, newPassword, mustChange);
      }
      setResults(data);
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro na operacao em massa.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Operacoes em Massa (Active Directory)">
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 700 }}>
        <label className="field">
          <span className="field-label">sAMAccountName (um por linha)</span>
          <textarea
            className="field-select"
            rows={8}
            value={samsText}
            onChange={(e) => setSamsText(e.target.value)}
            placeholder={"julia.moreira\nalexandre.fernandes\n..."}
            style={{ fontFamily: "monospace", resize: "vertical" }}
          />
        </label>

        <label className="field">
          <span className="field-label">Acao</span>
          <select className="field-select" value={action} onChange={(e) => setAction(e.target.value as Action)}>
            <option value="enable">Habilitar contas</option>
            <option value="disable">Desabilitar contas</option>
            <option value="group-add">Adicionar a um grupo</option>
            <option value="group-remove">Remover de um grupo</option>
            <option value="reset-password">Resetar senha (mesma senha para todos)</option>
          </select>
        </label>

        {(action === "group-add" || action === "group-remove") && (
          <label className="field">
            <span className="field-label">DN completo do grupo</span>
            <input className="field-select" value={groupDn} onChange={(e) => setGroupDn(e.target.value)} />
          </label>
        )}

        {action === "reset-password" && (
          <>
            <div className="login-error" style={{ marginBottom: 0 }}>
              Atencao: todos os usuarios listados receberao a MESMA senha temporaria.
              Use apenas em ambiente de laboratorio/demo; em producao, gere senhas
              individuais aleatorias por usuario.
            </div>
            <label className="field">
              <span className="field-label">Nova senha (temporaria)</span>
              <input
                className="field-select"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input type="checkbox" checked={mustChange} onChange={(e) => setMustChange(e.target.checked)} />
              <span>Exigir troca de senha no proximo logon</span>
            </label>
          </>
        )}

        {error && <div className="login-error">{error}</div>}

        <div>
          <button type="submit" className="logout-btn" disabled={busy}>
            {busy ? "Processando..." : "Executar"}
          </button>
        </div>
      </form>

      {results && (
        <div style={{ marginTop: 24 }}>
          <h3>Resultado ({results.filter((r) => r.ok).length}/{results.length} com sucesso)</h3>
          <table className="alerts-table">
            <thead>
              <tr>
                <th>sAMAccountName</th>
                <th>Status</th>
                <th>Erro</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.sam}>
                  <td className="alert-name">{r.sam}</td>
                  <td>
                    <span className={r.ok ? "badge badge-status-resolved" : "badge badge-status-firing"}>
                      {r.ok ? "sucesso" : "falha"}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{r.error ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}
