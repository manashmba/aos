import axios, { AxiosInstance } from "axios";
import { useAuthStore } from "@/store/auth";
import { DEMO_MODE, demoAdapter } from "@/lib/demo";
import i18n, { LANGUAGES, type LangCode } from "@/i18n";

const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  ...(DEMO_MODE ? { adapter: demoAdapter } : {}),
});

export { DEMO_MODE };

/** Current BCP-47 tag for outgoing requests (e.g. `hi-IN`). */
function currentBcp47(): string {
  const code = (i18n.resolvedLanguage ?? "en") as LangCode;
  return LANGUAGES.find((l) => l.code === code)?.locale ?? "en-IN";
}

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Negotiate response language with the backend on every call. The backend's
  // LanguageMiddleware reads X-Language first, then Accept-Language.
  const lng = currentBcp47();
  config.headers["Accept-Language"] = lng;
  config.headers["X-Language"] = lng.split("-")[0];
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  },
);

// ---- Typed helpers ---------------------------------------------------------

export interface RouteRequest {
  message: string;
  locale?: string;
}

export interface RunAgentRequest {
  message: string;
  session_id?: string;
  agent_name?: string;
  channel?: string;
}

export interface AgentRunResult {
  agent: string;
  text: string;
  tool_calls: Array<{ tool: string; arguments: Record<string, unknown>; confidence: number }>;
  tool_results: Array<{ tool: string; success: boolean; data?: unknown; error?: string }>;
  requires_approval: boolean;
  approval_request_id?: string;
  model: string;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
}

export const ConversationAPI = {
  createSession: (channel = "web") =>
    api.post("/conversation/sessions", {
      channel,
      // Belt-and-suspenders: send the language in the body too, so a later
      // turn that lands on a backend with a different middleware order still
      // gets the right session-default language.
      language: i18n.resolvedLanguage ?? "en",
    }),
  sendMessage: (sessionId: string, message: string) =>
    api.post<AgentRunResult>(`/conversation/sessions/${sessionId}/messages`, {
      message,
      language: i18n.resolvedLanguage ?? "en",
    }),
  getHistory: (sessionId: string) =>
    api.get(`/conversation/sessions/${sessionId}/history`),
  endSession: (sessionId: string) =>
    api.post(`/conversation/sessions/${sessionId}/end`),
};

export const AgentsAPI = {
  list: () => api.get("/agents"),
  route: (req: RouteRequest) => api.post("/agents/route", req),
  run: (req: RunAgentRequest) => api.post<AgentRunResult>("/agents/run", req),
};

export const FinanceAPI = {
  trialBalance: (as_of?: string) => api.get("/finance/trial-balance", { params: { as_of } }),
  ageing: (invoice_type = "sales") =>
    api.get("/finance/ageing", { params: { invoice_type } }),
};

export const ProcurementAPI = {
  listPOs: () => api.get("/procurement/purchase-orders"),
  createPO: (body: unknown) => api.post("/procurement/purchase-orders", body),
};

export const SalesAPI = {
  listCustomers: () => api.get("/sales/customers"),
  creditStatus: (id: string) => api.get(`/sales/customers/${id}/credit-status`),
};

export const InventoryAPI = {
  stock: (productId: string, warehouseId?: string) =>
    api.get(`/inventory/stock/${productId}`, { params: { warehouse_id: warehouseId } }),
  reorderSuggestions: () => api.get("/inventory/reorder-suggestions"),
};

export const AuditAPI = {
  listEvents: (params: Record<string, unknown> = {}) => api.get("/audit/events", { params }),
  verify: () => api.get("/audit/verify"),
};
