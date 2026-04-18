import "dotenv/config";
import { z } from "zod";

const Env = z.object({
  WA_VERIFY_TOKEN: z.string().min(1),
  WA_PHONE_NUMBER_ID: z.string().optional(),
  WA_ACCESS_TOKEN: z.string().optional(),
  WA_GRAPH_VERSION: z.string().default("v20.0"),
  AOS_API_URL: z.string().default("http://localhost:8000/api/v1"),
  AOS_SERVICE_TOKEN: z.string().optional(),
  PORT: z.coerce.number().default(3001),
  REDIS_URL: z.string().optional(),
  LOG_LEVEL: z.string().default("info"),
});

export const config = Env.parse(process.env);
export type Config = typeof config;
