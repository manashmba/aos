import { Router, Request, Response } from "express";
import { z } from "zod";
import { wa } from "../waClient.js";
import { logger } from "../logger.js";
import { config } from "../config.js";

export const notifyRouter = Router();

/**
 * Outbound notification endpoint used by the AOS backend to push
 * approval requests / alerts to a user on WhatsApp.
 *
 * Auth: shared secret via `Authorization: Bearer <AOS_SERVICE_TOKEN>`.
 */
const TextBody = z.object({
  to: z.string().min(5),
  body: z.string().min(1).max(4096),
});
const TemplateBody = z.object({
  to: z.string().min(5),
  template: z.string().min(1),
  params: z.array(z.string()).default([]),
});

function auth(req: Request, res: Response): boolean {
  if (!config.AOS_SERVICE_TOKEN) return true; // open in dev
  const header = req.header("authorization") ?? "";
  if (header === `Bearer ${config.AOS_SERVICE_TOKEN}`) return true;
  res.status(401).json({ error: "unauthorized" });
  return false;
}

notifyRouter.post("/notify/text", async (req, res) => {
  if (!auth(req, res)) return;
  const parsed = TextBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "bad_request", detail: parsed.error.issues });
    return;
  }
  try {
    const r = await wa.sendText(parsed.data.to, parsed.data.body);
    res.json({ ok: true, provider: r });
  } catch (err: any) {
    logger.error({ err: err?.message }, "notify text failed");
    res.status(502).json({ ok: false, error: err?.message ?? "provider_error" });
  }
});

notifyRouter.post("/notify/template", async (req, res) => {
  if (!auth(req, res)) return;
  const parsed = TemplateBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "bad_request", detail: parsed.error.issues });
    return;
  }
  try {
    const r = await wa.sendTemplate(parsed.data.to, parsed.data.template, parsed.data.params);
    res.json({ ok: true, provider: r });
  } catch (err: any) {
    logger.error({ err: err?.message }, "notify template failed");
    res.status(502).json({ ok: false, error: err?.message ?? "provider_error" });
  }
});
