// frontend/src/api.ts

export interface Position {
  id: number;
  ticker: string;
  entry_price: number;
  quantity: number;
  stop_loss: number;
  entry_date: string;
  current_price: number | null;
  pct_change: number | null;
  pnl_pct: number | null;
}

export interface RecommendationResult {
  ticker: string;
  score: number;
  current_price: number | null;
  pct_change: number | null;
  pct_from_52w_high: number;
  relative_strength: number;
  avg_dollar_volume: number;
}

export interface RecommendationsResponse {
  run_date: string | null;
  results: RecommendationResult[];
}

export interface WatchedIndex {
  symbol: string;
  display_name: string;
  current_price: number | null;
  pct_change: number | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function login(password: string): Promise<{ ok: boolean }> {
  return apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return apiFetch("/api/auth/logout", { method: "POST" });
}

export function getPortfolio(): Promise<Position[]> {
  return apiFetch("/api/portfolio");
}

export function buyPosition(
  ticker: string,
  entryPrice: number,
  quantity: number,
  stopLoss: number
): Promise<{ id: number }> {
  return apiFetch("/api/portfolio", {
    method: "POST",
    body: JSON.stringify({
      ticker,
      entry_price: entryPrice,
      quantity,
      stop_loss: stopLoss,
    }),
  });
}

export function addToPosition(
  id: number,
  quantity: number,
  price: number
): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}/add`, {
    method: "POST",
    body: JSON.stringify({ quantity, price }),
  });
}

export function updateStopLoss(id: number, stopLoss: number): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ stop_loss: stopLoss }),
  });
}

export function sellPosition(id: number): Promise<{ ok: boolean }> {
  return apiFetch(`/api/portfolio/${id}/sell`, { method: "POST" });
}

export function getRecommendations(): Promise<RecommendationsResponse> {
  return apiFetch("/api/recommendations");
}

export function getIndices(): Promise<WatchedIndex[]> {
  return apiFetch("/api/indices");
}

export function addIndex(symbol: string, displayName: string): Promise<{ ok: boolean }> {
  return apiFetch("/api/indices", {
    method: "POST",
    body: JSON.stringify({ symbol, display_name: displayName }),
  });
}

export function removeIndex(symbol: string): Promise<{ ok: boolean }> {
  return apiFetch(`/api/indices/${symbol}`, { method: "DELETE" });
}
