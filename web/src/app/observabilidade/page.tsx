"use client";

import Shell from "@/components/Shell";

const GRAFANA_URL =
  process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3001";

const IFRAME_SRC = `${GRAFANA_URL}/d/infranoc-overview/infranoc-overview?orgId=1&kiosk=tv&theme=dark&refresh=10s`;

export default function ObservabilidadePage() {
  return (
    <Shell title="Observabilidade">
      <div style={{ marginBottom: 12, color: "var(--fg-2)", fontSize: 13 }}>
        Dashboard renderizado do Grafana em modo kiosk. Refresh automatico a cada 10s. <a href={GRAFANA_URL} target="_blank" rel="noreferrer" style={{ color: "var(--accent-strong)" }}>Abrir no Grafana</a>
      </div>
      <div className="iframe-wrap">
        <iframe src={IFRAME_SRC} title="InfraNOC Overview" />
      </div>
    </Shell>
  );
}