import axios, { AxiosInstance } from "axios";
import { config } from "./config.js";

const http: AxiosInstance = axios.create({
  baseURL: config.AOS_API_URL,
  timeout: 60_000,
  headers: config.AOS_SERVICE_TOKEN
    ? { Authorization: `Bearer ${config.AOS_SERVICE_TOKEN}` }
    : {},
});

export interface AosAgentResult {
  agent: string;
  text: string;
  requires_approval?: boolean;
  approval_request_id?: string;
  tool_calls?: Array<{ tool: string; arguments: unknown }>;
}

export const aos = {
  async createSession(channel: string = "whatsapp") {
    const { data } = await http.post("/conversation/sessions", { channel });
    return data;
  },
  async sendMessage(sessionId: string, message: string): Promise<AosAgentResult> {
    const { data } = await http.post<AosAgentResult>(
      `/conversation/sessions/${sessionId}/messages`,
      { message },
    );
    return data;
  },
};
