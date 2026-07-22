"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/api";

type NavEntry = {
  href: string;
  label: string;
  requires?: string; // permissao necessaria (opcional)
};

const NAV: { section: string; items: NavEntry[] }[] = [
  {
    section: "Operacao",
    items: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/noc", label: "NOC", requires: "alerts.read" },
      { href: "/alertas", label: "Alertas", requires: "alerts.read" },
      { href: "/ativos", label: "Ativos", requires: "cmdb.read" },
      { href: "/chamados", label: "Chamados", requires: "tickets.read" },
      { href: "/integracoes", label: "Integracoes", requires: "integrations.manage" },
      { href: "/usuarios", label: "Usuarios (AD)", requires: "ad.read" },
      { href: "/ad-ous", label: "Estrutura de OUs", requires: "ad.read" },
      { href: "/ad-grupos", label: "Grupos (AD)", requires: "ad.read" },
      { href: "/ad-computadores", label: "Computadores (AD)", requires: "ad.read" },
      { href: "/ad-gpos-sessoes", label: "GPOs e Sessoes RDP", requires: "ad.read" },
      { href: "/ad-bulk", label: "Operacoes em Massa", requires: "ad.write" },
      { href: "/observabilidade", label: "Observabilidade", requires: "obs.read" },
      { href: "/ia", label: "Assistente IA", requires: "ai.chat" },
      { href: "/wiki", label: "Base de Conhecimento", requires: "wiki.read" },
      { href: "/hub-acessos", label: "Hub de Acessos", requires: "cmdb.read" },
      { href: "/linux-toolkit", label: "Linux Ops + Toolkit", requires: "linux.read" },
      { href: "/backup", label: "Backup", requires: "backup.read" },
      { href: "/security", label: "Seguranca (SIEM)", requires: "security.read" },
    ],
  },
];

export default function Shell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [name, setName] = useState<string>("");
  const [perms, setPerms] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setName(sessionStorage.getItem("infranoc.display_name") ?? "Usuario");
    try {
      setPerms(JSON.parse(sessionStorage.getItem("infranoc.permissions") ?? "[]"));
    } catch {
      setPerms([]);
    }
    setReady(true);
  }, [router]);

  function logout() {
    clearToken();
    sessionStorage.removeItem("infranoc.display_name");
    sessionStorage.removeItem("infranoc.permissions");
    router.replace("/login");
  }

  if (!ready) return null;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand">
            <img src="/Infranoc_logo.png" alt="InfraNOC" className="brand-logo" />
            <span className="brand-name">InfraNOC</span>
            <span className="brand-sub">Vale Verde S/A</span>
          </div>
        </div>

        {NAV.map((group) => (
          <div key={group.section}>
            <div className="nav-section">{group.section}</div>
            {group.items
              .filter((it) => !it.requires || perms.includes(it.requires))
              .map((it) => {
                const active = pathname === it.href || pathname.startsWith(it.href + "/");
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    className={`nav-item ${active ? "active" : ""}`}
                  >
                    <span className="nav-icon" />
                    <span>{it.label}</span>
                  </Link>
                );
              })}
          </div>
        ))}
        <div className="nav-section">Testes</div>
        
          <a
          href="/portal/login"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-item"
          title="Abre em nova aba (evita substituir sua sessao de admin)"
        >
          <span className="nav-icon" />
          <span>Portal (visao do funcionario)</span>
        </a>
      </aside>

      <div className="content">
        <header className="topbar">
          <div className="topbar-title">{title}</div>
          <div className="topbar-right">
            <span>
              <span className="status-dot" />
              online
            </span>
            <span className="app-username">{name}</span>
            <button className="logout-btn" onClick={logout}>
              Sair
            </button>
          </div>
        </header>

        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}