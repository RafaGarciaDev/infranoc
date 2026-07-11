"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import {
  getIntegrationSettings,
  updateIntegrationSettings,
  testIntegrationConnection,
  IntegrationSettings,
} from "@/lib/api";

const SEVERITY_OPTIONS = ["critical", "high", "warning", "info"];

export default function IntegracoesPage() {
  const [settings, setSettings] = useState<IntegrationSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    getIntegrationSettings()
      .then(setSettings)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar."))
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof IntegrationSettings>(key: K, value: IntegrationSettings[K]) {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
    setSaved(false);
  }

  async function handleSave() {
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateIntegrationSettings({
        peppermint_enabled: settings.peppermint_enabled,
        peppermint_url: settings.peppermint_url,
        peppermint_email: settings.peppermint_email,
        peppermint_password: settings.peppermint_password || undefined,
        peppermint_default_email: settings.peppermint_default_email,
        auto_ticket_min_severity: settings.auto_ticket_min_severity,
        storm_window_seconds: settings.storm_window_seconds,
        storm_threshold: settings.storm_threshold,
      });
      setSettings(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const result = await testIntegrationConnection();
      setTestResult(result);
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : "Erro inesperado." });
    } finally {
      setTesting(false);
    }
  }

  return (
    <Shell title="Integracoes">
      {loading && <div className="empty">carregando...</div>}

      {error && (
        <div className="login-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {settings && (
        <div style={{ maxWidth: 560, display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <h2 style={{ marginBottom: 4 }}>Peppermint</h2>
            <p style={{ color: "var(--fg-2)", fontSize: 13 }}>
              Configuracao de integracao de tickets para este tenant.
            </p>
          </div>

          <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={settings.peppermint_enabled}
              onChange={(e) => update("peppermint_enabled", e.target.checked)}
            />
            <span className="field-label">Integracao ativa</span>
          </label>

          <label className="field">
            <span className="field-label">URL do Peppermint</span>
            <input
              className="field-select"
              type="text"
              placeholder="http://localhost:3110"
              value={settings.peppermint_url ?? ""}
              onChange={(e) => update("peppermint_url", e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field-label">Email da conta de servico</span>
            <input
              className="field-select"
              type="email"
              placeholder="automacao@valeverde.com"
              value={settings.peppermint_email ?? ""}
              onChange={(e) => update("peppermint_email", e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field-label">Senha</span>
            <input
              className="field-select"
              type="password"
              placeholder="deixe em branco para manter a atual"
              value={settings.peppermint_password ?? ""}
              onChange={(e) => update("peppermint_password", e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field-label">Email padrao do solicitante (fallback)</span>
            <input
              className="field-select"
              type="email"
              placeholder="noc@valeverde.com"
              value={settings.peppermint_default_email ?? ""}
              onChange={(e) => update("peppermint_default_email", e.target.value)}
            />
          </label>

          <label className="field">
            <span className="field-label">Severidade minima para abrir chamado</span>
            <select
              className="field-select"
              value={settings.auto_ticket_min_severity}
              onChange={(e) =>
                update("auto_ticket_min_severity", e.target.value as IntegrationSettings["auto_ticket_min_severity"])
              }
            >
              {SEVERITY_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field-label">Janela de storm (segundos)</span>
            <input
              className="field-select"
              type="number"
              min={1}
              value={settings.storm_window_seconds}
              onChange={(e) => update("storm_window_seconds", Number(e.target.value))}
            />
          </label>

          <label className="field">
            <span className="field-label">Threshold de storm (qtd. alertas)</span>
            <input
              className="field-select"
              type="number"
              min={1}
              value={settings.storm_threshold}
              onChange={(e) => update("storm_threshold", Number(e.target.value))}
            />
          </label>

          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: "8px 16px",
                borderRadius: 6,
                background: "var(--accent-strong, #334155)",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                opacity: saving ? 0.6 : 1,
              }}
            >
              {saving ? "Salvando..." : "Salvar"}
            </button>

            <button
              onClick={handleTest}
              disabled={testing}
              style={{
                padding: "8px 16px",
                borderRadius: 6,
                background: "transparent",
                color: "var(--fg-1)",
                border: "1px solid var(--fg-2)",
                cursor: "pointer",
                opacity: testing ? 0.6 : 1,
              }}
            >
              {testing ? "Testando..." : "Testar conexao"}
            </button>

            {saved && <span style={{ color: "#22c55e", fontSize: 13 }}>Salvo.</span>}
          </div>

          {testResult && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 6,
                fontSize: 13,
                background: testResult.ok ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                border: `1px solid ${
                  testResult.ok ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)"
                }`,
              }}
            >
              {testResult.message}
            </div>
          )}
        </div>
      )}
    </Shell>
  );
}