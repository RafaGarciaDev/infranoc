"use client";

import { useEffect, useState } from "react";
import { ADUser, ADAuditEvent, listAdAudit, unlockUser, setEnabled, getUserPhotoBlobUrl, uploadUserPhoto } from "@/lib/api";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

type Props = {
  user: ADUser;
  onClose: () => void;
  onChanged: () => void;
  onOpenResetPassword: () => void;
  onOpenChangeGroup: () => void;
};

export default function UserDrawer({ user, onClose, onChanged, onOpenResetPassword, onOpenChangeGroup }: Props) {
  const [audit, setAudit] = useState<ADAuditEvent[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [actionErr, setActionErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoLoading, setPhotoLoading] = useState(true);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    let currentUrl: string | null = null;
    setPhotoLoading(true);
    setPhotoError(null);
    getUserPhotoBlobUrl(user.sam)
      .then((url) => {
        currentUrl = url;
        setPhotoUrl(url);
      })
      .catch((e) => setPhotoError(e instanceof Error ? e.message : "Erro ao buscar foto."))
      .finally(() => setPhotoLoading(false));
    return () => {
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [user.sam]);

  async function handlePhotoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    setPhotoError(null);
    try {
      await uploadUserPhoto(user.sam, file);
      const url = await getUserPhotoBlobUrl(user.sam);
      setPhotoUrl(url);
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Erro ao enviar foto.");
    } finally {
      setUploadingPhoto(false);
      e.target.value = "";
    }
  }

  useEffect(() => {
    setAuditLoading(true);
    setActionErr(null);
    listAdAudit({ target_sam: user.sam, limit: 20 })
      .then(setAudit)
      .catch((e) => setActionErr((e as Error).message))
      .finally(() => setAuditLoading(false));
  }, [user.sam]);

  async function handleUnlock() {
    if (!window.confirm(`Desbloquear o usuario ${user.sam}?`)) return;
    setBusy(true);
    setActionErr(null);
    try {
      await unlockUser(user.sam);
      onChanged();
    } catch (e) {
      setActionErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }



  async function handleToggleEnabled() {
    const action = user.disabled ? "habilitar" : "desabilitar";
    if (!window.confirm(`Tem certeza que deseja ${action} o usuario ${user.sam}?`)) return;
    setBusy(true);
    setActionErr(null);
    try {
      await setEnabled(user.sam, user.disabled);
      onChanged();
    } catch (e) {
      setActionErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-header">
          <div>
            <div style={{ fontSize: 18, fontWeight: 600, color: "var(--fg-0)" }}>
              {user.display_name}
            </div>
            <div style={{ fontSize: 13, color: "var(--fg-2)", marginTop: 2 }}>
              {user.sam}
            </div>
          </div>
          <button className="drawer-close" onClick={onClose}>Fechar</button>
        </div>

        {actionErr && (
          <div style={{ color: "var(--sev-critical)", marginBottom: 12, fontSize: 13 }}>
            Erro: {actionErr}
          </div>
        )}

        <div className="drawer-section">
          <div className="drawer-section-title">Foto</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {photoLoading ? (
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(148,163,184,.15)" }} />
            ) : photoUrl ? (
              <img src={photoUrl} alt={user.display_name} style={{ width: 64, height: 64, borderRadius: "50%", objectFit: "cover" }} />
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(59,130,246,.15)", color: "#60a5fa", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 600 }}>
                {user.display_name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase()}
              </div>
            )}
            <label className="btn" style={{ cursor: "pointer" }}>
              {uploadingPhoto ? "Enviando..." : "Alterar foto"}
              <input type="file" accept="image/*" onChange={handlePhotoUpload} disabled={uploadingPhoto} style={{ display: "none" }} />
            </label>
          </div>
          {photoError && <div style={{ color: "var(--sev-critical)", fontSize: 12, marginTop: 6 }}>{photoError}</div>}
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title">Identificacao</div>
          <dl className="drawer-kv">
            <dt>email</dt><dd>{user.email || "-"}</dd>
            <dt>cargo</dt><dd>{user.title || "-"}</dd>
            <dt>departamento</dt><dd>{user.department || "-"}</dd>
            <dt>dn</dt><dd style={{ wordBreak: "break-all" }}>{user.dn}</dd>
            <dt>bloqueado</dt><dd>{user.locked ? "sim" : "nao"}</dd>
            <dt>desabilitado</dt><dd>{user.disabled ? "sim" : "nao"}</dd>
          </dl>
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title">Acoes</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="btn btn-primary" disabled={busy} onClick={onOpenResetPassword}>
              Resetar Senha
            </button>
            {user.locked && (
              <button className="btn" disabled={busy} onClick={handleUnlock}>
                Desbloquear
              </button>
            )}
            <button className="btn" disabled={busy} onClick={handleToggleEnabled}>
              {user.disabled ? "Habilitar" : "Desabilitar"}
            </button>
            <button className="btn" disabled={busy} onClick={onOpenChangeGroup}>
              Alterar Grupo
            </button>
          </div>
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title">Grupos ({user.groups.length})</div>
          {user.groups.length === 0 ? (
            <div style={{ color: "var(--fg-2)", fontSize: 13 }}>Sem grupos</div>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {user.groups.map((g) => <li key={g}>{g}</li>)}
            </ul>
          )}
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title">Auditoria</div>
          {auditLoading ? (
            <div style={{ color: "var(--fg-2)", fontSize: 13 }}>Carregando...</div>
          ) : audit.length === 0 ? (
            <div style={{ color: "var(--fg-2)", fontSize: 13 }}>Sem eventos registrados</div>
          ) : (
            audit.map((ev) => (
              <div key={ev.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span className="badge badge-cat">{ev.event_id}</span>
                  <span style={{ fontSize: 12, color: "var(--fg-2)" }}>{fmtDate(ev.at)}</span>
                </div>
                <div style={{ fontSize: 13, marginTop: 2 }}>{ev.message}</div>
                {ev.actor_sam && (
                  <div style={{ fontSize: 11, color: "var(--fg-2)", marginTop: 2 }}>
                    por: {ev.actor_sam}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}