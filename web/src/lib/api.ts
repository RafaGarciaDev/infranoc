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
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    body,
  });
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

/* ---------------------------------------------------------
 * Alertas (Fase 3 - Bloco 5)
 * --------------------------------------------------------- */
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
  status_history: AlertStatusChange[];
};

export type AlertFilter = {
  status?: AlertStatus;
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