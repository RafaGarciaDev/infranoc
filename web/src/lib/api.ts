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
