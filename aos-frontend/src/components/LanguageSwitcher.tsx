import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Globe, ChevronDown } from "lucide-react";
import { LANGUAGES, type LangCode } from "@/i18n";
import { cn } from "@/lib/utils";

interface Props {
  variant?: "inline" | "ghost";
  align?: "start" | "end";
}

/**
 * Language switcher — shows native-script labels only, with the English
 * name as a secondary hint. Persists via i18next's localStorage detector.
 */
export function LanguageSwitcher({ variant = "ghost", align = "end" }: Props) {
  const { i18n, t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const active = LANGUAGES.find((l) => l.code === i18n.resolvedLanguage) ?? LANGUAGES[0];

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function pick(code: LangCode) {
    i18n.changeLanguage(code);
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t("topbar.language")}
        className={cn(
          "inline-flex items-center gap-2 rounded-full text-sm transition",
          variant === "ghost"
            ? "px-3 py-1.5 hover:bg-accent"
            : "border border-border bg-card px-3 py-2 shadow-sm hover:border-ring",
        )}
      >
        <Globe className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{active.native}</span>
        <ChevronDown className={cn("h-3.5 w-3.5 transition", open && "rotate-180")} />
      </button>

      {open && (
        <ul
          role="listbox"
          className={cn(
            "absolute z-50 mt-2 w-56 animate-fade-in-up overflow-hidden rounded-xl border border-border bg-card p-1 shadow-lg",
            align === "end" ? "right-0" : "left-0",
          )}
        >
          {LANGUAGES.map((l) => {
            const selected = l.code === active.code;
            return (
              <li key={l.code}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => pick(l.code)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition",
                    selected ? "bg-accent text-accent-foreground" : "hover:bg-muted",
                  )}
                >
                  <span>
                    <span className="font-medium">{l.native}</span>
                    {l.native !== l.english && (
                      <span className="ml-2 text-xs text-muted-foreground">{l.english}</span>
                    )}
                  </span>
                  {selected && <Check className="h-4 w-4 text-primary" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
