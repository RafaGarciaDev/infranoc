"use client";

import React, { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { listHubAssets, downloadRdpFile, HubAsset } from "@/lib/api";

export default function HubAcessosPage() {
  const [assets, setAssets] = useState<HubAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listHubAssets();
      setAssets(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRdp(a: HubAsset) {
    try {
      await downloadRdpFile(a.id, a.hostname || a.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao gerar RDP.");
    }
  }

  function handleCopySsh(a: HubAsset) {
    const cmd = `ssh admin@${a.ip_address}`;
    navigator.clipboard.writeText(cmd);
    setCopiedId(a.id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  return (
    <Shell title="Hub de Acessos Diretos">
      <div className="alerts-toolbar">
        <span className="alerts-count">
          {loading ? "carregando..." : `${assets.length} ativo(s) com acesso direto`}
        </span>
      </div>

      {error && <div className="login-error" style={{ marginBottom: 12 }}>{error}</div>}

      {!loading && assets.length === 0 ? (
        <div className="empty">Nenhum ativo com IP cadastrado ainda.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Nome</th>
              <th>IP / Hostname</th>
              <th>Tipo</th>
              <th>Site</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id}>
                <td className="alert-name">{a.name}</td>
                <td style={{ fontFamily: "monospace", fontSize: 12 }}>
                  {a.ip_address || a.hostname || "-"}
                </td>
                <td><span className="badge badge-cat">{a.type}</span></td>
                <td>{a.site}</td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    {(a.type === "Server" || a.type === "Workstation") && (
                      <button className="logout-btn" onClick={() => handleRdp(a)}>
                        Baixar RDP
                      </button>
                    )}
                    {a.ip_address && (
                      <button className="logout-btn" onClick={() => handleCopySsh(a)}>
                        {copiedId === a.id ? "Copiado!" : "Copiar SSH"}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Shell>
  );
}
