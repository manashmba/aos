import Redis from "ioredis";
import { config } from "./config.js";
import { logger } from "./logger.js";

/**
 * Maps a WhatsApp phone (E.164) to an AOS conversation session id.
 * Backed by Redis when REDIS_URL is configured, else in-memory (per-process).
 */
interface Store {
  get(phone: string): Promise<string | null>;
  set(phone: string, sessionId: string, ttlSeconds?: number): Promise<void>;
  del(phone: string): Promise<void>;
}

class MemoryStore implements Store {
  private m = new Map<string, { sessionId: string; expiresAt: number }>();
  async get(phone: string) {
    const e = this.m.get(phone);
    if (!e) return null;
    if (e.expiresAt < Date.now()) {
      this.m.delete(phone);
      return null;
    }
    return e.sessionId;
  }
  async set(phone: string, sessionId: string, ttl = 60 * 60 * 24) {
    this.m.set(phone, { sessionId, expiresAt: Date.now() + ttl * 1000 });
  }
  async del(phone: string) {
    this.m.delete(phone);
  }
}

class RedisStore implements Store {
  constructor(private r: Redis) {}
  private key(p: string) {
    return `wa:session:${p}`;
  }
  async get(phone: string) {
    return this.r.get(this.key(phone));
  }
  async set(phone: string, sessionId: string, ttl = 60 * 60 * 24) {
    await this.r.set(this.key(phone), sessionId, "EX", ttl);
  }
  async del(phone: string) {
    await this.r.del(this.key(phone));
  }
}

export const sessions: Store = (() => {
  if (config.REDIS_URL) {
    try {
      const r = new Redis(config.REDIS_URL, { lazyConnect: true });
      r.connect().catch((e) => logger.warn({ err: e }, "redis connect failed"));
      return new RedisStore(r);
    } catch (e) {
      logger.warn({ err: e }, "redis init failed — falling back to memory store");
    }
  }
  return new MemoryStore();
})();
