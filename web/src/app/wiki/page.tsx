"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import { listWikiPages, WikiPageListItem, WikiCategory } from "@/lib/api";

const CATEGORIAS: { value: WikiCategory | ""; label: string }[] = [
  { value: "", label: "todas" },
  { value: "rede", label: "Rede" },
  { value: "ad", label: "Active Directory" },
  { value: "linux", label: "Linux" },
  { value: "ot", label: "OT" },
  { value: "energia", label: "Energia" },
  { value: "seguranca", label: "Seguranca" },
  { value: "geral", label: "Geral" },
];

function categoriaBadge(cat: string) {
  return <span className="badge badge-cat">{cat}</span>;
}

function fmtDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function WikiListPage() {
  const [pages, setPages] = useState<WikiPageListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<WikiCategory | "">("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listWikiPages({ category: category || undefined });
      setPages(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  return (
    <Shell title="Base de Conhecimento">
      <div className="alerts-toolbar">
        <label className="field">
          <span className="field-label">Categoria</span>
          <select
            className="field-select"
            value={category}
            onChange={(e) => setCategory(e.target.value as WikiCategory | "")}
          >
            {CATEGORIAS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </label>

        <span className="alerts-count">
          {loading ? "carregando..." : `${pages.length} pagina(s)`}
        </span>

        <Link href="/wiki/novo" className="logout-btn" style={{ marginLeft: "auto" }}>
          + Nova pagina
        </Link>
      </div>

      {error && (
        <div className="login-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!loading && pages.length === 0 ? (
        <div className="empty">Nenhuma pagina cadastrada ainda.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Titulo</th>
              <th>Categoria</th>
              <th>Tags</th>
              <th>Versao</th>
              <th>Atualizado em</th>
            </tr>
          </thead>
          <tbody>
            {pages.map((p) => (
              <tr key={p.slug}>
                <td className="alert-name">
                  <Link href={`/wiki/${encodeURIComponent(p.slug)}`} style={{ color: "var(--accent-strong)" }}>
                    {p.title}
                  </Link>
                </td>
                <td>{categoriaBadge(p.category)}</td>
                <td>{(p.tags || []).join(", ") || "-"}</td>
                <td>v{p.version}</td>
                <td className="alert-time">{fmtDateTime(p.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
