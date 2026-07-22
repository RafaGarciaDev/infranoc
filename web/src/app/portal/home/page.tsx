"use client";

import Link from "next/link";
import PortalShell from "@/components/PortalShell";

export default function PortalHomePage() {
  return (
    <PortalShell title="Bem-vindo">
      <p style={{ marginBottom: 16, color: "var(--fg-2)" }}>
        Use os atalhos abaixo para abrir um chamado, consultar seus chamados
        anteriores, ou pesquisar a base de conhecimento.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Link href="/portal/chamados" className="logout-btn" style={{ textAlign: "center", padding: 16 }}>
          Abrir ou ver meus chamados
        </Link>
        <Link href="/portal/kb" className="logout-btn" style={{ textAlign: "center", padding: 16 }}>
          Base de Conhecimento
        </Link>
      </div>
    </PortalShell>
  );
}
