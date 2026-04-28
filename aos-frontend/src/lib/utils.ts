import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import i18n from "@/i18n";
import { LANGUAGES, type LangCode } from "@/i18n";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Locale-aware currency formatter. Uses `Intl.NumberFormat` with the active
 * BCP-47 tag (e.g. `hi-IN`) so lakh/crore grouping stays correct in every
 * Indian language — but forces `numberingSystem: "latn"` so digits stay
 * Latin (accounting convention; Devanagari digits would confuse finance
 * users who read statements in English).
 */
export function formatINR(amount: number | string): string {
  const n = typeof amount === "string" ? Number(amount) : amount;
  // Pin grouping to en-IN so lakh/crore formatting (42,50,000) is consistent
  // across every UI language. Some locales (mr-IN, kn-IN) default to Western
  // grouping in ICU, which is wrong for Indian accounting.
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    // @ts-expect-error — `numberingSystem` is valid per ECMA-402
    numberingSystem: "latn",
  }).format(Number.isFinite(n) ? n : 0);
}

export function formatDate(d: string | Date): string {
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleDateString(currentLocale(), {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

export function formatTime(d: string | Date): string {
  const date = typeof d === "string" ? new Date(d) : d;
  return date.toLocaleString(currentLocale(), {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function currentLocale(): string {
  const lang = (i18n.resolvedLanguage ?? "en") as LangCode;
  return LANGUAGES.find((l) => l.code === lang)?.locale ?? "en-IN";
}
