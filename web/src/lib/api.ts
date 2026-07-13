const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api";
const TOKEN_KEY = "infranoc.access";

export type LoginResult = {
  access_token: string;
  refresh_token: string;
  display_name: string;
  permissions: string[];
  token_type: string;
};

export function saveToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken() {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const body = new URLSearchParams();
  body.append("grant_type", "password");
  body.append("username", username);
  body.append("password", password);
  const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body });
  if (!res.ok) {
    if (res.status === 401) throw new Error("Usuario ou senha invalidos.");
    throw new Error(`Falha no login (HTTP ${res.status}).`);
  }
  return res.json();
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

/* Alertas */
export type Severity = "critical" | "high" | "warning" | "info";
export type AlertStatus = "firing" | "resolved";

export type Alert = {
  id: string;
  alertname: string;
  asset: string | null;
  severity: string;
  categoria: string | null;
  summary: string | null;
  impacto_negocio: string | null;
  status: AlertStatus;
  starts_at: string;
  ends_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
};

export type AlertStatusChange = {
  from_status: string | null;
  to_status: string;
  changed_at: string;
  note: string | null;
};

export type AlertDetail = Alert & {
  fingerprint: string;
  generator_url: string | null;
  labels: Record<string, unknown> | null;
  annotations: Record<string, unknown> | null;
  asset_id?: string | null;
  status_history: AlertStatusChange[];
};

export type AlertFilter = {
  status?: AlertStatus;
  area?: string;
  severity?: string;
  categoria?: string;
  limit?: number;
  offset?: number;
};

export async function listAlerts(filter: AlertFilter = {}): Promise<Alert[]> {
  const qs = new URLSearchParams();
  if (filter.status) qs.set("status", filter.status);
  if (filter.severity) qs.set("severity", filter.severity);
  if (filter.categoria) qs.set("categoria", filter.categoria);
  if (filter.area) qs.set("area", filter.area);
  if (filter.limit !== undefined) qs.set("limit", String(filter.limit));
  if (filter.offset !== undefined) qs.set("offset", String(filter.offset));
  const q = qs.toString();
  const res = await apiFetch(`/alerts${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar alertas (HTTP ${res.status}).`);
  return res.json();
}

export async function getAlert(id: string): Promise<AlertDetail> {
  const res = await apiFetch(`/alerts/${id}`);
  if (!res.ok) throw new Error(`Falha ao buscar alerta (HTTP ${res.status}).`);
  return res.json();
}

export async function ackAlert(id: string): Promise<void> {
  const res = await apiFetch(`/alerts/${id}/ack`, { method: "POST" });
  if (!res.ok) throw new Error(`Falha ao acked (HTTP ${res.status}).`);
}

/* Assets / CMDB (Fase 4.5) */
export type AssetType =
  | "Server" | "Workstation" | "Laptop" | "NetworkSwitch" | "Router" | "Firewall"
  | "AccessPoint" | "Printer" | "UPS" | "Generator" | "ACUnit" | "PLC" | "HMI"
  | "SCADA" | "Sensor" | "Scale" | "Camera" | "NVR" | "Phone" | "StorageArray"
  | "TapeLibrary" | "Motor" | "Tank" | "AirCompressor" | "SteamBoiler"
  | "ChilledWaterPump" | "BarcodeReader" | "Other";

export type Layer = "TI" | "OT" | "Physical";
export type AssetStatusValue = "Active" | "Maintenance" | "Retired" | "Storage" | "Faulty";
export type Criticality = "Low" | "Medium" | "High" | "Critical";
export type HierarchyLevel = "Area" | "Line" | "Equipment";

export type SectorRef = {
  id: string;
  code: string;
  name: string;
};

export type Sector = SectorRef & {
  description: string | null;
  oee_target: number | null;
  assets_count: number;
  equipments_count: number;
  alerts_firing: number;
  created_at: string;
  updated_at: string | null;
};

export type Asset = {
  id: string;
  name: string;
  display_name: string | null;
  description: string | null;
  type: AssetType;
  layer: Layer;
  site: string;
  location: string | null;
  status: AssetStatusValue;
  criticality: Criticality;
  ip_address: string | null;
  hostname: string | null;
  owner_email: string | null;
  owner_team: string | null;
  parent_id: string | null;
  sector_id: string | null;
  hierarchy_level: HierarchyLevel | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
};

export type AssetSummary = {
  id: string;
  name: string;
  type: AssetType;
  status: AssetStatusValue;
};

export type AssetDetail = Asset & {
  parent: AssetSummary | null;
  children: AssetSummary[];
  sector: SectorRef | null;
};

export type AlertOfAsset = {
  id: string;
  alertname: string;
  severity: string;
  status: string;
  summary: string | null;
  starts_at: string;
  ends_at: string | null;
};

export type AssetFilter = {
  type?: AssetType;
  layer?: Layer;
  site?: string;
  status?: AssetStatusValue;
  criticality?: Criticality;
  sector_code?: string;
  hierarchy_level?: HierarchyLevel;
  search?: string;
  limit?: number;
  offset?: number;
};

export type ListAssetsResult = {
  items: Asset[];
  total: number;
};

export async function listAssets(filter: AssetFilter = {}): Promise<ListAssetsResult> {
  const qs = new URLSearchParams();
  if (filter.type) qs.set("type", filter.type);
  if (filter.layer) qs.set("layer", filter.layer);
  if (filter.site) qs.set("site", filter.site);
  if (filter.status) qs.set("status", filter.status);
  if (filter.criticality) qs.set("criticality", filter.criticality);
  if (filter.sector_code) qs.set("sector_code", filter.sector_code);
  if (filter.hierarchy_level) qs.set("hierarchy_level", filter.hierarchy_level);
  if (filter.search) qs.set("search", filter.search);
  if (filter.limit != null) qs.set("limit", String(filter.limit));
  if (filter.offset != null) qs.set("offset", String(filter.offset));
  const query = qs.toString();
  const res = await apiFetch(`/assets${query ? "?" + query : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar ativos (HTTP ${res.status})`);
  const items = (await res.json()) as Asset[];
  const total = Number(res.headers.get("X-Total-Count") ?? items.length);
  return { items, total };
}

export async function getAsset(id: string): Promise<AssetDetail> {
  const res = await apiFetch(`/assets/${id}`);
  if (!res.ok) throw new Error(`Falha ao buscar ativo (HTTP ${res.status})`);
  return res.json();
}

export async function listAssetAlerts(id: string, status?: string): Promise<AlertOfAsset[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await apiFetch(`/assets/${id}/alerts${qs}`);
  if (!res.ok) throw new Error(`Falha ao listar alertas do ativo (HTTP ${res.status})`);
  return res.json();
}

/* Setores (Fase 4.5) */
export async function listSectors(): Promise<Sector[]> {
  const res = await apiFetch("/sectors");
  if (!res.ok) throw new Error(`Falha ao listar setores (HTTP ${res.status})`);
  return res.json();
}

/* Active Directory (Fase 5) */
export type ADUser = {
  sam: string;
  display_name: string;
  email: string;
  title: string;
  department: string;
  disabled: boolean;
  locked: boolean;
  dn: string;
  groups: string[];
};

export type ADSummary = {
  total: number;
  locked: number;
  disabled: number;
  by_department: Record<string, number>;
};

export type ADAuditEvent = {
  id: string;
  event_id: number;
  at: string;
  target_sam: string | null;
  actor_sam: string | null;
  message: string;
};

export async function listAdUsers(q?: string, ou?: string): Promise<ADUser[]> {
  const qs = new URLSearchParams();
  if (q) qs.set("q", q);
  if (ou) qs.set("ou", ou);
  const query = qs.toString();
  const res = await apiFetch(`/directory/users${query ? "?" + query : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar usuarios AD (HTTP ${res.status})`);
  return res.json();
}

export async function getAdSummary(): Promise<ADSummary> {
  const res = await apiFetch("/directory/summary");
  if (!res.ok) throw new Error(`Falha ao buscar summary AD (HTTP ${res.status})`);
  return res.json();
}

export async function resetPassword(sam: string, newPassword: string, mustChange = true): Promise<void> {
  const res = await apiFetch(`/directory/users/${sam}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword, must_change: mustChange }),
  });
  if (!res.ok) throw new Error(`Falha ao resetar senha (HTTP ${res.status})`);
}



export async function unlockUser(sam: string): Promise<void> {
  const res = await apiFetch(`/directory/users/${sam}/unlock`, { method: "POST" });
  if (!res.ok) throw new Error(`Falha ao desbloquear usuario (HTTP ${res.status})`);
}

export async function setEnabled(sam: string, value: boolean): Promise<void> {
  const res = await apiFetch(`/directory/users/${sam}/enable?value=${value}`, { method: "POST" });
  if (!res.ok) throw new Error(`Falha ao alterar status (HTTP ${res.status})`);
}

export async function changeGroup(sam: string, groupDn: string, add: boolean): Promise<void> {
  const res = await apiFetch(`/directory/users/${sam}/groups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_dn: groupDn, add }),
  });
  if (!res.ok) throw new Error(`Falha ao alterar grupo (HTTP ${res.status})`);
}

export async function listAdAudit(params?: {
  event_id?: number;
  target_sam?: string;
  limit?: number;
}): Promise<ADAuditEvent[]> {
  const qs = new URLSearchParams();
  if (params?.event_id) qs.set("event_id", String(params.event_id));
  if (params?.target_sam) qs.set("target_sam", params.target_sam);
  if (params?.limit) qs.set("limit", String(params.limit));
  const query = qs.toString();
  const res = await apiFetch(`/directory/audit${query ? "?" + query : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar auditoria AD (HTTP ${res.status})`);
  return res.json();
}

/* ============================================================
   Fase 6b â€” Integracoes (Peppermint) / Chamados
   ============================================================ */

/* Integracoes (Peppermint) â€” schema real de IntegrationSettings */
export type IntegrationSettings = {
  peppermint_url: string | null;
  peppermint_email: string | null;
  peppermint_password: string | null; // vem mascarado do backend (ex: "****")
  peppermint_default_email: string | null;
  peppermint_enabled: boolean;
  auto_ticket_min_severity: Severity;
  storm_window_seconds: number;
  storm_threshold: number;
  updated_at: string | null;
  updated_by: string | null;
};

export type IntegrationTestResult = {
  ok: boolean;
  message: string;
};

export async function getIntegrationSettings(): Promise<IntegrationSettings> {
  const res = await apiFetch("/integrations");
  if (!res.ok) throw new Error(`Falha ao buscar configuracao (HTTP ${res.status}).`);
  return res.json();
}

export async function updateIntegrationSettings(
  data: Partial<Omit<IntegrationSettings, "updated_at" | "updated_by">>
): Promise<IntegrationSettings> {
  const res = await apiFetch("/integrations", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Falha ao salvar configuracao (HTTP ${res.status}).`);
  return res.json();
}

export async function testIntegrationConnection(): Promise<IntegrationTestResult> {
  const res = await apiFetch("/integrations/test-connection", { method: "POST" });
  if (!res.ok) {
    let message = `Falha ao testar conexao (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) message = body.detail;
    } catch {
      /* ignore */
    }
    return { ok: false, message };
  }
  return res.json();
}

/* Chamados (TicketLink) â€” dados vem "achatados" do backend (JOIN com Alert) */
export type TicketLinkStatus = "open" | "closed";

export type TicketLink = {
  id: string;
  alert_id: string | null;
  alertname: string | null;
  asset: string | null;
  severity: string | null;
  ticket_id: string;
  ticket_url: string;
  status: TicketLinkStatus;
  created_at: string;
  closed_at: string | null;
};

export type TicketLinkFilter = {
  status?: TicketLinkStatus;
  limit?: number;
  offset?: number;
};

export async function listTicketLinks(filter: TicketLinkFilter = {}): Promise<TicketLink[]> {
  const qs = new URLSearchParams();
  if (filter.status) qs.set("status", filter.status);
  if (filter.limit !== undefined) qs.set("limit", String(filter.limit));
  if (filter.offset !== undefined) qs.set("offset", String(filter.offset));
  const q = qs.toString();
  const res = await apiFetch(`/tickets${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar chamados (HTTP ${res.status}).`);
  return res.json();
}

/* IA */
export async function askAiStream(
  question: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await apiFetch("/ai/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) {
    if (res.status === 403) throw new Error("Sem permissao para usar a IA (ai.chat).");
    throw new Error("Falha na IA (HTTP " + res.status + ").");
  }
  if (!res.body) throw new Error("Resposta sem corpo (stream indisponivel).");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk(decoder.decode(value, { stream: true }));
  }
}
