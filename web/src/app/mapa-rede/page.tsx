"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Shell from "@/components/Shell";
import Tooltip from "@/components/Tooltip";
import {
  getNetworkGraph, createNetworkLink, deleteNetworkLink,
  downloadRdpFile, toolkitPortCheck,
  NetworkNode, NetworkLinkItem, PortCheckResult,
} from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

const REMOTE_ACCESS_TYPES = new Set(["Server", "Workstation"]);

function defaultPortFor(type: string): string {
  if (type === "Server" || type === "Workstation") return "3389";
  return "161"; // maioria dos ativos de rede/OT (switch, router, AP, impressora, UPS) fala SNMP
}

export default function MapaRedePage() {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [links, setLinks] = useState<NetworkLinkItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NetworkNode | null>(null);
  const [linkA, setLinkA] = useState("");
  const [linkB, setLinkB] = useState("");
  const [linkType, setLinkType] = useState("Ethernet");
  const [busy, setBusy] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 900, height: 600 });

  const [pcPort, setPcPort] = useState("");
  const [pcResult, setPcResult] = useState<PortCheckResult | null>(null);
  const [pcBusy, setPcBusy] = useState(false);
  const [rdpBusy, setRdpBusy] = useState(false);
  const [sshCopied, setSshCopied] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const g = await getNetworkGraph();
      setNodes(g.nodes);
      setLinks(g.links);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    function resize() {
      if (containerRef.current) {
        setDims({
          width: containerRef.current.clientWidth,
          height: Math.max(500, window.innerHeight - 260),
        });
      }
    }
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);

  const layerColor = useMemo(() => ({
    TI: cssVar("--layer-ti", "#5eb1ff"),
    OT: cssVar("--layer-ot", "#ffb020"),
    Physical: cssVar("--layer-physical", "#45c785"),
  }), []);

  const graphData = useMemo(() => ({
    nodes: nodes.map((n) => ({ ...n })),
    links: links.map((l) => ({ ...l, source: l.asset_a_id, target: l.asset_b_id })),
  }), [nodes, links]);

  async function handleCreateLink(e: React.FormEvent) {
    e.preventDefault();
    if (!linkA || !linkB || linkA === linkB) return;
    setBusy(true);
    setError(null);
    try {
      await createNetworkLink(linkA, linkB, linkType);
      setLinkA("");
      setLinkB("");
      await load();
    } catch (e2) {
      setError(e2 instanceof Error ? e2.message : "Erro ao criar link.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteLink(linkId: string) {
    if (!confirm("Remover esta conexao?")) return;
    setBusy(true);
    setError(null);
    try {
      await deleteNetworkLink(linkId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao remover link.");
    } finally {
      setBusy(false);
    }
  }

  function selectNode(n: NetworkNode) {
    setSelected(n);
    setPcPort(defaultPortFor(n.type));
    setPcResult(null);
    setSshCopied(false);
  }

  async function handlePortCheck() {
    if (!selected?.ip_address) return;
    setPcBusy(true);
    setPcResult(null);
    setError(null);
    try {
      const r = await toolkitPortCheck(selected.ip_address, parseInt(pcPort, 10));
      setPcResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro no teste de conectividade.");
    } finally {
      setPcBusy(false);
    }
  }

  async function handleDownloadRdp() {
    if (!selected) return;
    setRdpBusy(true);
    setError(null);
    try {
      await downloadRdpFile(selected.id, selected.name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao baixar RDP.");
    } finally {
      setRdpBusy(false);
    }
  }

  function handleCopySsh() {
    if (!selected?.ip_address) return;
    navigator.clipboard.writeText(`ssh admin@${selected.ip_address}`);
    setSshCopied(true);
    setTimeout(() => setSshCopied(false), 2000);
  }

  const sortedNodes = useMemo(
    () => [...nodes].sort((a, b) => a.name.localeCompare(b.name)),
    [nodes]
  );

  return (
    <Shell title="Mapa de Rede">
      {error && <div className="login-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="alerts-toolbar">
        <span className="alerts-count">
          {loading ? "carregando..." : `${nodes.length} ativo(s), ${links.length} conexao(oes)`}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 12, fontSize: 12, color: "var(--fg-2)" }}>
          <span><span style={{ color: layerColor.TI }}>●</span> TI</span>
          <span><span style={{ color: layerColor.OT }}>●</span> OT</span>
          <span><span style={{ color: layerColor.Physical }}>●</span> Fisico</span>
        </span>
      </div>

      <div ref={containerRef} className="panel" style={{ padding: 0, overflow: "hidden", marginBottom: 16 }}>
        {!loading && (
          <ForceGraph2D
            graphData={graphData}
            width={dims.width}
            height={dims.height}
            nodeId="id"
            nodeLabel={(n: any) => `${n.name} (${n.type}) - ${n.site}`}
            nodeColor={(n: any) => layerColor[n.layer as keyof typeof layerColor] || "#8a8d96"}
            nodeRelSize={4}
            linkColor={() => cssVar("--border-strong", "#454a54")}
            linkWidth={1}
            backgroundColor="transparent"
            onNodeClick={(n: any) => selectNode(n)}
            onLinkClick={(l: any) => handleDeleteLink(l.id)}
            cooldownTicks={100}
          />
        )}
      </div>

      {selected && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-eyebrow">Ativo selecionado</div>
          <div className="panel-title" style={{ fontSize: 16 }}>{selected.name}</div>
          <div className="drawer-kv">
            <dt>Tipo</dt><dd>{selected.type}</dd>
            <dt>Camada</dt><dd>{selected.layer}</dd>
            <dt>Site</dt><dd>{selected.site}</dd>
            <dt>Status</dt><dd>{selected.status}</dd>
            <dt>Criticidade</dt><dd>{selected.criticality}</dd>
            <dt>IP</dt><dd>{selected.ip_address || "-"}</dd>
          </div>

          <div style={{ marginTop: 16, display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div>
              <div className="panel-eyebrow" style={{ marginBottom: 6 }}>Testar conectividade</div>
              {!selected.ip_address ? (
                <p style={{ fontSize: 12, color: "var(--fg-2)" }}>Ativo sem IP cadastrado.</p>
              ) : (
                <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                  <label className="field" style={{ minWidth: 140 }}>
                    <span className="field-label">Host</span>
                    <input className="field-select" value={selected.ip_address} readOnly />
                  </label>
                  <label className="field">
                    <span className="field-label">Porta</span>
                    <input className="field-select" value={pcPort} onChange={(e) => setPcPort(e.target.value)} style={{ width: 70 }} />
                  </label>
                  <Tooltip label="Testa se a porta esta acessivel a partir do backend (TCP connect)">
                    <button className="logout-btn" disabled={pcBusy} onClick={handlePortCheck}>
                      {pcBusy ? "Testando..." : "Testar"}
                    </button>
                  </Tooltip>
                  {pcResult && (
                    <span className={pcResult.reachable ? "badge badge-status-resolved" : "badge badge-status-firing"}>
                      {pcResult.reachable ? `Acessivel (${pcResult.latency_ms}ms)` : "Inacessivel"}
                    </span>
                  )}
                </div>
              )}
            </div>

            {REMOTE_ACCESS_TYPES.has(selected.type) && (
              <div>
                <div className="panel-eyebrow" style={{ marginBottom: 6 }}>Acesso rapido</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <Tooltip label="Baixa um arquivo .rdp pronto pra abrir no cliente de Area de Trabalho Remota">
                    <button className="logout-btn" disabled={rdpBusy} onClick={handleDownloadRdp}>
                      {rdpBusy ? "Baixando..." : "Baixar RDP"}
                    </button>
                  </Tooltip>
                  {selected.ip_address && (
                    <Tooltip label="Copia o comando ssh pra colar no seu terminal">
                      <button className="logout-btn" onClick={handleCopySsh}>
                        {sshCopied ? "Copiado!" : "Copiar SSH"}
                      </button>
                    </Tooltip>
                  )}
                </div>
              </div>
            )}

            <div>
              <div className="panel-eyebrow" style={{ marginBottom: 6 }}>Comandos</div>
              <Link href={`/dispositivos?asset=${selected.id}`} className="logout-btn" style={{ display: "inline-block" }}>
                Ver no Dispositivos
              </Link>
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-eyebrow">Adicionar conexao manual</div>
        <form onSubmit={handleCreateLink} style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
          <label className="field" style={{ minWidth: 220 }}>
            <span className="field-label">Ativo A</span>
            <select className="field-select" value={linkA} onChange={(e) => setLinkA(e.target.value)} required>
              <option value="">Selecione...</option>
              {sortedNodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
            </select>
          </label>
          <label className="field" style={{ minWidth: 220 }}>
            <span className="field-label">Ativo B</span>
            <select className="field-select" value={linkB} onChange={(e) => setLinkB(e.target.value)} required>
              <option value="">Selecione...</option>
              {sortedNodes.map((n) => <option key={n.id} value={n.id}>{n.name}</option>)}
            </select>
          </label>
          <label className="field">
            <span className="field-label">Tipo</span>
            <select className="field-select" value={linkType} onChange={(e) => setLinkType(e.target.value)}>
              <option value="Ethernet">Ethernet</option>
              <option value="Fibra">Fibra</option>
              <option value="Wireless">Wireless</option>
            </select>
          </label>
          <button type="submit" className="logout-btn" disabled={busy}>
            {busy ? "Salvando..." : "Conectar"}
          </button>
        </form>
        <p style={{ fontSize: 12, color: "var(--fg-2)", marginTop: 8 }}>
          Clique numa linha do grafo para remover a conexao.
        </p>
      </div>
    </Shell>
  );
}
