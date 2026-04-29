const BASE = "/api";

export interface Alert {
  id: number;
  listing_id: string;
  title: string;
  price: number;
  url: string;
  score: number;
  expected_profit: number;
  rolling_average: number;
  price_delta_percent: number;
  location: string | null;
  images_count: number;
  age_minutes: number | null;
  alerted_at: string;
  user_action: string | null;
}

export interface PriceHistoryEntry {
  price: number;
  seen_at: string;
}

export interface SearchProfile {
  id?: number;
  name: string;
  query: string;
  category_id?: string | null;
  max_price?: number | null;
  min_price?: number | null;
  active: boolean;
  custom_threshold?: number | null;
}

export interface BlacklistEntry {
  seller_id: string;
  reason?: string | null;
  added_at?: string;
}

export interface AppConfig {
  MAX_BUDGET_EUR: number;
  MIN_PROFIT_EUR: number;
  PRICE_THRESHOLD_PERCENT: number;
  ROLLING_AVERAGE_DAYS: number;
  SCRAPE_INTERVAL_MINUTES: number;
  MIN_LISTING_IMAGES: number;
  ALERT_COOLDOWN_HOURS: number;
  MAX_SELLER_LISTINGS: number;
  LOG_LEVEL: string;
  scraper_paused: boolean;
}

export interface StatsData {
  today_seen: number;
  today_alerts: number;
  week_alerts: number;
  total_alerts: number;
  best_margin_today: number | null;
  total_profit_interested: number;
  top_search_terms: Array<{ search_term: string; cnt: number }>;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  alerts: {
    list: (params: {
      page?: number;
      page_size?: number;
      min_score?: number;
      date_from?: string;
      date_to?: string;
      user_action?: string;
    } = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
      });
      return request<{ alerts: Alert[]; page: number; page_size: number }>(
        `/alerts?${qs}`
      );
    },
    get: (id: number) => request<Alert>(`/alerts/${id}`),
    updateAction: (id: number, user_action: string) =>
      request<{ ok: boolean }>(`/alerts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ user_action }),
      }),
  },

  priceHistory: {
    get: (searchTerm: string, days = 30) =>
      request<{ search_term: string; history: PriceHistoryEntry[] }>(
        `/price-history/${encodeURIComponent(searchTerm)}?days=${days}`
      ),
  },

  profiles: {
    list: () => request<{ profiles: SearchProfile[] }>("/profiles"),
    create: (p: SearchProfile) =>
      request<{ id: number }>("/profiles", {
        method: "POST",
        body: JSON.stringify(p),
      }),
    update: (id: number, p: Partial<SearchProfile>) =>
      request<{ ok: boolean }>(`/profiles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(p),
      }),
    delete: (id: number) =>
      request<{ ok: boolean }>(`/profiles/${id}`, { method: "DELETE" }),
  },

  stats: {
    get: () => request<StatsData>("/stats"),
  },

  config: {
    get: () => request<AppConfig>("/config"),
    update: (updates: Partial<AppConfig>) =>
      request<{ ok: boolean; updated: string[] }>("/config", {
        method: "PATCH",
        body: JSON.stringify(updates),
      }),
  },

  blacklist: {
    list: () => request<{ blacklist: BlacklistEntry[] }>("/blacklist"),
    add: (entry: BlacklistEntry) =>
      request<{ ok: boolean }>("/blacklist", {
        method: "POST",
        body: JSON.stringify(entry),
      }),
    remove: (sellerId: string) =>
      request<{ ok: boolean }>(`/blacklist/${encodeURIComponent(sellerId)}`, {
        method: "DELETE",
      }),
  },
};
