/**
 * Cliente WebSocket do Dashboard NOC (Fase 6).
 *
 * - Conecta em ws(s)://<host>/dashboard/ws?token=<jwt>
 * - Reconexao exponencial (1s, 2s, 4s...) ate 30s de teto
 * - Apos 3 falhas consecutivas, ativa fallback via HTTP polling
 *   (/dashboard/overview + /dashboard/plant) a cada 10s
 * - Retorna funcao de cleanup pra ser usada no return do useEffect
 */
import { apiFetch, getToken } from "./api";

export type NocStatus = "connecting" | "ok" | "reconnecting" | "polling" | "error";

export type NocPayload = {
  oee: Array<{ line: number; name: string; value: number; stopped: boolean }>;
  assets_up: number;
  assets_down: number;
  alerts_by_severity: Record<string, number>;
  alerts_active_total: number;
  top_alerts: Array<{
    id: string;
    summary: string | null;
    asset: string | null;
    severity: string;
    categoria: string | null;
    impacto_negocio: string | null;
    starts_at: string;
  }>;
  output_units: number;
  top_ti_alerts: Array<{
    id: string;
    summary: string | null;
    asset: string | null;
    severity: string;
    impacto_negocio: string | null;
    starts_at: string;
  }>;
  plant: Array<{
    key: string;
    label: string;
    severity: "ok" | "info" | "warning" | "high" | "critical";
    count: number;
  }>;
};

type Options = {
  onData: (payload: NocPayload) => void;
  onStatus?: (status: NocStatus) => void;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api";
const POLL_INTERVAL_MS = 10_000;
const MAX_WS_RETRIES = 3;
const MAX_BACKOFF_MS = 30_000;

function buildWsUrl(token: string): string {
  const wsBase = API_URL.replace(/^http/i, "ws");
  return `${wsBase}/dashboard/ws?token=${encodeURIComponent(token)}`;
}

async function fetchOverviewAndPlant(): Promise<NocPayload | null> {
  try {
    const [ovRes, plRes] = await Promise.all([
      apiFetch("/dashboard/overview"),
      apiFetch("/dashboard/plant"),
    ]);
    if (!ovRes.ok || !plRes.ok) return null;
    const overview = await ovRes.json();
    const plant = await plRes.json();
    return { ...overview, plant: plant.areas } as NocPayload;
  } catch {
    return null;
  }
}

export function connectNoc({ onData, onStatus }: Options): () => void {
  let ws: WebSocket | null = null;
  let closedByUser = false;
  let retries = 0;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const setStatus = (s: NocStatus) => onStatus?.(s);

  function startPolling() {
    if (pollTimer) return;
    setStatus("polling");
    const tick = async () => {
      const data = await fetchOverviewAndPlant();
      if (data) onData(data);
    };
    void tick();
    pollTimer = setInterval(tick, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function scheduleReconnect() {
    if (closedByUser) return;
    retries += 1;
    if (retries >= MAX_WS_RETRIES) {
      startPolling();
      return;
    }
    const delay = Math.min(1_000 * 2 ** (retries - 1), MAX_BACKOFF_MS);
    setStatus("reconnecting");
    reconnectTimer = setTimeout(connect, delay);
  }

  function connect() {
    if (closedByUser) return;
    const token = getToken();
    if (!token) {
      setStatus("error");
      return;
    }
    setStatus("connecting");
    try {
      ws = new WebSocket(buildWsUrl(token));
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      retries = 0;
      stopPolling();
      setStatus("ok");
    };
    ws.onmessage = (ev) => {
      try {
        onData(JSON.parse(ev.data) as NocPayload);
      } catch {
        /* payload malformado - ignora esse frame */
      }
    };
    ws.onerror = () => {
      try { ws?.close(); } catch { /* noop */ }
    };
    ws.onclose = () => {
      ws = null;
      if (!closedByUser) scheduleReconnect();
    };
  }

  connect();

  return () => {
    closedByUser = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    stopPolling();
    try { ws?.close(); } catch { /* noop */ }
  };
}