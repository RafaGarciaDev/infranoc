"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import {
  Asset,
  AssetDetail,
  AssetFilter,
  AssetType,
  AlertOfAsset,
  Criticality,
  HierarchyLevel,
  Layer,
  Sector,
  AssetStatusValue,
  getAsset,
  listAssets,
  listAssetAlerts,
  listSectors,
} from "@/lib/api";

const ASSET_TYPES: AssetType[] = [
  "Server", "Workstation", "Laptop", "NetworkSwitch", "Router", "Firewall",
  "AccessPoint", "Printer", "UPS", "Generator", "ACUnit", "PLC", "HMI",
  "SCADA", "Sensor", "Scale", "Camera", "NVR", "Phone", "StorageArray",
  "TapeLibrary", "Motor", "Tank", "AirCompressor", "SteamBoiler",
  "ChilledWaterPump", "BarcodeReader", "Other",
];
const LAYERS: Layer[] = ["TI", "OT", "Physical"];
const STATUSES: AssetStatusValue[] = ["Active", "Maintenance", "Retired", "Storage", "Faulty"];
const CRITS: Criticality[] = ["Critical", "High", "Medium", "Low"];
const HIER_LEVELS: HierarchyLevel[] = ["Equipment", "Line", "Area"];

const PAGE_SIZE = 50;

function critBadge(c: Criticality) {
  return <span className={`badge badge-crit-${c}`}>{c}</span>;
}
function layerBadge(l: Layer) {
  return <span className={`badge badge-layer-${l}`}>{l}</span>;
}
function statusBadge(s: AssetStatusValue) {
  return <span className={`badge badge-astatus-${s}`}>{s}</span>;
}
function sevBadge(sev: string) {
  const known = ["critical", "high", "warning", "info"];
  const cls = known.includes(sev.toLowerCase())
    ? `badge badge-sev-${sev.toLowerCase()}`
    : "badge badge-cat";
  return <span className={cls}>{sev}</span>;
}
function alertStatusBadge(s: string) {
  const cls = s === "firing" ? "badge badge-status-firing" : "badge badge-status-resolved";
  return <span className={cls}>{s}</span>;
}
function fmtDate(iso: string | null) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function AtivosInner() {
  const searchParams = useSearchParams();

  const [assets, setAssets] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [sectors, setSectors] = useState<Sector[]>([]);

  const [filter, setFilter] = useState<AssetFilter>({
    limit: PAGE_SIZE,
    offset: 0,
    hierarchy_level: "Equipment",
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [assetAlerts, setAssetAlerts] = useState<AlertOfAsset[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // Carrega setores uma vez
  useEffect(() => {
    listSectors()
      .then(setSectors)
      .catch((e) => setErr((e as Error).message));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const { items, total } = await listAssets(filter);
      setAssets(items);
      setTotal(total);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const openId = searchParams.get("open");
    if (openId) setSelectedId(openId);
  }, [searchParams]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setAssetAlerts([]);
      return;
    }
    setDetailLoading(true);
    Promise.all([getAsset(selectedId), listAssetAlerts(selectedId)])
      .then(([d, al]) => {
        setDetail(d);
        setAssetAlerts(al);
      })
      .catch((e) => setErr((e as Error).message))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  function updateFilter<K extends keyof AssetFilter>(key: K, value: AssetFilter[K] | "") {
    setFilter((f) => {
      const nf: AssetFilter = { ...f, offset: 0 };
      if (value === "" || value == null) delete nf[key];
      else nf[key] = value as AssetFilter[K];
      return nf;
    });
  }

  function goToPage(newOffset: number) {
    setFilter((f) => ({ ...f, offset: Math.max(0, newOffset) }));
  }

  const offset = filter.offset ?? 0;
  const pageFrom = total === 0 ? 0 : offset + 1;
  const pageTo = Math.min(offset + PAGE_SIZE, total);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  return (
    <Shell title="Ativos (CMDB)">
      <div className="cmdb-filters">
        <input
          placeholder="Buscar por name, hostname, ip..."
          value={filter.search ?? ""}
          onChange={(e) => updateFilter("search", e.target.value)}
        />
        <select
          value={filter.sector_code ?? ""}
          onChange={(e) => updateFilter("sector_code", e.target.value)}
        >
          <option value="">Setor (todos)</option>
          {sectors.map((s) => (
            <option key={s.code} value={s.code}>{s.name}</option>
          ))}
        </select>
        <select
          value={filter.hierarchy_level ?? ""}
          onChange={(e) => updateFilter("hierarchy_level", e.target.value as HierarchyLevel)}
        >
          <option value="">Nivel (todos)</option>
          {HIER_LEVELS.map((h) => <option key={h} value={h}>{h}</option>)}
        </select>
        <select value={filter.type ?? ""} onChange={(e) => updateFilter("type", e.target.value as AssetType)}>
          <option value="">Tipo (todos)</option>
          {ASSET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={filter.layer ?? ""} onChange={(e) => updateFilter("layer", e.target.value as Layer)}>
          <option value="">Camada (todas)</option>
          {LAYERS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <select value={filter.criticality ?? ""} onChange={(e) => updateFilter("criticality", e.target.value as Criticality)}>
          <option value="">Criticidade (todas)</option>
          {CRITS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filter.status ?? ""} onChange={(e) => updateFilter("status", e.target.value as AssetStatusValue)}>
          <option value="">Status (todos)</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {err && <div style={{ color: "var(--sev-critical)", marginBottom: 12 }}>Erro: {err}</div>}

      {loading ? (
        <div style={{ color: "var(--fg-2)" }}>Carregando ativos...</div>
      ) : (
        <>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            color: "var(--fg-2)", fontSize: 12, marginBottom: 8,
          }}>
            <span>
              {total === 0 ? "Nenhum ativo" : `Mostrando ${pageFrom}-${pageTo} de ${total}`}
            </span>
            <span style={{ display: "flex", gap: 8 }}>
              <button
                className="drawer-close"
                onClick={() => goToPage(offset - PAGE_SIZE)}
                disabled={!hasPrev}
                style={{ opacity: hasPrev ? 1 : 0.4, cursor: hasPrev ? "pointer" : "default" }}
              >
                &laquo; Anterior
              </button>
              <button
                className="drawer-close"
                onClick={() => goToPage(offset + PAGE_SIZE)}
                disabled={!hasNext}
                style={{ opacity: hasNext ? 1 : 0.4, cursor: hasNext ? "pointer" : "default" }}
              >
                Proxima &raquo;
              </button>
            </span>
          </div>
          <table className="cmdb-table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Tipo</th>
                <th>Camada</th>
                <th>Criticidade</th>
                <th>Status</th>
                <th>Site</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id} onClick={() => setSelectedId(a.id)}>
                  <td>
                    <div className="cell-name">{a.name}</div>
                    {a.display_name && <div className="cell-sub">{a.display_name}</div>}
                  </td>
                  <td>{a.type}</td>
                  <td>{layerBadge(a.layer)}</td>
                  <td>{critBadge(a.criticality)}</td>
                  <td>{statusBadge(a.status)}</td>
                  <td>{a.site}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {selectedId && (
        <>
          <div className="drawer-backdrop" onClick={() => setSelectedId(null)} />
          <aside className="drawer">
            <div className="drawer-header">
              <div>
                {detail?.sector && (
                  <div style={{ fontSize: 11, color: "var(--fg-2)", marginBottom: 6 }}>
                    <span
                      className="asset-link"
                      onClick={() => {
                        updateFilter("sector_code", detail.sector!.code);
                        setSelectedId(null);
                      }}
                    >
                      {detail.sector.name}
                    </span>
                    {detail.parent && (
                      <>
                        {" \u203A "}
                        <span
                          className="asset-link"
                          onClick={() => setSelectedId(detail.parent!.id)}
                        >
                          {detail.parent.name}
                        </span>
                      </>
                    )}
                    {" \u203A "}
                    <span>{detail.name}</span>
                  </div>
                )}
                <div style={{ fontSize: 18, fontWeight: 600, color: "var(--fg-0)" }}>
                  {detail?.name ?? "..."}
                </div>
                {detail?.display_name && (
                  <div style={{ fontSize: 13, color: "var(--fg-2)", marginTop: 2 }}>
                    {detail.display_name}
                  </div>
                )}
              </div>
              <button className="drawer-close" onClick={() => setSelectedId(null)}>
                Fechar
              </button>
            </div>

            {detailLoading || !detail ? (
              <div style={{ color: "var(--fg-2)" }}>Carregando...</div>
            ) : (
              <>
                <div className="drawer-section">
                  <div className="drawer-section-title">Identificacao</div>
                  <dl className="drawer-kv">
                    <dt>tipo</dt><dd>{detail.type}</dd>
                    <dt>camada</dt><dd>{layerBadge(detail.layer)}</dd>
                    <dt>criticidade</dt><dd>{critBadge(detail.criticality)}</dd>
                    <dt>status</dt><dd>{statusBadge(detail.status)}</dd>
                    <dt>site</dt><dd>{detail.site}</dd>
                    {detail.hierarchy_level && (<><dt>nivel</dt><dd>{detail.hierarchy_level}</dd></>)}
                    {detail.sector && (<><dt>setor</dt><dd>{detail.sector.name}</dd></>)}
                    {detail.location && (<><dt>local</dt><dd>{detail.location}</dd></>)}
                    {detail.hostname && (<><dt>hostname</dt><dd>{detail.hostname}</dd></>)}
                    {detail.ip_address && (<><dt>ip</dt><dd>{detail.ip_address}</dd></>)}
                    {detail.owner_team && (<><dt>time</dt><dd>{detail.owner_team}</dd></>)}
                  </dl>
                </div>

                {(detail.parent || detail.children.length > 0) && (
                  <div className="drawer-section">
                    <div className="drawer-section-title">Relacoes</div>
                    {detail.parent && (
                      <div style={{ marginBottom: 6, fontSize: 13 }}>
                        pai:{" "}
                        <span className="asset-link" onClick={() => setSelectedId(detail.parent!.id)}>
                          {detail.parent.name}
                        </span>
                      </div>
                    )}
                    {detail.children.length > 0 && (
                      <div style={{ fontSize: 13 }}>
                        filhos ({detail.children.length}):{" "}
                        {detail.children.slice(0, 20).map((ch, i) => (
                          <span key={ch.id}>
                            {i > 0 && ", "}
                            <span className="asset-link" onClick={() => setSelectedId(ch.id)}>
                              {ch.name}
                            </span>
                          </span>
                        ))}
                        {detail.children.length > 20 && (
                          <span style={{ color: "var(--fg-2)" }}>
                            {" "}(+{detail.children.length - 20} outros)
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="drawer-section">
                  <div className="drawer-section-title">Alertas ({assetAlerts.length})</div>
                  {assetAlerts.length === 0 ? (
                    <div style={{ color: "var(--fg-2)", fontSize: 13 }}>
                      Sem alertas registrados
                    </div>
                  ) : (
                    assetAlerts.map((al) => (
                      <div key={al.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          {sevBadge(al.severity)}
                          {alertStatusBadge(al.status)}
                          <span style={{ fontSize: 13 }}>{al.alertname}</span>
                        </div>
                        {al.summary && (
                          <div style={{ color: "var(--fg-2)", fontSize: 12, marginTop: 2 }}>
                            {al.summary}
                          </div>
                        )}
                        <div style={{ color: "var(--fg-2)", fontSize: 11, marginTop: 2 }}>
                          {fmtDate(al.starts_at)}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {detail.metadata_json && Object.keys(detail.metadata_json).length > 0 && (
                  <div className="drawer-section">
                    <div className="drawer-section-title">Metadata</div>
                    <pre className="json-block">{JSON.stringify(detail.metadata_json, null, 2)}</pre>
                  </div>
                )}
              </>
            )}
          </aside>
        </>
      )}
    </Shell>
  );
}

export default function AtivosPage() {
  return (
    <Suspense fallback={null}>
      <AtivosInner />
    </Suspense>
  );
}