"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { ADUser, ADSummary, listAdUsers, getAdSummary } from "@/lib/api";
import UserDrawer from "./UserDrawer";
import ResetPasswordModal from "./ResetPasswordModal";
import ChangeGroupModal from "./ChangeGroupModal";

function initials(name: string) {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

function statusChip(u: ADUser) {
  if (u.locked) {
    return <span className="badge badge-status-firing">bloqueado</span>;
  }
  if (u.disabled) {
    return <span className="badge badge-cat">desabilitado</span>;
  }
  return <span className="badge badge-status-resolved">ativo</span>;
}

function UsuariosInner() {
  const [users, setUsers] = useState<ADUser[]>([]);
  const [summary, setSummary] = useState<ADSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [onlyLocked, setOnlyLocked] = useState(false);

  const [selectedSam, setSelectedSam] = useState<string | null>(null);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);

  const selectedUser = users.find((u) => u.sam === selectedSam) ?? null;

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 400);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    getAdSummary()
      .then(setSummary)
      .catch((e) => setErr((e as Error).message));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const items = await listAdUsers(debouncedSearch || undefined);
      setUsers(onlyLocked ? items.filter((u) => u.locked) : items);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, onlyLocked]);

  useEffect(() => { load(); }, [load]);

  return (
    <Shell title="Usuarios (AD)">
      {summary && (
        <div className="stat-row" style={{ marginBottom: 16 }}>
          <div className="stat-card">
            <div className="stat-label">Total</div>
            <div className="stat-value">{summary.total}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Bloqueados</div>
            <div className="stat-value critical">{summary.locked}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Desabilitados</div>
            <div className="stat-value">{summary.disabled}</div>
          </div>
        </div>
      )}

      <div className="cmdb-filters">
        <input
          placeholder="Buscar por nome, sam, email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input
            type="checkbox"
            checked={onlyLocked}
            onChange={(e) => setOnlyLocked(e.target.checked)}
          />
          Somente bloqueados
        </label>
      </div>

      {err && (
        <div className="error-panel">
          <div className="error-panel-title">Nao foi possivel carregar os usuarios do AD</div>
          <div className="text-sm text-muted">{err}</div>
          <div className="text-xs text-muted" style={{ marginTop: 6 }}>Verifique se o controlador de dominio esta acessivel e tente novamente.</div>
        </div>
      )}

      {loading ? (
        <table className="cmdb-table">
          <thead>
            <tr><th>Nome</th><th>SAM</th><th>Departamento</th><th>Cargo</th><th>Status</th></tr>
          </thead>
          <tbody>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <tr key={i}>
                {[0, 1, 2, 3, 4].map((j) => (
                  <td key={j}>
                    <div style={{ height: 12, borderRadius: 6, background: "rgba(148,163,184,.15)", width: j === 0 ? "70%" : "55%", animation: "pulse 1.5s ease-in-out infinite" }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <table className="cmdb-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>SAM</th>
              <th>Departamento</th>
              <th>Cargo</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && !err && (
              <tr>
                <td colSpan={5} className="empty">
                  Nenhum usuario encontrado{debouncedSearch ? ` para "${debouncedSearch}"` : ""}.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.sam} onClick={() => setSelectedSam(u.sam)}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", background: "rgba(59,130,246,.15)", color: "#60a5fa", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 600, flexShrink: 0 }}>
                      {initials(u.display_name)}
                    </div>
                    <div>
                      <div className="cell-name">{u.display_name}</div>
                      <div className="cell-sub">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td>{u.sam}</td>
                <td>{u.department}</td>
                <td>{u.title}</td>
                <td>{statusChip(u)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedUser && (
        <UserDrawer
          user={selectedUser}
          onClose={() => setSelectedSam(null)}
          onChanged={() => { load(); setSelectedSam(null); }}
          onOpenResetPassword={() => setShowResetModal(true)}
          onOpenChangeGroup={() => setShowGroupModal(true)}
        />
      )}

      {showResetModal && selectedUser && (
        <ResetPasswordModal
          sam={selectedUser.sam}
          onClose={() => setShowResetModal(false)}
          onSuccess={() => { setShowResetModal(false); load(); setSelectedSam(null); }}
        />
      )}

      {showGroupModal && selectedUser && (
        <ChangeGroupModal
          sam={selectedUser.sam}
          onClose={() => setShowGroupModal(false)}
          onSuccess={() => { setShowGroupModal(false); load(); setSelectedSam(null); }}
        />
      )}
    </Shell>
  );
}

export default function UsuariosPage() {
  return (
    <Suspense fallback={null}>
      <UsuariosInner />
    </Suspense>
  );
}