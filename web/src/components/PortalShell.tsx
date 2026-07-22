"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken } from "@/lib/api";

export default function PortalShell({ title, children }: { title: string; children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
    setDisplayName(sessionStorage.getItem("infranoc.portal_display_name"));
  }, []);

  function logout() {
    clearToken();
    sessionStorage.removeItem("infranoc.portal_display_name");
    router.replace("/portal/login");
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--fg)" }}>
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 16px", borderBottom: "1px solid var(--border)",
      }}>
        <strong>Portal InfraNOC</strong>
        <div style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 13 }}>
          {displayName && <span>{displayName}</span>}
          <button className="logout-btn" onClick={logout}>Sair</button>
        </div>
      </header>
      <nav style={{ display: "flex", gap: 8, padding: "8px 16px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
        <Link href="/portal/home" className={pathname === "/portal/home" ? "nav-item active" : "nav-item"}>Inicio</Link>
        <Link href="/portal/chamados" className={pathname === "/portal/chamados" ? "nav-item active" : "nav-item"}>Meus Chamados</Link>
        <Link href="/portal/kb" className={pathname?.startsWith("/portal/kb") ? "nav-item active" : "nav-item"}>Base de Conhecimento</Link>
      </nav>
      <main style={{ padding: 16, maxWidth: 720, margin: "0 auto" }}>
        <h1 style={{ fontSize: 20, marginBottom: 16 }}>{title}</h1>
        {children}
      </main>
    </div>
  );
}
