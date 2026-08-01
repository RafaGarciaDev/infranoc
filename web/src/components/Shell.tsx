"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, MonitorCheck, AlertTriangle, LineChart, Ticket,
  Users, FolderTree, UsersRound, Monitor, ShieldCheck, Layers,
  Server, Archive, Terminal, MonitorCog, Network, Plug,
  ShieldAlert, Shield, Bot, BookOpen, ExternalLink, Sun, Moon, LogOut,
  type LucideIcon,
} from "lucide-react";
import { clearToken, getToken } from "@/lib/api";

type Theme = "dark" | "light";

type NavEntry = {
  href: string;
  label: string;
  icon: LucideIcon;
  requires?: string; // permissao necessaria (opcional)
  external?: boolean;
};

const NAV: { section: string; items: NavEntry[] }[] = [
  {
    section: "Operacao",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/noc", label: "NOC", icon: MonitorCheck, requires: "alerts.read" },
      { href: "/alertas", label: "Alertas", icon: AlertTriangle, requires: "alerts.read" },
      { href: "/observabilidade", label: "Observabilidade", icon: LineChart, requires: "obs.read" },
      { href: "/chamados", label: "Chamados", icon: Ticket, requires: "tickets.read" },
    ],
  },
  {
    section: "Identidade (AD)",
    items: [
      { href: "/usuarios", label: "Usuarios (AD)", icon: Users, requires: "ad.read" },
      { href: "/ad-ous", label: "Estrutura de OUs", icon: FolderTree, requires: "ad.read" },
      { href: "/ad-grupos", label: "Grupos (AD)", icon: UsersRound, requires: "ad.read" },
      { href: "/ad-computadores", label: "Computadores (AD)", icon: Monitor, requires: "ad.read" },
      { href: "/ad-gpos-sessoes", label: "GPOs e Sessoes RDP", icon: ShieldCheck, requires: "ad.read" },
      { href: "/ad-bulk", label: "Operacoes em Massa", icon: Layers, requires: "ad.write" },
    ],
  },
  {
    section: "Infraestrutura",
    items: [
      { href: "/ativos", label: "Ativos", icon: Server, requires: "cmdb.read" },
      { href: "/mapa-rede", label: "Hub de Redes", icon: Network, requires: "cmdb.read" },
      { href: "/backup", label: "Backup", icon: Archive, requires: "backup.read" },
      { href: "/linux-toolkit", label: "Linux Ops + Toolkit", icon: Terminal, requires: "linux.read" },
      { href: "/windows-ops", label: "Windows Server Ops", icon: MonitorCog, requires: "winserver.read" },
      { href: "/integracoes", label: "Integracoes", icon: Plug, requires: "integrations.manage" },
    ],
  },
  {
    section: "Seguranca",
    items: [
      { href: "/security", label: "Seguranca (SIEM)", icon: ShieldAlert, requires: "security.read" },
      { href: "/vpn", label: "VPN", icon: Shield, requires: "vpn.read" },
    ],
  },
  {
    section: "Conhecimento",
    items: [
      { href: "/ia", label: "Assistente IA", icon: Bot, requires: "ai.chat" },
      { href: "/wiki", label: "Base de Conhecimento", icon: BookOpen, requires: "wiki.read" },
    ],
  },
  {
    section: "Portal (teste)",
    items: [
      {
        href: "/portal/login",
        label: "Portal (visao do funcionario)",
        icon: ExternalLink,
        external: true,
      },
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
  const [theme, setTheme] = useState<Theme>("dark");

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
    const savedTheme = (localStorage.getItem("infranoc.theme") as Theme | null) ?? "dark";
    setTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);
    setReady(true);
  }, [router]);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("infranoc.theme", next);
  }

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

        {NAV.map((group) => {
          const visibleItems = group.items.filter((it) => !it.requires || perms.includes(it.requires));
          if (visibleItems.length === 0) return null;
          return (
            <div key={group.section}>
              <div className="nav-section">{group.section}</div>
              {visibleItems.map((it) => {
                const Icon = it.icon;
                if (it.external) {
                  return (
                    <a
                      key={it.href}
                      href={it.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="nav-item"
                      title="Abre em nova aba (evita substituir sua sessao de admin)"
                    >
                      <span className="nav-icon"><Icon size={17} strokeWidth={2} /></span>
                      <span>{it.label}</span>
                    </a>
                  );
                }
                const active = pathname === it.href || pathname.startsWith(it.href + "/");
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    className={`nav-item ${active ? "active" : ""}`}
                  >
                    <span className="nav-icon"><Icon size={17} strokeWidth={2} /></span>
                    <span>{it.label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })}
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
            <button className="logout-btn btn-ghost" onClick={toggleTheme}>
              {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
              {theme === "dark" ? "Tema claro" : "Tema escuro"}
            </button>
            <button className="logout-btn btn-ghost" onClick={logout}>
              <LogOut size={15} />
              Sair
            </button>
          </div>
        </header>

        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}