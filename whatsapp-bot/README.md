# AOS WhatsApp Bot

Express + TypeScript bridge between WhatsApp Business Cloud API and
the AOS backend's conversation API.

## Responsibilities

- Verify Meta webhook handshake (`GET /webhook`)
- Receive inbound WhatsApp messages (`POST /webhook`), map the sender's
  phone to a persistent AOS conversation session, forward the text to
  `/conversation/sessions/{id}/messages`, and send the assistant's
  response back via the Cloud API.
- Expose outbound `POST /notify/text` and `POST /notify/template`
  endpoints for the backend to send approval prompts, payment alerts,
  GRN reminders, etc.

## Run

```bash
cp .env.example .env   # fill in WA_* and AOS_* vars
npm install
npm run dev
```

## Session mapping

Phone → AOS session id is stored in Redis (if `REDIS_URL` is set) with a
24 h TTL, otherwise in an in-memory map.

## Auth

Outbound `/notify/*` endpoints require `Authorization: Bearer $AOS_SERVICE_TOKEN`.
