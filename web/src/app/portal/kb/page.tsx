"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import PortalShell from "@/components/PortalShell";
import { listWikiPages, WikiPageListItem } from "@/lib/api";

export default function PortalKbPage() {
  const [pages, setPages] = useState<WikiPageListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listWikiPages()
      .then(setPages)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PortalShell title="Base de Conhecimento">
      {error && <div className="login-error">{error}</div>}
      {loading ? (
        <div className="empty">carregando...</div>
      ) : pages.length === 0 ? (
        <div className="empty">Nenhum artigo disponivel.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {pages.map((p) => (
            <Link
              key={p.slug}
              href={`/portal/kb/${encodeURIComponent(p.slug)}`}
              style={{
                background: "var(--panel)", padding: 12, borderRadius: 8, border: "1px solid var(--border)",
                color: "var(--accent-strong)",
              }}
            >
              <strong>{p.title}</strong>
              <div style={{ fontSize: 12, color: "var(--fg-2)" }}>{p.category}</div>
            </Link>
          ))}
        </div>
      )}
    </PortalShell>
  );
}
