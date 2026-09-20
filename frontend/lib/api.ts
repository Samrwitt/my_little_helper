const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getTokens() {
  if (typeof window === "undefined") return { access: null, refresh: null };
  return {
    access: localStorage.getItem("access_token"),
    refresh: localStorage.getItem("refresh_token"),
  };
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshAccessToken(): Promise<string | null> {
  const { refresh } = getTokens();
  if (!refresh) return null;
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true
): Promise<T> {
  const { access } = getTokens();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) return api<T>(path, options, false);
    throw new ApiError(401, "Unauthorized");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const authApi = {
  register: (payload: { email: string; password: string; full_name?: string }) =>
    api("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: async (email: string, password: string) => {
    const data = await api<{ access_token: string; refresh_token: string }>(
      "/auth/login/json",
      { method: "POST", body: JSON.stringify({ email, password }) }
    );
    setTokens(data.access_token, data.refresh_token);
    return data;
  },
  me: () => api<import("@/types").User>("/auth/me"),
  logout: () => clearTokens(),
};

export const profileApi = {
  get: () => api<import("@/types").Profile>("/profile"),
  update: (payload: Partial<import("@/types").Profile>) =>
    api<import("@/types").Profile>("/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
};

export const dashboardApi = {
  get: () => api<import("@/types").Dashboard>("/dashboard"),
};

export const scholarshipsApi = {
  list: (params: Record<string, string | undefined> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) q.set(k, v);
    });
    const qs = q.toString();
    return api<{ items: import("@/types").Scholarship[]; total: number }>(
      `/scholarships${qs ? `?${qs}` : ""}`
    );
  },
  get: (id: string) => api<import("@/types").Scholarship>(`/scholarships/${id}`),
  save: (id: string) => api(`/scholarships/${id}/save`, { method: "POST" }),
};

export const applicationsApi = {
  list: () => api<import("@/types").Application[]>("/applications"),
  create: (scholarship_id: string, status = "saved") =>
    api<import("@/types").Application>("/applications", {
      method: "POST",
      body: JSON.stringify({ scholarship_id, status }),
    }),
  update: (id: string, payload: { status?: string; notes?: string }) =>
    api<import("@/types").Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  updateDocument: (appId: string, docId: string, is_complete: boolean) =>
    api<import("@/types").Application>(`/applications/${appId}/documents/${docId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_complete }),
    }),
};

export const notificationsApi = {
  list: () => api<import("@/types").Notification[]>("/notifications"),
  markRead: (id: string) =>
    api(`/notifications/${id}/read`, { method: "PATCH" }),
};

export const agentApi = {
  discover: (max_results = 10) =>
    api("/agent/discover", {
      method: "POST",
      body: JSON.stringify({ max_results }),
    }),
  runs: () => api("/agent/runs"),
};
