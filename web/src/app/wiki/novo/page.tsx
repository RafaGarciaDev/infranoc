"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Shell from "@/components/Shell";
import { createWikiPage, WikiCategory } from "@/lib/api";

const CATEGORIAS: WikiCategory[] = ["rede", "ad", "linux", "ot", "energia", "seguranca", "geral"];

function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default function WikiNewPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [category, setCategory] = useState<WikiCategory>("geral");
  const [contentMd, setContentMd] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleTitleChange(v: string) {
    setTitle(v);
    if (!slugTouched) setSlug(slugify(v));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const tags = tagsInput.split(",").map((t) => t.trim()).filter(Boolean);
      const created = await createWikiPage({ slug, title, category, content_md: contentMd, tags });
      router.push(`/wiki/${encodeURIComponent(created.slug)}`);
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao criar pagina.");
      setSaving(false);
    }
  }

  return (
    <Shell title="Nova pagina">
      <div className="alerts-toolbar">
        <Link href="/wiki" style={{ color: "var(--accent-strong)" }}>&larr; Voltar</Link>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 800 }}>
        <label className="field">
          <span className="field-label">Titulo</span>
          <input
            className="field-select"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            required
          />
        </label>
        <label className="field">
          <span className="field-label">Slug (identificador na URL)</span>
          <input
            className="field-select"
            value={slug}
            onChange={(e) => { setSlug(e.target.value); setSlugTouched(true); }}
            required
          />
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
            required
          />
        </label>
        <div>
          <button type="submit" className="logout-btn" disabled={saving}>
            {saving ? "Criando..." : "Criar pagina"}
          </button>
        </div>
      </form>
    </Shell>
  );
}
