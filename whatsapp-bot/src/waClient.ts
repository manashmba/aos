import axios, { AxiosInstance } from "axios";
import { config } from "./config.js";
import { logger } from "./logger.js";

/** Thin client around Meta's WhatsApp Cloud API. No-ops when creds absent. */
export class WhatsAppClient {
  private http: AxiosInstance | null = null;

  constructor() {
    if (config.WA_PHONE_NUMBER_ID && config.WA_ACCESS_TOKEN) {
      this.http = axios.create({
        baseURL: `https://graph.facebook.com/${config.WA_GRAPH_VERSION}`,
        timeout: 15_000,
        headers: { Authorization: `Bearer ${config.WA_ACCESS_TOKEN}` },
      });
    } else {
      logger.warn("WhatsApp creds not configured — running in dry-run mode");
    }
  }

  async sendText(to: string, body: string) {
    const payload = {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "text",
      text: { body: body.slice(0, 4096), preview_url: false },
    };
    if (!this.http) {
      logger.info({ dry_run: true, to, body }, "would send whatsapp text");
      return { dry_run: true, to };
    }
    const { data } = await this.http.post(
      `/${config.WA_PHONE_NUMBER_ID}/messages`,
      payload,
    );
    return data;
  }

  async sendTemplate(to: string, template: string, params: string[] = []) {
    const payload = {
      messaging_product: "whatsapp",
      to,
      type: "template",
      template: {
        name: template,
        language: { code: "en_US" },
        components: params.length
          ? [
              {
                type: "body",
                parameters: params.map((p) => ({ type: "text", text: p })),
              },
            ]
          : [],
      },
    };
    if (!this.http) {
      logger.info({ dry_run: true, to, template, params }, "would send whatsapp template");
      return { dry_run: true, to, template };
    }
    const { data } = await this.http.post(
      `/${config.WA_PHONE_NUMBER_ID}/messages`,
      payload,
    );
    return data;
  }
}

export const wa = new WhatsAppClient();
