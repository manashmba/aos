import { Router, Request, Response } from "express";
import { config } from "../config.js";
import { logger } from "../logger.js";
import { aos } from "../aosClient.js";
import { wa } from "../waClient.js";
import { sessions } from "../sessionMap.js";

export const webhookRouter = Router();

/** Meta verification challenge. */
webhookRouter.get("/webhook", (req: Request, res: Response) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];
  if (mode === "subscribe" && token === config.WA_VERIFY_TOKEN) {
    res.status(200).send(String(challenge));
    return;
  }
  res.sendStatus(403);
});

/** Inbound message delivery. */
webhookRouter.post("/webhook", async (req: Request, res: Response) => {
  res.sendStatus(200); // Ack fast — do work async
  try {
    await handlePayload(req.body);
  } catch (err) {
    logger.error({ err }, "webhook handler failed");
  }
});

async function handlePayload(body: any) {
  const entries = body?.entry ?? [];
  for (const entry of entries) {
    for (const change of entry?.changes ?? []) {
      const value = change?.value;
      for (const msg of value?.messages ?? []) {
        await handleInbound(msg, value?.contacts?.[0]);
      }
    }
  }
}

async function handleInbound(msg: any, contact: any) {
  const from: string = msg.from;
  const type: string = msg.type;
  const text =
    type === "text"
      ? msg.text?.body
      : type === "interactive"
        ? msg.interactive?.button_reply?.title || msg.interactive?.list_reply?.title
        : null;

  if (!text) {
    logger.info({ from, type }, "unsupported message type — ignoring");
    return;
  }

  let sessionId = await sessions.get(from);
  if (!sessionId) {
    const s = await aos.createSession("whatsapp");
    sessionId = s.session_id ?? s.id;
    await sessions.set(from, sessionId!);
    logger.info({ from, sessionId }, "created aos session");
  }

  try {
    const result = await aos.sendMessage(sessionId!, text);
    let reply = result.text ?? "(no response)";
    if (result.requires_approval) {
      reply += `\n\n🕒 Pending approval (ref: ${result.approval_request_id ?? "?"})`;
    }
    await wa.sendText(from, reply);
  } catch (err: any) {
    logger.error({ err: err?.message, from }, "aos call failed");
    await wa
      .sendText(from, "Sorry, AOS is unavailable right now. Please try again shortly.")
      .catch(() => {});
  }
}
