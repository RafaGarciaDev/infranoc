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
  last_logon: string | null;
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


/* Wiki (Base de Conhecimento - Fase 9b) */
export type WikiCategory = "rede" | "ad" | "linux" | "ot" | "energia" | "seguranca" | "geral";

export type WikiPageListItem = {
  slug: string;
  title: string;
  category: WikiCategory;
  tags: string[];
  version: number;
  updated_at: string;
};

export type WikiPageDetail = WikiPageListItem & {
  content_md: string;
  author_email: string | null;
};

export type WikiPageVersionOut = {
  version: number;
  author_email: string | null;
  created_at: string;
};

export type WikiPageCreateInput = {
  slug: string;
  title: string;
  category: WikiCategory;
  content_md: string;
  tags?: string[];
};

export type WikiPageUpdateInput = {
  title?: string;
  category?: WikiCategory;
  content_md?: string;
  tags?: string[];
};

export async function listWikiPages(filter?: { category?: string; tag?: string }): Promise<WikiPageListItem[]> {
  const qs = new URLSearchParams();
  if (filter?.category) qs.set("category", filter.category);
  if (filter?.tag) qs.set("tag", filter.tag);
  const q = qs.toString();
  const res = await apiFetch(`/wiki${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error(`Falha ao listar paginas da wiki (HTTP ${res.status}).`);
  return res.json();
}

export async function getWikiPage(slug: string): Promise<WikiPageDetail> {
  const res = await apiFetch(`/wiki/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(`Falha ao buscar pagina (HTTP ${res.status}).`);
  return res.json();
}

export async function getWikiHistory(slug: string): Promise<WikiPageVersionOut[]> {
  const res = await apiFetch(`/wiki/${encodeURIComponent(slug)}/history`);
  if (!res.ok) throw new Error(`Falha ao buscar historico (HTTP ${res.status}).`);
  return res.json();
}

export async function createWikiPage(body: WikiPageCreateInput): Promise<WikiPageDetail> {
  const res = await apiFetch(`/wiki`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Falha ao criar pagina (HTTP ${res.status}).`);
  return res.json();
}

export async function updateWikiPage(slug: string, body: WikiPageUpdateInput): Promise<WikiPageDetail> {
  const res = await apiFetch(`/wiki/${encodeURIComponent(slug)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Falha ao editar pagina (HTTP ${res.status}).`);
  return res.json();
}

export async function deleteWikiPage(slug: string): Promise<void> {
  const res = await apiFetch(`/wiki/${encodeURIComponent(slug)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Falha ao excluir pagina (HTTP ${res.status}).`);
}


/* Gestao de OUs (Active Directory) - Fase 9c */
export type OU = {
  name: string;
  dn: string;
  parent_dn: string;
};

export async function listOUs(baseDn?: string): Promise<OU[]> {
  const qs = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : "";
  const res = await apiFetch(`/directory/ous${qs}`);
  if (!res.ok) throw new Error(`Falha ao listar OUs (HTTP ${res.status}).`);
  return res.json();
}

export async function createOU(name: string, parentDn?: string): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/ous`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, parent_dn: parentDn }),
  });
  if (!res.ok) throw new Error(`Falha ao criar OU (HTTP ${res.status}).`);
  return res.json();
}

export async function renameOU(dn: string, newName: string): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/ous/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn, new_name: newName }),
  });
  if (!res.ok) throw new Error(`Falha ao renomear OU (HTTP ${res.status}).`);
  return res.json();
}

export async function moveOU(dn: string, newParentDn: string): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/ous/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn, new_parent_dn: newParentDn }),
  });
  if (!res.ok) throw new Error(`Falha ao mover OU (HTTP ${res.status}).`);
  return res.json();
}

export async function deleteOU(dn: string): Promise<void> {
  const res = await apiFetch(`/directory/ous/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn }),
  });
  if (!res.ok) {
    let msg = `Falha ao excluir OU (HTTP ${res.status}).`;
    try {
      const data = await res.json();
      if (data?.detail) msg = data.detail;
    } catch {}
    throw new Error(msg);
  }
}


/* Gestao de Grupos (Active Directory) - Fase 9c */
export type ADGroupScope = "Global" | "DomainLocal" | "Universal";
export type ADGroupType = "Security" | "Distribution";

export type ADGroup = {
  name: string;
  dn: string;
  description: string;
  scope: ADGroupScope;
  group_type: ADGroupType;
  member_count: number;
};

export async function listGroups(baseDn?: string): Promise<ADGroup[]> {
  const qs = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : "";
  const res = await apiFetch(`/directory/groups${qs}`);
  if (!res.ok) throw new Error(`Falha ao listar grupos (HTTP ${res.status}).`);
  return res.json();
}

export async function createGroup(input: {
  name: string; parentDn?: string; scope?: ADGroupScope; groupType?: ADGroupType; description?: string;
}): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/groups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      parent_dn: input.parentDn,
      scope: input.scope ?? "Global",
      group_type: input.groupType ?? "Security",
      description: input.description ?? "",
    }),
  });
  if (!res.ok) throw new Error(`Falha ao criar grupo (HTTP ${res.status}).`);
  return res.json();
}

export async function renameGroup(dn: string, newName: string): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/groups/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn, new_name: newName }),
  });
  if (!res.ok) throw new Error(`Falha ao renomear grupo (HTTP ${res.status}).`);
  return res.json();
}

export async function updateGroup(dn: string, changes: {
  description?: string; scope?: ADGroupScope; groupType?: ADGroupType;
}): Promise<void> {
  const res = await apiFetch(`/directory/groups/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dn, description: changes.description, scope: changes.scope, group_type: changes.groupType,
    }),
  });
  if (!res.ok) throw new Error(`Falha ao atualizar grupo (HTTP ${res.status}).`);
}

export async function deleteGroup(dn: string): Promise<void> {
  const res = await apiFetch(`/directory/groups/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn }),
  });
  if (!res.ok) throw new Error(`Falha ao excluir grupo (HTTP ${res.status}).`);
}


/* Gestao de Computadores (Active Directory) - Fase 9c */
export type ADComputer = {
  name: string;
  dn: string;
  os: string;
  disabled: boolean;
};

export async function listComputers(baseDn?: string): Promise<ADComputer[]> {
  const qs = baseDn ? `?base_dn=${encodeURIComponent(baseDn)}` : "";
  const res = await apiFetch(`/directory/computers${qs}`);
  if (!res.ok) throw new Error(`Falha ao listar computadores (HTTP ${res.status}).`);
  return res.json();
}

export async function setComputerEnabled(dn: string, value: boolean): Promise<void> {
  const res = await apiFetch(`/directory/computers/enable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn, value }),
  });
  if (!res.ok) throw new Error(`Falha ao alterar status (HTTP ${res.status}).`);
}

export async function moveComputer(dn: string, newParentDn: string): Promise<{ dn: string }> {
  const res = await apiFetch(`/directory/computers/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn, new_parent_dn: newParentDn }),
  });
  if (!res.ok) throw new Error(`Falha ao mover computador (HTTP ${res.status}).`);
  return res.json();
}

export async function deleteComputer(dn: string): Promise<void> {
  const res = await apiFetch(`/directory/computers/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dn }),
  });
  if (!res.ok) throw new Error(`Falha ao excluir computador (HTTP ${res.status}).`);
}


/* Membros de grupo (diretos vs herdados) - Fase 9c */
export type GroupMember = {
  dn: string;
  name: string;
  sam: string | null;
  direct: boolean;
  via: string[];
};

export async function getGroupMembers(groupDn: string): Promise<GroupMember[]> {
  const res = await apiFetch(`/directory/groups/members?group_dn=${encodeURIComponent(groupDn)}`);
  if (!res.ok) throw new Error(`Falha ao buscar membros (HTTP ${res.status}).`);
  return res.json();
}


/* GPOs e Sessoes RDP (Active Directory) - Fase 9c */
export type GPO = {
  name: string | null;
  id: string | null;
  status: string | null;
  created: string | null;
  modified: string | null;
};

export async function listGPOs(): Promise<GPO[]> {
  const res = await apiFetch(`/directory/gpos`);
  if (!res.ok) throw new Error(`Falha ao listar GPOs (HTTP ${res.status}).`);
  return res.json();
}

export type RdpSession = {
  username: string;
  session_name: string;
  state: string;
  idle_time: string;
  logon_time: string;
};

export async function listRdpSessions(): Promise<RdpSession[]> {
  const res = await apiFetch(`/directory/rdp-sessions`);
  if (!res.ok) throw new Error(`Falha ao listar sessoes RDP (HTTP ${res.status}).`);
  return res.json();
}


/* Bulk operations + reset de senha em massa - Fase 9c */
export type BulkResultItem = {
  sam: string;
  ok: boolean;
  error: string | null;
};

export async function bulkEnableUsers(sams: string[], value: boolean): Promise<BulkResultItem[]> {
  const res = await apiFetch(`/directory/bulk/enable`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sams, value }),
  });
  if (!res.ok) throw new Error(`Falha na operacao em massa (HTTP ${res.status}).`);
  return res.json();
}

export async function bulkChangeGroup(sams: string[], groupDn: string, add: boolean): Promise<BulkResultItem[]> {
  const res = await apiFetch(`/directory/bulk/group`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sams, group_dn: groupDn, add }),
  });
  if (!res.ok) throw new Error(`Falha na operacao em massa (HTTP ${res.status}).`);
  return res.json();
}

export async function bulkResetPassword(sams: string[], newPassword: string, mustChange = true): Promise<BulkResultItem[]> {
  const res = await apiFetch(`/directory/bulk/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sams, new_password: newPassword, must_change: mustChange }),
  });
  if (!res.ok) throw new Error(`Falha no reset em massa (HTTP ${res.status}).`);
  return res.json();
}
