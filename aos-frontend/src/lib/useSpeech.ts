import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { LANGUAGES, type LangCode } from "@/i18n";

// Cross-vendor SpeechRecognition handle (Webkit prefix in Chrome on Windows).
type SR = typeof window extends { SpeechRecognition: infer T } ? T : any;
function getCtor(): SR | null {
  if (typeof window === "undefined") return null;
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
}

interface SpeechState {
  supported: boolean;
  listening: boolean;
  transcript: string;
  error: string | null;
  start: () => void;
  stop: () => void;
}

/**
 * Thin wrapper over Web Speech API. Picks the BCP-47 locale of the active
 * UI language so a Hindi user gets Hindi recognition, Tamil user gets Tamil
 * etc. Stops automatically on a final result so users don't have to click
 * twice — matches the WhatsApp voice-note mental model.
 */
export function useSpeech(onFinal?: (text: string) => void): SpeechState {
  const { i18n } = useTranslation();
  const Ctor = getCtor();
  const supported = !!Ctor;

  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<any>(null);

  useEffect(() => {
    if (!Ctor) return;
    const rec = new (Ctor as any)();
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = bcp47For(i18n.resolvedLanguage as LangCode);

    rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) {
          const final = res[0].transcript.trim();
          setTranscript(final);
          onFinal?.(final);
        } else {
          interim += res[0].transcript;
        }
      }
      if (interim) setTranscript(interim);
    };
    rec.onerror = (e: any) => {
      setError(e.error || "speech-error");
      setListening(false);
    };
    rec.onend = () => setListening(false);

    recRef.current = rec;
    return () => {
      try {
        rec.abort();
      } catch {
        /* ignore */
      }
    };
  }, [Ctor, i18n.resolvedLanguage, onFinal]);

  function start() {
    if (!recRef.current) return;
    setError(null);
    setTranscript("");
    try {
      recRef.current.start();
      setListening(true);
    } catch {
      // Already started — ignore.
    }
  }
  function stop() {
    try {
      recRef.current?.stop();
    } catch {
      /* ignore */
    }
  }

  return { supported, listening, transcript, error, start, stop };
}

function bcp47For(code: LangCode): string {
  return LANGUAGES.find((l) => l.code === code)?.locale ?? "en-IN";
}
