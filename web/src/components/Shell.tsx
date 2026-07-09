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
      { href: "/alertas", label: "Alertas", requires: "alerts.read" },
      { href: "/ativos", label: "Ativos", requires: "cmdb.read" },
      { href: "/usuarios", label: "Usuarios (AD)", requires: "ad.read" },
      { href: "/observabilidade", label: "Observabilidade", requires: "obs.read" },
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
            <span className="brand-dot" />
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