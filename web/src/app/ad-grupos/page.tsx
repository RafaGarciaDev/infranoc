"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listGroups, createGroup, renameGroup, updateGroup, deleteGroup, ADGroup, ADGroupScope, ADGroupType } from "@/lib/api";

export default function GroupsPage() {
  const [groups, setGroups] = useState<ADGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listGroups();
      data.sort((a, b) => a.name.localeCompare(b.name));
      setGroups(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function handleCreate() {
    const name = window.prompt("Nome do novo grupo:");
    if (!name) return;
    const scope = (window.prompt("Escopo (Global, DomainLocal ou Universal):", "Global") || "Global") as ADGroupScope;
    const groupType = (window.prompt("Tipo (Security ou Distribution):", "Security") || "Security") as ADGroupType;
    const description = window.prompt("Descricao (opcional):", "") || "";
    setBusy("__new__");
    setError(null);
    try {
      await createGroup({ name, scope, groupType, description });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar grupo.");
    } finally {
      setBusy(null);
    }
  }

  async function handleRename(dn: string, currentName: string) {
    const newName = window.prompt("Novo nome:", currentName);
    if (!newName || newName === currentName) return;
    setBusy(dn);
    setError(null);
    try {
      await renameGroup(dn, newName);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao renomear grupo.");
    } finally {
      setBusy(null);
    }
  }

  async function handleEditDescription(dn: string, current: string) {
    const newDesc = window.prompt("Nova descricao:", current);
    if (newDesc === null) return;
    setBusy(dn);
    setError(null);
    try {
      await updateGroup(dn, { description: newDesc });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao editar descricao.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(dn: string, name: string) {
    if (!confirm(`Excluir o grupo "${name}"?`)) return;
    setBusy(dn);
    setError(null);
    try {
      await deleteGroup(dn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir grupo.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell title="Grupos (Active Directory)">
      <div className="alerts-toolbar">
        <span className="alerts-count">
          {loading ? "carregando..." : `${groups.length} grupo(s)`}
        </span>
        <button className="logout-btn" style={{ marginLeft: "auto" }} disabled={busy === "__new__"} onClick={handleCreate}>
          + Novo grupo
        </button>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      {!loading && groups.length === 0 ? (
        <div className="empty">Nenhum grupo encontrado.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Escopo</th>
              <th>Tipo</th>
              <th>Descricao</th>
              <th>Membros</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.dn}>
                <td className="alert-name">{g.name}</td>
                <td><span className="badge badge-cat">{g.scope}</span></td>
                <td><span className="badge badge-cat">{g.group_type}</span></td>
                <td style={{ fontSize: 12, color: "var(--fg-2)" }}>{g.description || "-"}</td>
                <td>{g.member_count}</td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="logout-btn" disabled={busy === g.dn} onClick={() => handleRename(g.dn, g.name)}>
                      Renomear
                    </button>
                    <button className="logout-btn" disabled={busy === g.dn} onClick={() => handleEditDescription(g.dn, g.description)}>
                      Descricao
                    </button>
                    <button className="logout-btn" disabled={busy === g.dn} onClick={() => handleDelete(g.dn, g.name)}>
                      Excluir
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
