import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./locales/en.json";
import hi from "./locales/hi.json";
import ta from "./locales/ta.json";
import bn from "./locales/bn.json";
import mr from "./locales/mr.json";
import gu from "./locales/gu.json";
import te from "./locales/te.json";
import kn from "./locales/kn.json";

export type LangCode = "en" | "hi" | "ta" | "bn" | "mr" | "gu" | "te" | "kn";

export interface LanguageMeta {
  code: LangCode;
  native: string;   // Shown in pickers — always native script
  english: string;  // Shown as secondary hint
  locale: string;   // BCP-47 tag for Intl.* APIs
}

export const LANGUAGES: LanguageMeta[] = [
  { code: "en", native: "English",   english: "English",   locale: "en-IN" },
  { code: "hi", native: "हिन्दी",     english: "Hindi",     locale: "hi-IN" },
  { code: "bn", native: "বাংলা",     english: "Bengali",   locale: "bn-IN" },
  { code: "ta", native: "தமிழ்",     english: "Tamil",     locale: "ta-IN" },
  { code: "te", native: "తెలుగు",    english: "Telugu",    locale: "te-IN" },
  { code: "mr", native: "मराठी",      english: "Marathi",   locale: "mr-IN" },
  { code: "gu", native: "ગુજરાતી",   english: "Gujarati",  locale: "gu-IN" },
  { code: "kn", native: "ಕನ್ನಡ",      english: "Kannada",   locale: "kn-IN" },
];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
      ta: { translation: ta },
      bn: { translation: bn },
      mr: { translation: mr },
      gu: { translation: gu },
      te: { translation: te },
      kn: { translation: kn },
    },
    fallbackLng: "en",
    supportedLngs: LANGUAGES.map((l) => l.code),
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator", "htmlTag"],
      lookupLocalStorage: "aos-lang",
      caches: ["localStorage"],
    },
  });

// Keep <html lang> + direction in sync for screen readers & typography.
function syncHtmlLang(lng: string) {
  if (typeof document === "undefined") return;
  document.documentElement.lang = lng;
  document.documentElement.dir = "ltr";
  document.documentElement.dataset.lang = lng;
}
syncHtmlLang(i18n.language);
i18n.on("languageChanged", syncHtmlLang);

// Expose for debugging / automated preview checks.
if (typeof window !== "undefined") (window as any).__i18n = i18n;

export default i18n;
