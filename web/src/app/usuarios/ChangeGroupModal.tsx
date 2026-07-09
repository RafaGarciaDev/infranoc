"use client";

import { useState } from "react";
import { changeGroup } from "@/lib/api";

type Props = {
  sam: string;
  onClose: () => void;
  onSuccess: () => void;
};

export default function ChangeGroupModal({ sam, onClose, onSuccess }: Props) {
  const [groupDn, setGroupDn] = useState("");
  const [add, setAdd] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canSubmit = groupDn.trim().length > 0 && !busy;

  async function handleSubmit() {
    if (!canSubmit) return;
    setBusy(true);
    setErr(null);
    try {
      await changeGroup(sam, groupDn.trim(), add);
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
          <div style={{ fontSize: 16, fontWeight: 600 }}>Alterar grupo — {sam}</div>
          <button className="drawer-close" onClick={onClose}>Fechar</button>
        </div>

        <div className="drawer-section">
          <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>DN do grupo</label>
          <input
            type="text"
            placeholder="CN=Grupo,OU=Groups,DC=exemplo,DC=com"
            value={groupDn}
            onChange={(e) => setGroupDn(e.target.value)}
            style={{ width: "100%", marginBottom: 12 }}
            autoFocus
          />

          <div style={{ display: "flex", gap: 16, marginBottom: 12, fontSize: 13 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input type="radio" checked={add} onChange={() => setAdd(true)} />
              Adicionar
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input type="radio" checked={!add} onChange={() => setAdd(false)} />
              Remover
            </label>
          </div>

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
            {busy ? "Aplicando..." : add ? "Adicionar ao grupo" : "Remover do grupo"}
          </button>
        </div>
      </div>
    </>
  );
}