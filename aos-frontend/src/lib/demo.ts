/**
 * Demo-mode axios adapter.
 *
 * When enabled (default when VITE_DEMO_MODE !== "0"), every request made by
 * the shared axios client is short-circuited and resolved with plausible
 * mocked data. Great for UI walkthroughs without a live backend.
 */
import type { AxiosAdapter, AxiosRequestConfig, AxiosResponse } from "axios";
import { INTENTS, detectIntent, getReply, type Intent } from "./demoReplies";

export const DEMO_MODE =
  (import.meta.env.VITE_DEMO_MODE ?? "1") !== "0";

// ── Seeded state ────────────────────────────────────────────────────────────

const DEMO_ORG_ID = "org_demo_acme";
const DEMO_USER = {
  id: "usr_demo_admin",
  email: "admin@acme.in",
  name: "Asha Menon",
  role: "admin",
  org_id: DEMO_ORG_ID,
};

let sessionSeq = 0;
const sessions = new Map<string, Array<{ role: string; content: string }>>();

// ── Scripted chat replies ───────────────────────────────────────────────────

interface MockAgentRun {
  agent: string;
  text: string;
  tool_calls: Array<{ tool: string; arguments: Record<string, unknown>; confidence: number }>;
  tool_results: Array<{ tool: string; success: boolean; data?: unknown }>;
  requires_approval: boolean;
  approval_request_id?: string;
  model: string;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
}

function agentReply(message: string): MockAgentRun {
  const intent = detectIntent(message);
  const text = getReply(intent);

  if (intent === "fallback") {
    return {
      agent: "router",
      text,
      tool_calls: [],
      tool_results: [],
      requires_approval: false,
      model: "claude-sonnet-4-6",
      latency_ms: 420,
      tokens_in: 120,
      tokens_out: 60,
    };
  }

  const meta = INTENTS[intent as Exclude<Intent, "fallback">];
  return {
    agent: meta.agent,
    text,
    tool_calls: [{ tool: meta.tool, arguments: meta.toolArgs ?? {}, confidence: meta.confidence }],
    tool_results: [{ tool: meta.tool, success: true }],
    requires_approval: !!meta.requiresApproval,
    approval_request_id: meta.approvalId,
    model: "claude-sonnet-4-6",
    latency_ms: 600 + Math.floor(Math.random() * 600),
    tokens_in: 200 + Math.floor(Math.random() * 120),
    tokens_out: 100 + Math.floor(Math.random() * 100),
  };
}

// ── Seed data for REST endpoints ────────────────────────────────────────────

const ageingSales = {
  current: 1_875_000,
  "1-30": 1_240_000,
  "31-60": 680_000,
  "61-90": 310_000,
  "90+": 145_000,
};

const reorder = [
  { product_id: "SS-6205", product_name: "Ball Bearing 6205", on_hand: 24, reorder_level: 50, suggested_qty: 200 },
  { product_id: "PCB-A11", product_name: "Controller PCB A11", on_hand: 8, reorder_level: 25, suggested_qty: 100 },
  { product_id: "LUB-5L", product_name: "Synthetic Lube 5L", on_hand: 2, reorder_level: 10, suggested_qty: 40 },
  { product_id: "FLT-OS", product_name: "Oil Seal FLT", on_hand: 14, reorder_level: 30, suggested_qty: 80 },
];

const trialBalance = [
  { code: "1000", name: "Cash on Hand",           type: "Asset",      debits: 125000,   credits: 0,        balance: 125000 },
  { code: "1010", name: "Bank — HDFC Current",    type: "Asset",      debits: 4820000,  credits: 0,        balance: 4820000 },
  { code: "1200", name: "Accounts Receivable",    type: "Asset",      debits: 4250000,  credits: 0,        balance: 4250000 },
  { code: "1300", name: "Inventory",              type: "Asset",      debits: 6200000,  credits: 0,        balance: 6200000 },
  { code: "1310", name: "TDS Receivable",         type: "Asset",      debits: 85000,    credits: 0,        balance: 85000 },
  { code: "2000", name: "Accounts Payable",       type: "Liability",  debits: 0,        credits: 3120000,  balance: -3120000 },
  { code: "2300", name: "Output GST",             type: "Liability",  debits: 0,        credits: 612000,   balance: -612000 },
  { code: "2310", name: "TDS Payable",            type: "Liability",  debits: 0,        credits: 48000,    balance: -48000 },
  { code: "2400", name: "PF Payable",             type: "Liability",  debits: 0,        credits: 96000,    balance: -96000 },
  { code: "2500", name: "Salaries Payable",       type: "Liability",  debits: 0,        credits: 720000,   balance: -720000 },
  { code: "3000", name: "Share Capital",          type: "Equity",     debits: 0,        credits: 5000000,  balance: -5000000 },
  { code: "3200", name: "Retained Earnings",      type: "Equity",     debits: 0,        credits: 2890000,  balance: -2890000 },
  { code: "4000", name: "Sales Revenue",          type: "Income",     debits: 0,        credits: 12400000, balance: -12400000 },
  { code: "5000", name: "Cost of Goods Sold",     type: "Expense",    debits: 7100000,  credits: 0,        balance: 7100000 },
  { code: "6100", name: "Salaries & Wages",       type: "Expense",    debits: 980000,   credits: 0,        balance: 980000 },
  { code: "6200", name: "Rent",                   type: "Expense",    debits: 240000,   credits: 0,        balance: 240000 },
];

function seedAuditEvents() {
  const now = Date.now();
  const base = [
    { event_type: "auth.login",                outcome: "success",   entity: { type: "user",    id: "usr_demo_admin", display: "admin@acme.in" } },
    { event_type: "sales.invoice_posted",      outcome: "success",   entity: { type: "invoice", id: "INV-2026-0412",  display: "INV-2026-0412" } },
    { event_type: "procurement.po_created",    outcome: "pending",   entity: { type: "po",      id: "PO-2026-0142",   display: "PO-2026-0142" } },
    { event_type: "finance.payment_received",  outcome: "success",   entity: { type: "receipt", id: "RCP-0901",       display: "RCP-0901" } },
    { event_type: "inventory.goods_received",  outcome: "success",   entity: { type: "grn",     id: "GRN-0322",       display: "GRN-0322" } },
    { event_type: "hr.payroll_run",            outcome: "success",   entity: { type: "payroll", id: "PAY-2026-M01",   display: "Apr-2026" } },
    { event_type: "policy.block",              outcome: "blocked",   entity: { type: "po",      id: "PO-2026-0143",   display: "PO-2026-0143" } },
    { event_type: "approval.granted",          outcome: "success",   entity: { type: "po",      id: "PO-2026-0142",   display: "PO-2026-0142" } },
  ];
  return base.map((e, i) => ({
    id: `evt_${(1000 + i).toString(36)}`,
    timestamp: new Date(now - (base.length - i) * 9 * 60_000).toISOString(),
    actor: { type: i === 6 ? "system" : "user", id: "usr_demo_admin", name: "Asha Menon" },
    ...e,
    previous_hash: i === 0 ? "0".repeat(64) : `hash_${i - 1}`,
    hash: `hash_${i}`,
  }));
}

// ── Adapter ─────────────────────────────────────────────────────────────────

function ok<T>(config: AxiosRequestConfig, data: T, status = 200): AxiosResponse<T> {
  return {
    data,
    status,
    statusText: "OK",
    headers: {},
    config: config as any,
  };
}

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export const demoAdapter: AxiosAdapter = async (config) => {
  const url = (config.url ?? "").replace(/^\/+/, "");
  const method = (config.method ?? "get").toLowerCase();
  await sleep(180 + Math.random() * 220);

  // Auth -------------------------------------------------------------------
  if (url === "auth/login" && method === "post") {
    return ok(config, {
      access_token: "demo.jwt.token",
      refresh_token: "demo.refresh.token",
      token_type: "bearer",
      user: DEMO_USER,
      user_id: DEMO_USER.id,
      role: DEMO_USER.role,
      org_id: DEMO_USER.org_id,
      org_name: "Acme Traders Pvt Ltd",
    });
  }

  // Conversation -----------------------------------------------------------
  if (url === "conversation/sessions" && method === "post") {
    const id = `sess_demo_${++sessionSeq}`;
    sessions.set(id, []);
    return ok(config, { session_id: id, id, channel: "web", started_at: new Date().toISOString() });
  }

  const convoMsgMatch = url.match(/^conversation\/sessions\/([^/]+)\/messages$/);
  if (convoMsgMatch && method === "post") {
    const body = typeof config.data === "string" ? JSON.parse(config.data) : config.data ?? {};
    return ok(config, agentReply(String(body.message ?? "")));
  }

  const convoHistMatch = url.match(/^conversation\/sessions\/([^/]+)\/history$/);
  if (convoHistMatch && method === "get") {
    return ok(config, sessions.get(convoHistMatch[1]) ?? []);
  }

  if (/^conversation\/sessions\/[^/]+\/end$/.test(url) && method === "post") {
    return ok(config, { ended: true });
  }

  // Agents -----------------------------------------------------------------
  if (url === "agents" && method === "get") {
    return ok(config, [
      { name: "finance", description: "Finance & accounting", tools: 8 },
      { name: "procurement", description: "Vendors, POs, GRN", tools: 6 },
      { name: "sales", description: "Customers, orders, credit", tools: 5 },
      { name: "inventory", description: "Stock, reorder, dispatch", tools: 7 },
      { name: "hr", description: "Employees, leave, payroll", tools: 6 },
      { name: "manufacturing", description: "BOM, production orders", tools: 4 },
    ]);
  }

  if (url === "agents/route" && method === "post") {
    return ok(config, { agent: "finance", confidence: 0.89 });
  }

  if (url === "agents/run" && method === "post") {
    const body = typeof config.data === "string" ? JSON.parse(config.data) : config.data ?? {};
    return ok(config, agentReply(String(body.message ?? "")));
  }

  // Finance ----------------------------------------------------------------
  if (url === "finance/trial-balance" && method === "get") {
    return ok(config, trialBalance);
  }
  if (url === "finance/ageing" && method === "get") {
    return ok(config, ageingSales);
  }

  // Procurement ------------------------------------------------------------
  if (url === "procurement/purchase-orders" && method === "get") {
    return ok(config, [
      { id: "PO-2026-0140", vendor: "Acme Bearings",  total: 148000, status: "approved" },
      { id: "PO-2026-0141", vendor: "NovaCorp",       total: 92000,  status: "approved" },
      { id: "PO-2026-0142", vendor: "Acme Bearings",  total: 59000,  status: "pending_approval" },
    ]);
  }

  // Sales ------------------------------------------------------------------
  if (url === "sales/customers" && method === "get") {
    return ok(config, [
      { id: "cus_bharat", name: "Bharat Tools",   credit_limit: 1000000, outstanding: 840000 },
      { id: "cus_nova",   name: "NovaCorp",       credit_limit: 500000,  outstanding: 410000 },
      { id: "cus_relay",  name: "RelayTech",      credit_limit: 300000,  outstanding: 275000 },
    ]);
  }
  const creditMatch = url.match(/^sales\/customers\/([^/]+)\/credit-status$/);
  if (creditMatch && method === "get") {
    return ok(config, { customer_id: creditMatch[1], available: 160000, utilisation_pct: 84 });
  }

  // Inventory --------------------------------------------------------------
  if (url === "inventory/reorder-suggestions" && method === "get") {
    return ok(config, reorder);
  }
  const stockMatch = url.match(/^inventory\/stock\/([^/]+)$/);
  if (stockMatch && method === "get") {
    return ok(config, { product_id: stockMatch[1], on_hand: 42, reserved: 8, available: 34 });
  }

  // Audit ------------------------------------------------------------------
  if (url === "audit/events" && method === "get") {
    return ok(config, seedAuditEvents());
  }
  if (url === "audit/verify" && method === "get") {
    return ok(config, { verified: true, checked: 8, broken_at: null });
  }

  // Health / fallbacks -----------------------------------------------------
  if (url === "health" && method === "get") {
    return ok(config, { status: "ok", mode: "demo" });
  }

  return ok(config, { demo: true, message: `No demo fixture for ${method.toUpperCase()} /${url}` }, 200);
};
