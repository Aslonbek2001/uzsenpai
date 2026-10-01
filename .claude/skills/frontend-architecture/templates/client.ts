// shared/api/client.ts — one client for the whole app.
import i18n from "i18next";

export type ApiErrorBody = { error: { code: string; params?: Record<string, unknown> } };

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
    public readonly params: Record<string, unknown> = {},
  ) {
    super(code);
  }
}

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";
let accessToken: string | null = null;
export const setAccessToken = (token: string | null) => {
  accessToken = token;
};

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept-Language", i18n.language || "uz");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const body = data as Partial<ApiErrorBody> | null;
    throw new ApiError(body?.error?.code ?? "common.unknown", res.status, body?.error?.params ?? {});
  }
  return data as T;
}

export const get = <T>(path: string, signal?: AbortSignal) => api<T>(path, { signal });
export const send = <T>(method: "POST" | "PUT" | "PATCH" | "DELETE", path: string, body?: unknown) =>
  api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });

/** Translate an error for display. Namespace syntax `errors:<code>` — keys inside errors.json have no prefix. */
export function errorMessage(t: (k: string, o?: Record<string, unknown>) => string, err: unknown): string {
  if (err instanceof ApiError) return t(`errors:${err.code}`, { ...err.params, defaultValue: t("errors:common.unknown") });
  return t("errors:common.network");
}
