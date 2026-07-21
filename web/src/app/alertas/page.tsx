"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import {
  ackAlert,
  Alert,
  AlertDetail,
  AlertStatus,
  createWikiPage,
  getAlert,
  listAlerts,
  WikiCategory,
} from "@/lib/api";

const REFRESH_MS = 15000;

const ALERT_CAT_TO_WIKI: Record<string, WikiCategory> = {
  OT: "ot",
  energia: "energia",
  TI: "geral",
  AD: "ad",
};

const SEV_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  warning: 2,
  info: 3,
};

const AREA_LABELS: Record<string, string> = {
  recebimento: "Recebimento",
  pasteurizacao: "Pasteurizacao",
  laboratorio: "Laboratorio",
  linha1: "Linha 1 UHT",
  linha2: "Linha 2 Iogurte",
  linha3: "Linha 3 Queijo Frescal",
  linha4: "Linha 4 Manteiga",
  camaras: "Camaras Frias",
  expedicao: "Expedicao",
  utilidades: "Utilidades",
  datacenter: "Datacenter",
};

function severityBadge(sev: string) {
  const known = ["critical", "high", "warning", "info"];
  const cls = known.includes(sev.toLowerCase())
    ? `badge badge-sev-${sev.toLowerCase()}`
    : "badge badge-cat";
  return <span className={cls}>{sev}</span>;
}

function statusBadge(status: string) {
  const cls =
    status === "firing" ? "badge badge-status-firing" : "badge badge-status-resolved";
  return <span className={cls}>{status}</span>;
}

function fmtDateTime(iso: string | null) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function fmtRelative(iso: string) {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Math.floor((now - then) / 1000));
  if (diff < 60) return `${diff}s atras`;
  if (diff < 3600) return `${Math.floor(diff / 60)}min atras`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atras`;
  return `${Math.floor(diff / 86400)}d atras`;
}

function AlertasContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const areaParam = searchParams.get("area") ?? "";

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [fStatus, setFStatus] = useState<"" | AlertStatus>("firing");
  const [fSeverity, setFSeverity] = useState<string>("");
  const [fCategoria, setFCategoria] = useState<string>("");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AlertDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [ackBusy, setAckBusy] = useState<string | null>(null);

  const [docAlert, setDocAlert] = useState<Alert | null>(null);
  const [docTitle, setDocTitle] = useState("");
  const [docCategory, setDocCategory] = useState<WikiCategory>("geral");
  const [docContent, setDocContent] = useState("");
  const [docSaving, setDocSaving] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await listAlerts({
        status: fStatus || undefined,
        severity: fSeverity || undefined,
        categoria: fCategoria || undefined,
        area: areaParam || undefined,
        limit: 200,
      });
      data.sort((a, b) => {
        if (a.status !== b.status) return a.status === "firing" ? -1 : 1;
        const sa = SEV_ORDER[a.severity.toLowerCase()] ?? 99;
        const sb = SEV_ORDER[b.severity.toLowerCase()] ?? 99;
        if (sa !== sb) return sa - sb;
        return new Date(b.starts_at).getTime() - new Date(a.starts_at).getTime();
      });
      setAlerts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }, [fStatus, fSeverity, fCategoria, areaParam]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let alive = true;
    setDetailLoading(true);
    getAlert(selectedId)
      .then((d) => { if (alive) setDetail(d); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : "Erro no detalhe."); })
      .finally(() => { if (alive) setDetailLoading(false); });
    return () => { alive = false; };
  }, [selectedId]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedId(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function clearArea() {
    router.push("/alertas");
  }

  async function handleAck(a: Alert, ev: React.MouseEvent) {
    ev.stopPropagation();
    setAckBusy(a.id);
    setError(null);
    try {
      await ackAlert(a.id);
      await load();
      setDocAlert(a);
      setDocTitle(`Solucao: ${a.alertname}${a.asset ? " em " + a.asset : ""}`);
      setDocCategory(ALERT_CAT_TO_WIKI[a.categoria ?? ""] ?? "geral");
      setDocContent(
        `## Contexto\n\n` +
        `- Alerta: ${a.alertname}\n` +
        (a.asset ? `- Ativo: ${a.asset}\n` : "") +
        `- Severidade: ${a.severity}\n` +
        (a.summary ? `- Resumo: ${a.summary}\n` : "") +
        `\n## Solucao aplicada\n\n(descreva aqui o que foi feito para resolver)\n`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao acked.");
    } finally {
      setAckBusy(null);
    }
  }

  async function handleSaveDoc() {
    setDocSaving(true);
    setDocError(null);
    try {
      const slugBase = docTitle
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "");
      const slug = `${slugBase}-${Date.now()}`;
      await createWikiPage({
        slug,
        title: docTitle,
        category: docCategory,
        content_md: docContent,
        tags: docAlert?.categoria ? [docAlert.categoria.toLowerCase(), "incidente"] : ["incidente"],
      });
      setDocAlert(null);
    } catch (e) {
      setDocError(e instanceof Error ? e.message : "Erro ao salvar na wiki.");
    } finally {
      setDocSaving(false);
    }
  }

  const areaLabel = areaParam ? (AREA_LABELS[areaParam] ?? areaParam) : "";

  return (
    <>
      <div className="alerts-toolbar">
        <label className="field">
          <span className="field-label">Status</span>
          <select
            className="field-select"
            value={fStatus}
            onChange={(e) => setFStatus(e.target.value as "" | AlertStatus)}
          >
            <option value="">todos</option>
            <option value="firing">firing</option>
            <option value="resolved">resolved</option>
          </select>
        </label>

        <label className="field">
          <span className="field-label">Severity</span>
          <select
            className="field-select"
            value={fSeverity}
            onChange={(e) => setFSeverity(e.target.value)}
          >
            <option value="">todas</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
        </label>

        <label className="field">
          <span className="field-label">Categoria</span>
          <select
            className="field-select"
            value={fCategoria}
            onChange={(e) => setFCategoria(e.target.value)}
          >
            <option value="">todas</option>
            <option value="OT">OT</option>
            <option value="energia">energia</option>
            <option value="TI">TI</option>
            <option value="AD">AD</option>
          </select>
        </label>

        {areaParam && (
          <div
            style={{
              display: "flex", alignItems: "center", gap: 8,
              padding: "6px 10px", borderRadius: 8,
              background: "rgba(59,130,246,0.15)",
              border: "1px solid rgba(59,130,246,0.4)",
            }}
          >
            <span style={{ fontSize: 12, color: "var(--fg-2)" }}>Area:</span>
            <span style={{ fontWeight: 600 }}>{areaLabel}</span>
            <button
              onClick={clearArea}
              style={{
                background: "transparent", border: "none",
                color: "var(--fg-2)", cursor: "pointer",
                fontSize: 16, lineHeight: 1, padding: 0,
              }}
              title="Limpar filtro de area"
            >
              x
            </button>
          </div>
        )}

        <span className="alerts-count">
          {loading ? "carregando..." : `${alerts.length} alerta(s)`}
        </span>
      </div>

      {error && (
        <div className="login-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!loading && alerts.length === 0 ? (
        <div className="empty">Nenhum alerta com esses filtros.</div>
      ) : (
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Alertname</th>
              <th>Asset</th>
              <th>Categoria</th>
              <th>Status</th>
              <th>Iniciado</th>
              <th>Acao</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id} onClick={() => setSelectedId(a.id)}>
                <td>{severityBadge(a.severity)}</td>
                <td>
                  <div className="alert-name">{a.alertname}</div>
                  {a.summary && (
                    <div style={{ color: "var(--fg-2)", fontSize: 12 }}>{a.summary}</div>
                  )}
                </td>
                <td className="alert-asset">{a.asset ?? "-"}</td>
                <td>
                  {a.categoria ? <span className="badge badge-cat">{a.categoria}</span> : "-"}
                </td>
                <td>{statusBadge(a.status)}</td>
                <td className="alert-time">
                  {fmtRelative(a.starts_at)}
                  <div style={{ fontSize: 11 }}>{fmtDateTime(a.starts_at)}</div>
                </td>
                <td>
                  {a.status === "firing" ? (
                    <button
                      onClick={(ev) => handleAck(a, ev)}
                      disabled={ackBusy === a.id}
                      style={{
                        padding: "4px 10px", borderRadius: 6,
                        background: "var(--accent-strong, #334155)",
                        color: "#fff", border: "none", cursor: "pointer",
                        fontSize: 12, opacity: ackBusy === a.id ? 0.5 : 1,
                      }}
                    >
                      {ackBusy === a.id ? "..." : "Ack"}
                    </button>
                  ) : (
                    <span style={{ fontSize: 11, color: "var(--fg-2)" }}>-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedId && (
        <>
          <div className="drawer-backdrop" onClick={() => setSelectedId(null)} />
          <aside className="drawer">
            <div className="drawer-header">
              <div>
                <h2 className="drawer-title">{detail?.alertname ?? "carregando..."}</h2>
                {detail?.asset && <div className="drawer-subtitle">{detail.asset}</div>}
              </div>
              <button className="drawer-close" onClick={() => setSelectedId(null)}>
                x
              </button>
            </div>

            <div className="drawer-body">
              {detailLoading && <p style={{ color: "var(--fg-2)" }}>carregando...</p>}
              {detail && (
                <>
                  <div className="drawer-section">
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {severityBadge(detail.severity)}
                      {statusBadge(detail.status)}
                      {detail.categoria && (
                        <span className="badge badge-cat">{detail.categoria}</span>
                      )}
                    </div>
                  </div>

                  {detail.summary && (
                    <div className="drawer-section">
                      <div className="drawer-section-title">Resumo</div>
                      <div>{detail.summary}</div>
                    </div>
                  )}

                  {detail.impacto_negocio && (
                    <div className="drawer-section">
                      <div className="drawer-section-title">Impacto no negocio</div>
                      <div>{detail.impacto_negocio}</div>
                    </div>
                  )}

                  <div className="drawer-section">
                    <div className="drawer-section-title">Metadados</div>
                    <dl className="drawer-kv">
                      <dt>fingerprint</dt>
                      <dd style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}>
                        {detail.fingerprint}
                      </dd>
                      {detail.asset_id && (
                        <>
                          <dt>ativo (CMDB)</dt>
                          <dd>
                            <span className="asset-link" onClick={() => router.push(`/ativos?open=${detail.asset_id}`)}>ver ativo</span>
                          </dd>
                        </>
                      )}
                      <dt>iniciado</dt>
                      <dd>{fmtDateTime(detail.starts_at)}</dd>
                      <dt>encerrado</dt>
                      <dd>{fmtDateTime(detail.ends_at)}</dd>
                      {detail.generator_url && (
                        <>
                          <dt>Prometheus</dt>
                          <dd>
                            <a href={detail.generator_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent-strong)" }}>abrir consulta</a>
                          </dd>
                        </>
                      )}
                    </dl>
                  </div>

                  <div className="drawer-section">
                    <div className="drawer-section-title">
                      Historico de status ({detail.status_history.length})
                    </div>
                    <div className="timeline">
                      {detail.status_history.map((h, i) => (
                        <div key={i} className="timeline-item">
                          <div className="timeline-status">
                            {h.from_status ? `${h.from_status} -> ${h.to_status}` : h.to_status}
                          </div>
                          <div className="timeline-time">{fmtDateTime(h.changed_at)}</div>
                          {h.note && <div className="timeline-note">{h.note}</div>}
                        </div>
                      ))}
                    </div>
                  </div>

                  {detail.labels && Object.keys(detail.labels).length > 0 && (
                    <div className="drawer-section">
                      <div className="drawer-section-title">Labels</div>
                      <pre className="json-block">
                        {JSON.stringify(detail.labels, null, 2)}
                      </pre>
                    </div>
                  )}

                  {detail.annotations && Object.keys(detail.annotations).length > 0 && (
                    <div className="drawer-section">
                      <div className="drawer-section-title">Annotations</div>
                      <pre className="json-block">
                        {JSON.stringify(detail.annotations, null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              )}
            </div>
          </aside>
        </>
      )}
      {docAlert && (
        <>
          <div className="drawer-backdrop" onClick={() => setDocAlert(null)} />
          <aside className="drawer">
            <div className="drawer-header">
              <div>
                <h2 className="drawer-title">Documentar solucao?</h2>
                <div className="drawer-subtitle">{docAlert.alertname}</div>
              </div>
              <button className="drawer-close" onClick={() => setDocAlert(null)}>x</button>
            </div>
            <div className="drawer-body">
              {docError && <div className="login-error" style={{ marginBottom: 12 }}>{docError}</div>}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <label className="field">
                  <span className="field-label">Titulo</span>
                  <input className="field-select" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">Categoria</span>
                  <select
                    className="field-select"
                    value={docCategory}
                    onChange={(e) => setDocCategory(e.target.value as WikiCategory)}
                  >
                    <option value="rede">rede</option>
                    <option value="ad">ad</option>
                    <option value="linux">linux</option>
                    <option value="ot">ot</option>
                    <option value="energia">energia</option>
                    <option value="seguranca">seguranca</option>
                    <option value="geral">geral</option>
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">Solucao (Markdown)</span>
                  <textarea
                    className="field-select"
                    rows={12}
                    value={docContent}
                    onChange={(e) => setDocContent(e.target.value)}
                    style={{ fontFamily: "monospace", resize: "vertical" }}
                  />
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="logout-btn" onClick={handleSaveDoc} disabled={docSaving}>
                    {docSaving ? "Salvando..." : "Salvar na wiki"}
                  </button>
                  <button className="logout-btn" onClick={() => setDocAlert(null)}>Agora nao</button>
                </div>
              </div>
            </div>
          </aside>
        </>
      )}
    </>
  );
}

export default function AlertasPage() {
  return (
    <Shell title="Alertas">
      <Suspense fallback={<div className="empty">carregando...</div>}>
        <AlertasContent />
      </Suspense>
    </Shell>
  );
}