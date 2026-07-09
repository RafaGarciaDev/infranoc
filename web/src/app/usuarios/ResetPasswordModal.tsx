"use client";

import { useState } from "react";
import { resetPassword } from "@/lib/api";

type Props = {
  sam: string;
  onClose: () => void;
  onSuccess: () => void;
};

export default function ResetPasswordModal({ sam, onClose, onSuccess }: Props) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mustChange, setMustChange] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const validationErr =
    password.length === 0 || confirm.length === 0
      ? null
      : password.length < 8
      ? "A senha deve ter no minimo 8 caracteres."
      : password !== confirm
      ? "As senhas nao coincidem."
      : null;

  const canSubmit = password.length >= 8 && password === confirm && !busy;

  async function handleSubmit() {
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      await resetPassword(sam, password, mustChange);
      onSuccess();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer" style={{ maxWidth: 420 }}>
        <div className="drawer-header">
          <div style={{ fontSize: 16, fontWeight: 600 }}>Resetar senha — {sam}</div>
          <button className="drawer-close" onClick={onClose}>Fechar</button>
        </div>

        <div className="drawer-section">
          <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Nova senha</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", marginBottom: 12 }}
            autoFocus
          />

          <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>Confirmar senha</label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            style={{ width: "100%", marginBottom: 12 }}
          />

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, marginBottom: 12 }}>
            <input
              type="checkbox"
              checked={mustChange}
              onChange={(e) => setMustChange(e.target.checked)}
            />
            Forcar troca no proximo login
          </label>

          {validationErr && (
            <div style={{ color: "var(--sev-critical)", fontSize: 13, marginBottom: 12 }}>
              {validationErr}
            </div>
          )}
          {err && (
            <div style={{ color: "var(--sev-critical)", fontSize: 13, marginBottom: 12 }}>
              Erro: {err}
            </div>
          )}

          <button
            className="btn btn-primary"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {busy ? "Aplicando..." : "Resetar senha"}
          </button>
        </div>
      </div>
    </>
  );
}