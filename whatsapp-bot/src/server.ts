import express from "express";
import pinoHttp from "pino-http";
import { config } from "./config.js";
import { logger } from "./logger.js";
import { webhookRouter } from "./routes/webhook.js";
import { notifyRouter } from "./routes/notify.js";

const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(pinoHttp({ logger }));

app.get("/health", (_req, res) => res.json({ status: "ok", service: "aos-whatsapp-bot" }));

app.use(webhookRouter);
app.use(notifyRouter);

app.listen(config.PORT, () => {
  logger.info({ port: config.PORT }, "aos whatsapp bot listening");
});
