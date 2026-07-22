"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import PortalShell from "@/components/PortalShell";
import { getWikiPage, WikiPageDetail } from "@/lib/api";

export default function PortalKbDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = decodeURIComponent(params.slug);
  const [page, setPage] = useState<WikiPageDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWikiPage(slug)
      .then(setPage)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar."))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <PortalShell title={page?.title || "Artigo"}>
      <Link href="/portal/kb" style={{ color: "var(--accent-strong)", display: "inline-block", marginBottom: 12 }}>
        &larr; Voltar
      </Link>
      {error && <div className="login-error">{error}</div>}
      {loading ? (
        <div className="empty">carregando...</div>
      ) : page ? (
        <pre style={{
          whiteSpace: "pre-wrap", wordBreak: "break-word", background: "var(--panel)",
          padding: 16, borderRadius: 8, border: "1px solid var(--border)",
        }}>
          {page.content_md}
        </pre>
      ) : null}
    </PortalShell>
  );
}
