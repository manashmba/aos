import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Send, Bot, User as UserIcon, Wrench, Mic, MicOff, Sparkles } from "lucide-react";
import { ConversationAPI, type AgentRunResult } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useSpeech } from "@/lib/useSpeech";
import { cn } from "@/lib/utils";

type Msg = {
  role: "user" | "assistant" | "system";
  content: string;
  meta?: AgentRunResult | null;
};

export function ChatPage() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Voice-first: when speech recognition delivers a final transcript, drop it
  // into the input and submit. Recognition language follows the UI language.
  const speech = useSpeech((finalText) => {
    setInput(finalText);
    void send(finalText);
  });
  // Live interim transcript updates the input field for visual feedback.
  useEffect(() => {
    if (speech.listening && speech.transcript) setInput(speech.transcript);
  }, [speech.transcript, speech.listening]);

  const firstName = useMemo(() => (user?.name ?? "").split(" ")[0] || "👋", [user]);

  // Order of useEffects matters — session first, welcome reacts to language.
  useEffect(() => {
    (async () => {
      const { data } = await ConversationAPI.createSession("web");
      setSessionId(data.session_id ?? data.id);
    })();
  }, []);

  useEffect(() => {
    // Reset welcome bubble whenever language changes so the greeting
    // reflects the picker. Keep the user's own messages intact.
    setMessages((prev) => {
      const userAndAssist = prev.filter((m) => m.role !== "system");
      const welcome: Msg = {
        role: "assistant",
        content: t("chat.welcome", { name: firstName }),
      };
      const nonWelcome = userAndAssist.filter((_, idx) => idx !== 0 || !isWelcome(userAndAssist[0]));
      return [welcome, ...nonWelcome];
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i18n.resolvedLanguage, firstName]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(messageOverride?: string) {
    const text = (messageOverride ?? input).trim();
    if (!text || !sessionId || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const { data } = await ConversationAPI.sendMessage(sessionId, text);
      setMessages((m) => [...m, { role: "assistant", content: data.text, meta: data }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "system", content: `Error: ${e?.response?.data?.detail ?? e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const suggestionKeys = ["trialBalance", "reorder", "createPO", "leave"] as const;
  const showSuggestions = messages.length <= 1;

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-auto pb-4 pr-1">
        {messages.map((m, i) => (
          <Bubble key={i} msg={m} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 pl-11 text-sm text-muted-foreground">
            <Sparkles className="h-3 w-3 animate-pulse" />
            <span>{t("chat.thinking")}</span>
          </div>
        )}
      </div>

      {showSuggestions && (
        <div className="mb-3 flex flex-wrap gap-2">
          {suggestionKeys.map((k) => {
            const label = t(`chat.suggestions.${k}`);
            return (
              <button
                key={k}
                type="button"
                onClick={() => send(label)}
                className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition hover:border-primary/50 hover:bg-accent hover:text-foreground"
              >
                {label}
              </button>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-2 shadow-sm">
        <Input
          placeholder={t("chat.placeholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          disabled={loading || !sessionId}
          className="border-0 shadow-none focus-visible:ring-0"
        />
        <Button
          variant={speech.listening ? "default" : "ghost"}
          size="icon"
          type="button"
          aria-label={t("chat.mic")}
          title={
            !speech.supported
              ? "Voice input not supported in this browser"
              : speech.listening
                ? "Stop recording"
                : t("chat.mic")
          }
          disabled={!speech.supported}
          onClick={() => (speech.listening ? speech.stop() : speech.start())}
          className={cn(speech.listening && "animate-pulse")}
        >
          {speech.listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </Button>
        <Button onClick={() => send()} disabled={loading || !sessionId || !input.trim()} aria-label={t("chat.send")}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function isWelcome(m?: Msg) {
  return !!m && m.role === "assistant" && !m.meta;
}

function Bubble({ msg }: { msg: Msg }) {
  const { t } = useTranslation();
  const isUser = msg.role === "user";
  const isSystem = msg.role === "system";
  const Icon = isUser ? UserIcon : Bot;

  if (isSystem) {
    return (
      <div className="mx-auto max-w-xl rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-center text-xs text-destructive">
        {msg.content}
      </div>
    );
  }

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary/10 text-primary" : "bg-accent text-accent-foreground",
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <div className={cn("max-w-2xl space-y-2", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "rounded-tr-sm bg-primary text-primary-foreground"
              : "rounded-tl-sm border bg-card",
          )}
        >
          {msg.content}
        </div>
        {msg.meta?.tool_calls && msg.meta.tool_calls.length > 0 && (
          <div className="space-y-1 text-xs text-muted-foreground">
            {msg.meta.tool_calls.map((tc, i) => (
              <div key={i} className="inline-flex items-center gap-1.5 rounded-full border bg-muted/60 px-2 py-0.5">
                <Wrench className="h-3 w-3" />
                <span className="font-mono">{tc.tool}</span>
                <span className="opacity-60">· {(tc.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}
        {msg.meta?.requires_approval && (
          <div className="inline-block rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-900">
            {t("chat.pendingApproval")} · {msg.meta.approval_request_id}
          </div>
        )}
      </div>
    </div>
  );
}
