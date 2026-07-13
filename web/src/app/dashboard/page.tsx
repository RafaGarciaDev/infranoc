"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";

export default function DashboardPage() {
  const [name, setName] = useState<string>("");
  const [perms, setPerms] = useState<string[]>([]);

  useEffect(() => {
    setName(sessionStorage.getItem("infranoc.display_name") ?? "Usuario");
    try {
      setPerms(JSON.parse(sessionStorage.getItem("infranoc.permissions") ?? "[]"));
    } catch {
      setPerms([]);
    }
  }, []);

  return (
    <Shell title="Dashboard">
      <section className="panel">
        <img src="/Valeverde_logo.png" alt="Vale Verde" className="dash-logo" />
        <div className="panel-eyebrow">SESSAO AUTENTICADA</div>
        <h1 className="panel-title">Bem-vindo, {name}</h1>
        <p className="panel-text">
          Voce esta autenticado no InfraNOC via token JWT. Este e o painel base -
          use o menu lateral para navegar pelos modulos operacionais.
        </p>
      </section>

      <section className="panel">
        <div className="panel-eyebrow">SUAS PERMISSOES - {perms.length}</div>
        <div className="perm-grid">
          {perms.map((p) => (
            <span key={p} className="perm-chip">
              {p}
            </span>
          ))}
        </div>
      </section>
    </Shell>
  );
}