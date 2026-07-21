"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Shell from "@/components/Shell";
import {
  getWikiPage,
  updateWikiPage,
  deleteWikiPage,
  getWikiHistory,
  WikiPageDetail,
  WikiPageVersionOut,
  WikiCategory,
} from "@/lib/api";

const CATEGORIAS: WikiCategory[] = ["rede", "ad", "linux", "ot", "energia", "seguranca", "geral"];

function fmtDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function WikiDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = decodeURIComponent(params.slug);

  const [page, setPage] = useState<WikiPageDetail | null>(null);
  const [history, setHistory] = useState<WikiPageVersionOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [saving, setSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<WikiCategory>("geral");
  const [contentMd, setContentMd] = useState("");
  const [tagsInput, setTagsInput] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await getWikiPage(slug);
      setPage(data);
      setTitle(data.title);
      setCategory(data.category);
      setContentMd(data.content_md);
      setTagsInput((data.tags || []).join(", "));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const tags = tagsInput.split(",").map((t) => t.trim()).filter(Boolean);
      const updated = await updateWikiPage(slug, { title, category, content_md: contentMd, tags });
      setPage(updated);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Excluir a pagina "${page?.title}"? Essa acao nao pode ser desfeita.`)) return;
    try {
      await deleteWikiPage(slug);
      router.push("/wiki");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao excluir.");
    }
  }

  async function loadHistory() {
    if (showHistory) {
      setShowHistory(false);
      return;
    }
    try {
      const data = await getWikiHistory(slug);
      setHistory(data);
      setShowHistory(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao buscar historico.");
    }
  }

  if (loading) return <Shell title="Base de Conhecimento"><div className="empty">Carregando...</div></Shell>;
  if (!page) return <Shell title="Base de Conhecimento"><div className="empty">Pagina nao encontrada.</div></Shell>;

  return (
    <Shell title={page.title}>
      <div className="alerts-toolbar">
        <Link href="/wiki" style={{ color: "var(--accent-strong)" }}>&larr; Voltar</Link>
        <span className="alerts-count">
          {page.category} - v{page.version} - atualizado em {fmtDateTime(page.updated_at)}
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button className="logout-btn" onClick={loadHistory}>
            {showHistory ? "Ocultar historico" : "Historico"}
          </button>
          {!editing && (
            <button className="logout-btn" onClick={() => setEditing(true)}>Editar</button>
          )}
          {!editing && (
            <button className="logout-btn" onClick={handleDelete}>Excluir</button>
          )}
        </div>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      {showHistory && (
        <div style={{ marginBottom: 16, border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
          <strong>Historico de versoes</strong>
          <ul>
            {history.map((h) => (
              <li key={h.version}>
                v{h.version} - {h.author_email ?? "desconhecido"} - {fmtDateTime(h.created_at)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {editing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 800 }}>
          <label className="field">
            <span className="field-label">Titulo</span>
            <input className="field-select" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Categoria</span>
            <select className="field-select" value={category} onChange={(e) => setCategory(e.target.value as WikiCategory)}>
              {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Tags (separadas por virgula)</span>
            <input className="field-select" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">Conteudo (Markdown)</span>
            <textarea
              className="field-select"
              rows={16}
              value={contentMd}
              onChange={(e) => setContentMd(e.target.value)}
              style={{ fontFamily: "monospace", resize: "vertical" }}
            />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="logout-btn" onClick={handleSave} disabled={saving}>
              {saving ? "Salvando..." : "Salvar"}
            </button>
            <button className="logout-btn" onClick={() => setEditing(false)}>Cancelar</button>
          </div>
        </div>
      ) : (
        <pre style={{
          whiteSpace: "pre-wrap", wordBreak: "break-word", maxWidth: 900,
          background: "var(--panel)", padding: 16, borderRadius: 8, border: "1px solid var(--border)",
        }}>
          {page.content_md}
        </pre>
      )}
    </Shell>
  );
}
