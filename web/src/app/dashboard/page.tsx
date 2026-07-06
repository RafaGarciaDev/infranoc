"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [name, setName] = useState<string>("");
  const [perms, setPerms] = useState<string[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // proteção de rota: sem token, volta pro login
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setName(sessionStorage.getItem("infranoc.display_name") ?? "Usuário");
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
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-dot" />
          <span className="brand-name">InfraNOC</span>
        </div>
        <div className="app-user">
          <span className="app-status">
            <span className="status-dot" /> online
          </span>
          <span className="app-username">{name}</span>
          <button className="logout-btn" onClick={logout}>
            Sair
          </button>
        </div>
      </header>

      <main className="app-main">
        <section className="panel">
          <div className="panel-eyebrow">SESSÃO AUTENTICADA</div>
          <h1 className="panel-title">Bem-vindo, {name}</h1>
          <p className="panel-text">
            Você está autenticado no InfraNOC via token JWT. Este é o painel base —
            os módulos de observabilidade, CMDB, diretório e o mapa da planta entram
            nas próximas etapas.
          </p>
        </section>

        <section className="panel">
          <div className="panel-eyebrow">SUAS PERMISSÕES · {perms.length}</div>
          <div className="perm-grid">
            {perms.map((p) => (
              <span key={p} className="perm-chip">
                {p}
              </span>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
