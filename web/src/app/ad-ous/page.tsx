"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listOUs, createOU, renameOU, moveOU, deleteOU, OU } from "@/lib/api";

type TreeNode = OU & { children: TreeNode[]; depth: number };

function buildTree(ous: OU[]): TreeNode[] {
  const byDn = new Map<string, TreeNode>();
  ous.forEach((o) => byDn.set(o.dn, { ...o, children: [], depth: 0 }));

  const roots: TreeNode[] = [];
  byDn.forEach((node) => {
    const parent = byDn.get(node.parent_dn);
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });

  function setDepth(node: TreeNode, depth: number) {
    node.depth = depth;
    node.children.sort((a, b) => a.name.localeCompare(b.name));
    node.children.forEach((c) => setDepth(c, depth + 1));
  }
  roots.sort((a, b) => a.name.localeCompare(b.name));
  roots.forEach((r) => setDepth(r, 0));
  return roots;
}

function flatten(nodes: TreeNode[]): TreeNode[] {
  const out: TreeNode[] = [];
  function visit(n: TreeNode) {
    out.push(n);
    n.children.forEach(visit);
  }
  nodes.forEach(visit);
  return out;
}

export default function OUsPage() {
  const [ous, setOus] = useState<OU[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listOUs();
      setOus(data);
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

  async function handleCreate(parentDn: string) {
    const name = window.prompt("Nome da nova OU:");
    if (!name) return;
    setBusy(parentDn);
    setError(null);
    try {
      await createOU(name, parentDn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar OU.");
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
      await renameOU(dn, newName);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao renomear OU.");
    } finally {
      setBusy(null);
    }
  }

  async function handleMove(dn: string) {
    const newParentDn = window.prompt("DN completo do novo pai:");
    if (!newParentDn) return;
    setBusy(dn);
    setError(null);
    try {
      await moveOU(dn, newParentDn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao mover OU.");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(dn: string, name: string) {
    if (!confirm(`Excluir a OU "${name}"? A OU precisa estar vazia.`)) return;
    setBusy(dn);
    setError(null);
    try {
      await deleteOU(dn);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir OU.");
    } finally {
      setBusy(null);
    }
  }

  const tree = buildTree(ous);
  const rows = flatten(tree);

  return (
    <Shell title="Estrutura de OUs (Active Directory)">
      <div className="alerts-toolbar">
        <span className="alerts-count">
          {loading ? "carregando..." : `${ous.length} OU(s)`}
        </span>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      {!loading && rows.length === 0 ? (
        <div className="empty">Nenhuma OU encontrada.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>DN</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((n) => (
              <tr key={n.dn}>
                <td className="alert-name">
                  <span style={{ paddingLeft: n.depth * 20 }}>
                    {n.depth > 0 ? "└ " : ""}
                    {n.name}
                  </span>
                </td>
                <td style={{ fontSize: 11, color: "var(--fg-2)" }}>{n.dn}</td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button className="logout-btn" disabled={busy === n.dn} onClick={() => handleCreate(n.dn)}>
                      + Sub-OU
                    </button>
                    <button className="logout-btn" disabled={busy === n.dn} onClick={() => handleRename(n.dn, n.name)}>
                      Renomear
                    </button>
                    <button className="logout-btn" disabled={busy === n.dn} onClick={() => handleMove(n.dn)}>
                      Mover
                    </button>
                    <button className="logout-btn" disabled={busy === n.dn} onClick={() => handleDelete(n.dn, n.name)}>
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
